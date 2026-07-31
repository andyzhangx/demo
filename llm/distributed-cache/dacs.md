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
- **Scheduling constraints** (from the STS `spec.template.spec`):
  - `nodeAffinity requiredDuringScheduling: karpenter.sh/nodepool In [kaito]`
    — the cache backend can **only** land on the kaito (GPU inference)
    nodepool. It cannot run on any other pool.
  - `podAntiAffinity requiredDuringScheduling: app=cacheserver, topologyKey=kubernetes.io/hostname`
    — at most one `cache-sample-*` pod per node. Scaling replicas requires
    at least the same number of kaito nodes.
  - `tolerations: [{operator: Exists}]` — tolerates every taint
    (including whatever kaito uses to keep non-GPU workloads off).
- **Storage**: `hostPath: /var/lib/ssd/cacheserver` with `type: Directory`.
  The directory must **already exist** on the node, i.e. the
  `cache-server-prereq` DS must have finished its NVMe RAID0 setup on
  that node before the STS pod can Ready. Without an NVMe-provisioned
  kaito node, the pod fails with `FailedMount`.
- Current placement: the sole kaito node in the cluster
  (`aks-ws151843db6-36714139-vmss000000`).

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

### How the DS ties into the cache STS

The prereq DS is the hard prerequisite for `cache-sample-0` being able
to start on a given node. The STS itself has a `hostPath` volume at
`/var/lib/ssd/cacheserver` with `type: Directory`, so kubelet refuses
to mount it if that path doesn't exist. The DS is what creates it:

```
cache-server-prereq DS (per kaito node)
    initContainer nvme-raid-setup
        nsenter -> host mount namespace
        mdadm --create /dev/md0 --level=0 (NVMe RAID0)
        mkfs.ext4 -L tachyon-cache
        mount /var/lib/ssd/cacheserver
            |
            v
cache-sample-0 (STS) can now hostPath-mount /var/lib/ssd/cacheserver
        `-- kaito nodepool nodeAffinity + one-per-node antiAffinity
            makes sure it lands on exactly such a node
```

Earlier drafts of this doc (before the STS spec was inspected) said the
NVMe RAID0 volumes were pre-provisioned but idle and that `cache-sample`
ran on a different pool. That was wrong — the STS is already pinned to
kaito and the hostPath is already wired into `/var/lib/ssd/cacheserver`,
so the RAID0 is being consumed today, not sitting idle. The mistake came
from looking at a stale node name from a previous karpenter generation.

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
                    │                            │   consumed by
                    │                            │   cache-sample-0 via
                    │                            │   hostPath
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
2. **NVMe RAID0 volumes on kaito nodes are consumed by `cache-sample-0`
   via `hostPath`.** The STS is pinned to `karpenter.sh/nodepool=kaito`
   with a one-per-node anti-affinity and mounts `/var/lib/ssd/cacheserver`
   directly. That means:
   - Scaling `cache-sample` beyond 1 replica requires ≥N kaito nodes
     with a healthy prereq DS run on each.
   - Losing the prereq DS (e.g. it crashes before mounting) on a node
     that's about to host `cache-sample-0` blocks the STS pod at
     `FailedMount`.
   - Karpenter disrupting the current kaito node forces the STS to
     reschedule to another kaito node where the prereq DS has already
     finished — there's a rescheduling latency budget here.
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

## Consumer contract — how a workload actually opts in

Every workload that wants to use DACS must mount the `dacs-client` image
volume. Concretely a running `phi-4-cache-*` pod looks like this (only the
DACS-relevant bits shown — everything else is unchanged from a normal
vLLM inference pod):

```yaml
spec:
  volumes:
    # 1. The dacs-client, delivered as an OCI image volume (K8s 1.31+ beta,
    #    1.33 GA, requires the ImageVolume feature gate on kubelet).
    - name: cache-client
      image:
        reference: hariazstortest.azurecr.io/dacs-client:20260714.10
        pullPolicy: IfNotPresent
    # 2. Workload-identity federated token for cache -> Azure Blob auth.
    - name: azure-identity-token
      projected:
        sources:
          - serviceAccountToken:
              audience: api://AzureADTokenExchange
              expirationSeconds: 3600
              path: azure-identity-token

  containers:
    - name: phi-4-cache
      volumeMounts:
        - name: cache-client
          mountPath: /opt/cache-client
          readOnly: true                # image volumes are ALWAYS read-only
        - name: azure-identity-token
          mountPath: /var/run/secrets/azure/tokens
          readOnly: true
      env:
        # --- Where to reach the cache (data plane) ---
        - name: CACHE_DISCOVERY_URL
          value: cache-sample-discovery.dacs-cache-system.svc.cluster.local
        - name: CACHE_SERVER_PORT
          value: "9065"

        # --- Storage account this workload wants to read ---
        - name: AZURE_STORAGE_ACCOUNT_NAME
          value: harikaito

        # --- vLLM / RunAI Streamer wiring: tell the streamer to load
        #     the DACS interception .so out of the image volume ---
        - name: RUNAI_STREAMER_CACHE_ENABLED
          value: "true"
        - name: RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED
          value: "true"
        - name: RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB
          value: /opt/cache-client/usr/local/lib/python3.10/dist-packages/dacs_client/libStorageDirect.so

        # --- Workload Identity for the cache to fetch blobs on
        #     behalf of this pod's SA ---
        - name: AZURE_CLIENT_ID
          value: <workload-identity-client-id>
        - name: AZURE_TENANT_ID
          value: <tenant-id>
        - name: AZURE_FEDERATED_TOKEN_FILE
          value: /var/run/secrets/azure/tokens/azure-identity-token
        - name: AZURE_AUTHORITY_HOST
          value: https://login.microsoftonline.com/
