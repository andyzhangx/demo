# DACS (Distributed Azure Cache Service) — component walkthrough

Notes from inspecting a live DACS-enabled AKS cluster (`andy-aks135`,
namespace `dacs-cache-system`) on 2026-07-29. Focus is on what each
workload in the namespace actually does, how they relate to each other,
and where the current bottlenecks are.

## What was running

```console
$ kubectl -n dacs-cache-system get all
NAME                                        READY   STATUS    RESTARTS   AGE
pod/cache-sample-0                          1/1     Running   0          27h
pod/cache-server-prereq-6kndn               1/1     Running   0          25m
pod/cache-server-prereq-7h86n               1/1     Running   0          2d
pod/cache-server-prereq-9psjw               1/1     Running   0          47h
pod/cache-server-prereq-9z9qd               1/1     Running   0          45m
pod/cache-server-prereq-hv6h2               1/1     Running   0          93m
pod/cache-server-prereq-jcxlj               1/1     Running   0          47h
pod/cache-server-prereq-kr8n5               1/1     Running   0          2d
pod/cache-server-prereq-q48pp               1/1     Running   0          17h
pod/cache-server-prereq-thlv9               1/1     Running   0          24h
pod/cache-server-prereq-xl7vz               1/1     Running   0          2d
pod/cache-server-prereq-xvlcx               1/1     Running   0          17h
pod/tachyon-cache-manager-cb4745548-tmmkf   1/1     Running   0          27h

NAME                                            TYPE        CLUSTER-IP     PORT(S)
service/cache-sample                            ClusterIP   None           9065/TCP,9096/TCP   # headless
service/cache-sample-discovery                  ClusterIP   10.0.150.137   9065/TCP
service/tachyon-cache-manager-metrics-service   ClusterIP   10.0.8.14      8443/TCP
service/tachyon-cache-webhook-service           ClusterIP   10.0.32.198    443/TCP

NAME                                 KIND         DESIRED   READY   NODE SELECTOR
daemonset.apps/cache-server-prereq   DaemonSet    4         4       karpenter.sh/nodepool=kaito
statefulset.apps/cache-sample        StatefulSet  1         1       -
deployment.apps/tachyon-cache-manager Deployment  1         1       -
```

Three distinct roles: **data plane**, **node bootstrap**, **control plane**.

## 1. `cache-sample-0` — the actual cache backend (data plane)

- Kind: **StatefulSet** `cache-sample` (`replicas=1`)
- Services:
  - `cache-sample` — headless (`ClusterIP: None`), ports `9065/TCP` and `9096/TCP`
  - `cache-sample-discovery` — regular `ClusterIP` on `9065/TCP`, used by clients to bootstrap the server list
- Node: currently scheduled on `aks-wseb5f636b9-...` (**not** a kaito nodepool node)

This is the Tachyon cache server that every `dacs_client` connects to.
The client-side config (auto-generated in each workload pod) points at:

```
cacheServerDiscoveryEndpoint  cache-sample-discovery.dacs-cache-system.svc.cluster.local
cacheServerPort               9065
cacheEnableRemote             true
```

and `ConnectionManager` then resolves the list to
`cache-sample-0.cache-sample.dacs-cache-system.svc.cluster.local` via the
headless service. Every one of the `phi-4-cache-*` inference pods measured
in [`enable-dacs-in-kaito-workspace.md`](./enable-dacs-in-kaito-workspace.md)
reports its warm-path `Samples=433 from Cache` against exactly this pod.

Single-replica STS = **the current throughput/HA bottleneck**. The client
config already advertises `HashingStrategy=ConsistentHashing`, so scaling
the STS out is a config change on the CR / STS, not a client migration.

## 2. `cache-server-prereq-*` — per-node NVMe bootstrap DaemonSet

- Kind: **DaemonSet** `cache-server-prereq`
- `nodeSelector: karpenter.sh/nodepool=kaito` (only the GPU inference nodepool)
- Toleration: `karpenter.sh/disrupted:NoSchedule op=Exists`
- Main container: `mcr.microsoft.com/azurelinux/base/core:3.0` running
  `sleep infinity` — pure pause once init finishes