```

The user does **not** hand-write any of this — the
`tachyon-cache-webhook-service` MutatingWebhook (see §3 above) injects
the `cache-client` volume, the `azure-identity-token` projection, and all
the env vars at admission time based on a pod label (e.g.
`dacs.azure.com/inject: "true"`). What the user *does* have to do is:

1. Add the DACS mutation label to the pod / template.
2. Bind the workload's ServiceAccount to a Workload Identity that has
   `Storage Blob Data Reader` on the target storage account
   (`harikaito` here).
3. Use a model loader that understands the DACS interception library
   (currently RunAI Streamer, i.e. vLLM's `--load-format=runai_streamer`).

### Why an `image` volume specifically

The `dacs-client` is a plain OCI image published to ACR
(`hariazstortest.azurecr.io/dacs-client:20260714.10`). Kubernetes 1.31
introduced the `image` volume source (beta, GA in 1.33) which pulls an
OCI image via the container runtime and exposes its rootfs to the pod
as a **read-only** volume, mounted at `/opt/cache-client` in this case.
Compared to the alternatives, this buys DACS several properties:

- **No init container, no sidecar.** No extra pod-startup latency, no
  extra container to manage lifecycles for. The volume is just there
  from the moment the main container starts.
- **No baking `dacs_client` into every model image.** Kaito, HuggingFace
  TGI, custom vLLM images … none of them need to know DACS exists at
  build time. The webhook adds it at admission time.
- **Independent lifecycle from the workload image.** Rolling out a new
  DACS client (`:20260714.10` → `:20260801.1`) is a webhook config change
  + pod restart, not a rebuild of every inference image.
- **Read-only by design.** The volume is mounted `readOnly: true` (the
  image-volume spec enforces this anyway), so nothing in the workload can
  tamper with the interception library. The vLLM process can only load
  the `.so` and use it.
- **Same pull machinery as normal images.** Uses the node's kubelet image
  pull secrets, same registry credentials, same containerd cache. Nothing
  bespoke about registry auth.
- **Content addressable / signable.** Because it's an OCI image, it can
  be pinned by digest and cosigned/attested in a normal SLSA/sigstore
  pipeline. No cluster-scoped file distribution or DaemonSet-based
  bootstrap needed.

### What the mount actually contains

`/opt/cache-client` is the full rootfs of the `dacs-client` image. The
pieces the workload consumes:

- `/opt/cache-client/usr/local/lib/python3.10/dist-packages/dacs_client/libStorageDirect.so`
  — the C++ interception library. RunAI Streamer is pointed at this via
  `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB`, `dlopen`s it, and from
  that point on every Azure Blob GET/READ the streamer would issue goes
  through the DACS `StreamingClient` → `ConnectionManager` → cache-pool
  code path instead of straight to `*.blob.core.windows.net`.
- The `dacs_client` Python package (also under `dist-packages/`) —
  provides the `BlobSiWrapper` that generates `/tmp/storageIntercept.<pid>.config`
  at process startup, populates `storagePath`, `cacheServerDiscoveryEndpoint`,
  `cacheEnableRemote`, `HashingStrategy=ConsistentHashing`, etc. from
  the `CACHE_DISCOVERY_URL` / `CACHE_SERVER_PORT` / `AZURE_*` env vars.

All of the `AISC_CTR:INFO|StorageIntercept|...` and
`AISC_CTR:INFO|StorageCommon|ConnectionManager.cpp:...` log lines you see
in the inference pod logs come from this `.so` — they're the ground
truth for `Samples=N from Cache` / `Samples=M from Remote` that drove
the cold-vs-warm cache measurements in
[`enable-dacs-in-kaito-workspace.md`](./enable-dacs-in-kaito-workspace.md).

### End-to-end flow when a workload starts

1. User creates a KAITO `Workspace` (or a plain pod with the DACS label).
2. Admission goes through the API server → `tachyon-cache-webhook-service`.
   The webhook mutates the pod spec to add the `cache-client` image
   volume, the `azure-identity-token` projection, the `volumeMounts`,
   and the RunAI Streamer + Workload Identity env vars.
3. kubelet on the target node pulls `hariazstortest.azurecr.io/dacs-client:20260714.10`
   via containerd (same path as any other image) and mounts its rootfs
   read-only at `/opt/cache-client`. The workload's `phi-4-cache` main
   container starts.
4. vLLM sees `--load-format=runai_streamer` (or the KAITO controller has
   set `load_format=runai_streamer` on its behalf).
5. RunAI Streamer honours `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=true`
   and `dlopen`s `libStorageDirect.so` out of the image volume.
6. `BlobSiWrapper` runs, generates the SI config, discovers the cache
   pool via `cache-sample-discovery.dacs-cache-system.svc:9065`, gets
   back `cache-sample-0.cache-sample.dacs-cache-system.svc:9065`.
7. Streamer issues "blob GET" — the SI shim rewrites it into a request
   against `cache-sample-0` on port 9065. Cache hit → served locally.
   Cache miss → cache pod uses `azure-identity-token` (workload identity
   federated exchange) to fetch from `harikaito.blob.core.windows.net`,
   populates the cache, streams to the client. Both paths are labelled
   in the shutdown latency histogram (`from Cache` vs `from Remote`).

### If any piece is missing

- **No image volume mounted at `/opt/cache-client`** → `dlopen` of the
  `.so` fails, RunAI Streamer falls back to raw Azure Blob (or, if the
  KAITO controller silently rewrites `--load-format` to `auto`, to HF
  Hub). This is the exact "silent HF fallback" mode called out in the
  sibling doc's *Red flags* section.
- **`RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB` unset** → the library
  is on disk but never loaded. Loader goes straight to Azure Blob.
- **`azure-identity-token` projection missing** → cache pod's remote
  fetch path fails with 401/403 the first time a miss falls through to
  Azure Blob, and the whole workload wedges on the cold-cache path.
- **`ImageVolume` feature gate off on kubelet** (K8s <1.31 or gate
  disabled) → API server accepts the pod spec but kubelet refuses to
  mount the volume, pod stuck in `ContainerCreating`. Node must be on
  K8s 1.31+ with the gate enabled (default in 1.33).

## Failure case study — `cache-sample-0` in ImagePullBackOff (2026-07-29)

Caught a live example of the exact silent-degradation mode called out
above. `phi-4-cache-kdf7k-0` had DACS fully injected on the client side
but still loaded weights straight from Azure Blob — because the cache
backend was down.

### Symptom on the client side

Model load time jumped back to the cold-cache range even though the
cache was "supposed to be warm":

```text
Loading safetensors using Runai Model Streamer: 100% Completed | 194/194 [00:09<...]
StreamingClient.cpp:LogDownloadLatencyStatsInner:
  Download latencies (ms) from Remote MountName= Samples=252 Min=263 Max=4267 Avg=1285 P50=1013 P95=3090
  Download latencies (ms) from Remote MountName= Samples=426 Min=202 Max=4267 Avg=1127 P50=929  P95=2824