- All the real work happens in the **initContainer** `nvme-raid-setup`:
  - `hostPID: true` + `privileged: true`
  - `nsenter -t 1 -m -u -i -n -p -- /bin/bash` to run inside the **host**
    mount/util namespaces
  - Installs `mdadm` + `e2fsprogs` if missing
  - Enumerates `/dev/nvme*n*`, skips: partitions, RAID members, mounted
    devices (catches OS disk), devices with existing signatures
  - Single unused NVMe → `mkfs.ext4 -L tachyon-cache` and mount directly
  - Multiple unused NVMe → `mdadm --create /dev/md0 --level=0` RAID0,
    then `mkfs.ext4 -L tachyon-cache`
  - Mounts at `/var/lib/ssd/cacheserver`, `chmod 0777`
  - Persists via `/etc/mdadm/mdadm.conf` and an `/etc/fstab` entry
    (`LABEL=tachyon-cache … ext4 defaults,noatime,nofail 0 2`)
  - On failure, emits a `Warning` Event to the K8s API (`reason=NVMeSetupFailed`)
    against the Node object

### Why 11 pods when `DESIRED=4`

The DaemonSet controller reports `DESIRED=4 CURRENT=4 READY=4`, but there
are 11 `Running` pods spread across 11 different kaito-pool GPU nodes.
That gap is karpenter node rotation churn — the controller's `desired`
count doesn't line up with the number of nodes currently matched by the
selector because karpenter is disrupting/replacing kaito-pool nodes
frequently. Functionally every kaito-pool GPU node has exactly one live
prereq pod that already did the NVMe RAID0 setup.

### Latent design decision — currently unused disks

The NVMe RAID0 volumes are mounted on **kaito nodepool GPU nodes**, but
`cache-sample-0` runs on a **different pool** (`aks-wseb5f636b9-...`) with
no `hostPath` volume mount to `/var/lib/ssd/cacheserver`. So today the
Tachyon cache server is **not** actually consuming these NVMe RAID0
volumes — they're pre-provisioned and idle. This strongly suggests the
roadmap is to either:

- convert `cache-sample` to a DaemonSet co-scheduled with the GPU pods and
  fronting the local NVMe, or
- add anti-affinity + `hostPath` to pin cache STS replicas onto kaito
  nodes.

Either way, the prereq DS is preparing for a topology where cache lives
next to compute for zero cross-node network hops. That step hasn't shipped
in this cluster yet.

## 3. `tachyon-cache-manager-cb4745548-tmmkf` — the control plane

- Kind: **Deployment** `tachyon-cache-manager` (1 replica)
- Services:
  - `tachyon-cache-manager-metrics-service:8443` — metrics / health
  - `tachyon-cache-webhook-service:443` — mutating webhook endpoint
- 5 historical ReplicaSets (`5966466b5`, `6c5c78bc5c`, `779cbdbcf7`,
  `c44b74494`, `cb4745548`) all at 0 replicas — image has rolled 5 times;
  the current version is 27h old

Two responsibilities:

**a) Reconcile the `caches.storage.azure.com` CR.** When KAITO (or any
other controller) creates a `Cache` CR that describes a blob source and
caching policy, this controller renders that into the `cache-sample`
StatefulSet, its services, and the auto-generated client config. This is
why the KAITO workspace controller had to be granted RBAC on
`caches.storage.azure.com` in the sibling
[`enable-dacs-in-kaito-workspace.md`](./enable-dacs-in-kaito-workspace.md)
walkthrough.

**b) MutatingWebhook injection.** Pods labeled with
`dacs.azure.com/inject` (or whatever the current DACS mutation label is)
get the DACS client mounted in:

- an image volume `cache-client` pointing at
  `hariazstortest.azurecr.io/dacs-client:20260714.10` (an OCI image mounted
  read-only via the K8s `image` volume type)
- Storage-Intercept environment variables that tell libc/libcurl overlays
  to route Azure Blob API calls through the cache