Model loading took 7.17 GiB memory and 14.262235 seconds
```

Key signal: **`Samples=426 from Remote`, zero `from Cache`.** Compare
against the warm baseline in
[`enable-dacs-in-kaito-workspace.md`](./enable-dacs-in-kaito-workspace.md)
(`Samples=433 from Cache`, `0 from Remote`, 4.2–4.6 s). The 14.26 s load
time is even a bit worse than the original cold measurement because
now *no* client is populating the cache either — there's literally no
cache pod to write to.

### The pod's DACS wiring was fine

All the mutations were in place:

- `cache-client` image volume mounted at `/opt/cache-client`
- `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB` pointed at the right `.so`
- `CACHE_DISCOVERY_URL=cache-sample-discovery.dacs-cache-system.svc.cluster.local`
- Workload Identity token projected at `/var/run/secrets/azure/tokens/`

SI startup logs even confirm the client thought it was going to use the
cache:

```text
BlobSiWrapper.cpp:generate_si_config(214): distributed cache enabled (port=9065)
ConnectionManager.cpp:ConnectionManager(144): Cache server discovery is enabled
```

### Where it fell over

~5 ms later the client couldn't reach the discovery endpoint:

```text
ConnectionManager.cpp:CreateSocketAndConnect(622):
  Connection timed out or socket not writable for
  hostname=cache-sample-discovery.dacs-cache-system.svc.cluster.local