- a `projected` token with audience `api://AzureADTokenExchange` for
  Workload Identity (so the cache client can hit the storage account
  under the workload's identity, not a shared key)

In the inference pods that produced the 3× speedup data, the injected
volumes were:

```json
[
  {"emptyDir":{"medium":"Memory"},"name":"dshm"},
  {"image":{"pullPolicy":"IfNotPresent",
            "reference":"hariazstortest.azurecr.io/dacs-client:20260714.10"},
   "name":"cache-client"},
  {"name":"azure-identity-token","projected":{"sources":[
     {"serviceAccountToken":{"audience":"api://AzureADTokenExchange",
                             "expirationSeconds":3600,
                             "path":"azure-identity-token"}}]}}
]
```

None of that is in the KAITO workspace spec — it's all injected by this
webhook.

## Relationship diagram

```
                    ┌─────────────────────────────┐
                    │  tachyon-cache-manager       │  control plane
                    │  Deployment (1 replica)     │
                    │  - reconciles Cache CR      │
                    │  - MutatingWebhook          │  ──▶ injects
                    │    (tachyon-cache-webhook-  │      dacs-client image
                    │     service:443)            │      volume + SI env +
                    │  - metrics (:8443)          │      WI token into
                    └──────────────┬──────────────┘      workload pods
                                   │
                                   │ creates / owns
                                   ▼
                    ┌─────────────────────────────┐
                    │  cache-sample (STS x1)       │  data plane
                    │  cache-sample-0             │  ◀── phi-4-cache-* pods
                    │                             │      via dacs_client
                    │  Headless svc  :9065/:9096  │      Storage-Intercept
                    │  Discovery svc :9065        │      (ConsistentHashing)
                    └─────────────────────────────┘

                    ┌─────────────────────────────┐
                    │  cache-server-prereq (DS)    │  node bootstrap
                    │  kaito nodepool only        │
                    │  privileged + hostPID       │  ─── nsenter host ns
                    │  initContainer:             │      to build RAID0 on
                    │  - detects unused NVMe      │      /dev/nvme*n*,
                    │  - RAID0 via mdadm         │      mkfs.ext4,
                    │  - mkfs.ext4 -L tachyon-   │      mount at
                    │    cache                   │      /var/lib/ssd/
                    │  - persist to fstab        │      cacheserver
                    │  main: sleep infinity      │
                    │                            │  (NOT yet consumed by
                    │                            │   the current cache-
                    │                            │   sample STS)
                    └─────────────────────────────┘
```

## Observations and recommendations

1. **`cache-sample` is a single-replica STS and every inference pod hits
   it.** The 3× warm-cache speedup measured in the sibling doc came from
   this one pod serving 3 clients simultaneously. Under HPA burst
   (10+ concurrent replicas coming up at once) it will be the
   throughput bottleneck. `ConsistentHashing` is already the client
   strategy — scaling the STS out to 2–3 replicas requires only a CR /
   STS edit, no client-side migration.
2. **NVMe RAID0 volumes are pre-provisioned on kaito nodes but not used
   by `cache-sample-0`.** Either the cache STS needs a scheduling
   constraint / hostPath mount to consume them, or the roadmap is to
   move `cache-sample` to a DaemonSet co-scheduled with GPU workloads.
   Until one of those lands, `cache-server-prereq` is dead weight from
   the data-plane perspective (though it's cheap — just a bootstrapper +
   pause).
3. **`tachyon-cache-manager` is a single-replica Deployment sitting on
   the critical path** for pod admission (webhook) and Cache-CR
   reconcile. If it goes down or its serving cert lapses, new workload
   pods will start **without** the `cache-client` image volume and the
   DACS env vars, and silently degrade to raw Azure Blob (or, worse, HF
   Hub). This is the exact "silent HF fallback" failure mode documented
   in [`enable-dacs-in-kaito-workspace.md`](./enable-dacs-in-kaito-workspace.md).
   Production posture should be:
   - `replicas>=2` with leader election on the reconciler side
   - PDB with `maxUnavailable=1`
   - cert-manager rotation for the webhook serving cert (or short-lived
     CAs pushed by the chart)
   - a KAITO-side readiness probe that verifies "webhook applied its
     mutation" before reporting `KVCacheReady=True`
4. **The webhook is the reason KAITO's spec is so clean.** Nothing in a
   KAITO `Workspace` mentions the DACS client image, the token audience,
   or the SI env vars — they're all mutated in at admission time by
   `tachyon-cache-webhook-service`. That's a nice separation, but it
   also means troubleshooting starts with "did the webhook fire?" — see
   the verification snippets in the sibling doc.

## See also

- [`enable-dacs-in-kaito-workspace.md`](./enable-dacs-in-kaito-workspace.md)
  — end-to-end enablement walkthrough on the KAITO controller side,
  including the cold-vs-warm cache benchmark that these components serve.
- [`dacs-vs-tachyon.md`](./dacs-vs-tachyon.md) — comparison notes.
- [`setup.md`](./setup.md) — cluster/component installation notes.