ConnectionManager.cpp:FetchLatestCacheServers(922):
  Couldn't create server connection for fetching cache servers
ConnectionManager.cpp:ConnectionManager(148):
  Failed to fetch the cache servers from endpoint ...
  Cache client will start with empty server list and
  rely on background discovery.
```

StreamingClient then continued setup with an *empty server list* and
initialised `BlobClient` with the pod's Workload Identity:

```text
BlobAuthTokenProvider: Successfully fetched access token via WorkloadIdentityCredential
BlobClient(114): Initialized blob client ... authType=2 ...
StreamingClient(188): StreamingClient initialized ... enableRemoteWrite=true ...
```

From that point on, every safetensors read went straight to
`harikaito.blob.core.windows.net` via the WI-authenticated `BlobClient`.
No HF Hub fallback — the `runai_streamer` loader was still active, it
just bypassed the cache tier entirely.

### Root cause on the cache side

```console
$ kubectl -n dacs-cache-system get po
NAME             READY   STATUS         RESTARTS   AGE
cache-sample-0   0/1     ErrImagePull   0          3m30s

$ kubectl -n dacs-cache-system get endpoints cache-sample cache-sample-discovery
NAME                     ENDPOINTS   AGE
cache-sample                         2d3h      # empty
cache-sample-discovery               2d3h      # empty

$ kubectl -n dacs-cache-system describe po cache-sample-0
  Warning  Failed  ...  Failed to pull image
    "tachyontestacr.azurecr.io/cache-server:20260724.17":
    ... 401 Unauthorized
```

The `cache-sample` StatefulSet had been rolled to a new image tag
`tachyontestacr.azurecr.io/cache-server:20260724.17`, but the cluster
doesn't have credentials for `tachyontestacr.azurecr.io` (the previously
working image was on `hariazstortest.azurecr.io`). kubelet loops on
`ErrImagePull` → `ImagePullBackOff`, the pod never reaches Ready, the
headless service and the discovery service both keep an empty endpoint
list, and every DACS client in the cluster silently falls back to
direct blob reads.

### End-to-end path this pod actually took

```
phi-4-cache-kdf7k-0 (vLLM --load-format=runai_streamer)
       |
       | dlopen /opt/cache-client/.../libStorageDirect.so   OK
       |
       +-- cache-sample-discovery.dacs-cache-system.svc:9065
       |         `-- X  connect timeout (endpoint empty)
       |
       |  (StreamingClient continues in remote-only mode)
       v
  BlobClient (WorkloadIdentity -> api://AzureADTokenExchange
              -> Azure AD -> Storage Blob Data Reader)
       |
       v
  https://harikaito.blob.core.windows.net/...   194 files, 426 GETs
       |
       v
  vLLM model weights loaded (14.26 s, 100% Azure Blob egress)
```

### Why this is the *silent* fallback

- Pod is `Running / Ready` — no alarm at the workload level.
- Load time is 3× the warm baseline but only 15–20% worse than a legit
  cold-cache load. Easy to miss unless you're watching the histogram.
- Zero `from Cache` samples is the *only* immediate signal, and it lives
  in the client's shutdown log, not in Prometheus.
- Workload Identity path works, so the storage account still serves
  reads happily — you just pay full egress every pod start.

### Detection & remediation

What to check when a workload "looks slow":

```bash
# 1. is the cache backend actually up?
kubectl -n dacs-cache-system get po,endpoints cache-sample cache-sample-discovery

# 2. did the client find a server?
kubectl logs <workload-pod> | grep -E "ConnectionManager|FetchLatestCacheServers" | head

# 3. what's the from-Cache / from-Remote split at shutdown?
kubectl logs <workload-pod> | grep 'Download latencies'
```

Remediation for this specific incident:

1. Fix `cache-sample` STS image: either revert the tag to the previously
   working `hariazstortest.azurecr.io/cache-server:*`, or attach an
   `imagePullSecret` for `tachyontestacr.azurecr.io` on the STS's
   ServiceAccount.
2. Wait for `cache-sample-0` Ready → endpoints populate.
3. Running client pods **don't need to restart** — `ConnectionManager`
   runs `background discovery` every 300 s and will pick up the new
   endpoint automatically. But this only helps *future* reads; the model
   is already loaded, so the cold-path cost on the already-running pod
   can't be recovered until the pod restarts.

### Follow-ups to prevent it next time

- Add a PrometheusRule: alert if `cache-sample-*` pods have `ready==0`
  for > 5 min, or if `cache-sample-discovery` endpoints are empty.
- Add a KAITO controller readiness gate that scrapes
  `Samples=... from Cache` on the first pod after `KVCacheReady=True` and
  refuses to mark the workspace Healthy if `Cache==0 && Remote>0`.
- Pin the cache backend image to a specific ACR the cluster already has
  a working pull secret for; block silent tag changes behind
  code review.

## `ModelMirror` — the origin blob layer in front of HF Hub

A lot of confusion around "is the cache warm?" comes from mixing up two
different backends. This section separates them.

### What it is

`ModelMirror` is a **cluster-scoped Kaito CRD** (`kaito.sh/v1alpha1`) that
pre-fetches a HuggingFace (or OCI) model into cluster-local persistent
storage, and exposes it as a **stable, auth-controlled blob URI** for later
Workspace / InferenceSet runs. Think "in-cluster mirror of HF Hub."

How the reconcile loop works, roughly:

1. Kaito controller creates a one-shot download `Job` in
   `spec.jobNamespace`, using `spec.serviceAccountName` for HF token /
   Azure workload identity.
2. Job pulls the model from `spec.source.registry` + `modelID`.
3. Bytes land in a PVC provisioned from `spec.storage.storageClassName`
   (on `andy-aks135` this is `blob-harikaito` → Azure Blob account
   `harikaito`).
4. On success: `status.phase=Ready`, `status.modelPath` becomes the path
   vLLM / RunAI Streamer reads from.

### Where it sits vs DACS

With DACS enabled the full read path is:

```text
vLLM (--load-format=runai_streamer)
   → RunAI Streamer
      → libStorageDirect.so (DACS client)
         → cache-sample-0 (DACS cache, host-path SSD)
            → (miss) ModelMirror blob PVC = harikaito.blob.core.windows.net/...
               → (miss) HuggingFace Hub   ← only during ModelMirror initial pull
```

Two distinct backends, both fronting HF:

| Layer | What it stores | Populated by | Consumed as |
|---|---|---|---|
| **ModelMirror** | HF snapshot on Azure Blob PVC (`storageClassName: blob-harikaito`, path `/models/<org>/<model>`) | one-shot Job at ModelMirror create time | RunAI Streamer's **origin URI** — shows up as `from Remote` in the DACS histogram |
| **DACS `cache-sample-0`** | on-disk block cache (`/var/lib/ssd/cacheserver`) | lazily by client I/O (first miss → fetch → store) | RunAI Streamer via `libStorageDirect.so` — shows up as `from Cache` in the DACS histogram |

**⚠️ `ModelMirror.status.phase=Ready` does *not* imply the DACS cache is
warm.** All it guarantees is that the origin blob is populated. If
`cache-sample-0` has been pending, restarted, or its host-path SSD was
wiped (e.g. Karpenter replaced the node), the next inference pod is
back on the cold path even if `ModelMirror` reported `Ready` days ago.
See [`dacs-test-result.md`](./dacs-test-result.md) for a concrete
cold-path observation with `ModelMirror` already Ready for 2 days.

### `kubectl` cookbook

`ModelMirror` is cluster-scoped, so no `-n` needed:

```bash
# List everything
kubectl get modelmirror
kubectl get mm                              # short name
kubectl get modelmirror -o wide

# Detail on one CR
kubectl describe modelmirror <name>
kubectl get modelmirror <name> -o yaml

# Compact JSON summary of what matters
kubectl get modelmirror -o json | jq '.items[] | {
  name: .metadata.name,
  model: .spec.source.modelID,
  registry: .spec.source.registry,
  storageClass: .spec.storage.storageClassName,
  size: .spec.storage.size,
  jobNs: .spec.jobNamespace,
  sa: .spec.serviceAccountName,
  phase: .status.phase,
  modelPath: .status.modelPath,
  lastDownload: .status.lastDownloadTime,
  ready: (.status.conditions[]? | select(.type=="Ready") | .status)
}'

# CRD schema — useful for authoring new mirrors
kubectl explain modelmirror.spec --recursive
kubectl get crd modelmirrors.kaito.sh -o yaml

# Backing PVC + downloader Job
kubectl get pvc -A | grep -i mirror
kubectl get job -A | grep -i mirror         # in spec.jobNamespace
kubectl -n <jobNs> logs job/<mirror-download-job>
```

Example from `andy-aks135` today:

```console
$ kubectl get modelmirror
NAME     MODEL                            PHASE   AGE
172f34   microsoft/phi-4-mini-instruct    Ready   2d
8deac4   qwen/qwen2.5-coder-7b-instruct   Ready   2d16h
```

`172f34` key spec + status:

```yaml
spec:
  mode: Managed
  jobNamespace: default
  serviceAccountName: vllm-sa
  source:
    registry: huggingface
    modelID: microsoft/phi-4-mini-instruct
  storage:
    storageClassName: blob-harikaito       # → Azure Blob account 'harikaito'
    size: 87Gi
status:
  phase: Ready
  modelPath: /models/microsoft/phi-4-mini-instruct
  lastDownloadTime: 2026-07-29T07:15:34Z
  conditions:
    - type: StorageReady   status: True   reason: PVCBound
    - type: Ready          status: True   reason: DownloadSucceeded
```

### How a Workspace opts in

Set `Workspace.spec.inference.preset.name` to a model ID that has a Ready
`ModelMirror`. The Kaito controller matches by `spec.source.modelID`,
mounts the ModelMirror's PVC into the inference pod, and rewrites the
vLLM launch to read from `status.modelPath`. If no matching ModelMirror
exists, vLLM falls back to `huggingface_hub.snapshot_download()` and
pays the HF Hub round-trip per pod — which also **bypasses DACS entirely**
unless `--load-format=runai_streamer` is being used.

## See also

- [`enable-dacs-in-kaito-workspace.md`](./enable-dacs-in-kaito-workspace.md)
  — end-to-end enablement walkthrough on the KAITO controller side,
  including the cold-vs-warm cache benchmark that these components serve.
- [`dacs-test-result.md`](./dacs-test-result.md) — concrete cold-path
  observation on `andy-aks135` showing why `ModelMirror Ready` ≠ warm cache.
- [`dacs-vs-tachyon.md`](./dacs-vs-tachyon.md) — comparison notes.
- [`setup.md`](./setup.md) — cluster/component installation notes.
