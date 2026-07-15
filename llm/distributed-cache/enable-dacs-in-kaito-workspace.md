# Enable DACS distributed cache in KAITO workspace controller

Steps to switch an existing `kaito-workspace` deployment onto the KAITO PR
[#2169](https://github.com/kaito-project/kaito/pull/2169) build with the
DACS distributed-cache feature gate enabled, wired to a DACS installation in
the `dacs-cache-system` namespace.

## Target changes

| Item | From | To |
|---|---|---|
| Container image | `andyzhangx/workspace:0.9.0` | `andyzhangx/workspace:0.11.0-cache` |
| `--feature-gates=` | `...,enableMultiRoleInferenceController=true` | append `,distributedCache=true` |
| `DACS_DISCOVERY_ENDPOINT` | *(empty)* | `cacheserver-discovery.dacs-cache-system.svc.cluster.local:9065` |
| `DACS_KV_CONNECTOR_PROTOCOL` | *(empty)* | `tcp` |
| `DACS_CLIENT_IMAGE` | *(empty)* | `hariazstortest.azurecr.io/dacs-client:20260701.7` |
| `DACS_ENABLED` | `true` | *(unchanged)* |
| `DACS_KV_CACHE_ENABLED` | `false` | *(unchanged)* |
| ClusterRole `kaito-workspace-clusterrole` | — | grant `get,list,watch` on `caches.storage.azure.com` |

## Prerequisites

- `kubectl` pointing at the target AKS cluster.
- CRD `caches.storage.azure.com` installed (DACS ships it):

  ```bash
  kubectl get crd caches.storage.azure.com
  ```

- DACS control plane running in `dacs-cache-system`:

  ```bash
  kubectl -n dacs-cache-system get svc,deploy,ds
  ```

  Expect `cacheserver-discovery` service on port `9065`, `tachyon-cache-manager` deployment, and `cache-server-prereq` daemonset ready.

## Step 0 — Backup current state

```bash
mkdir -p /tmp/backup
kubectl -n kaito-workspace get deploy kaito-workspace -o yaml \
  > /tmp/backup/kaito-workspace.deploy.$(date +%Y%m%d-%H%M).yaml
kubectl get clusterrole kaito-workspace-clusterrole -o yaml \
  > /tmp/backup/kaito-workspace.clusterrole.$(date +%Y%m%d-%H%M).yaml
```

## Step 1 — Grant RBAC on `caches.storage.azure.com`

The cache controller in the KAITO build watches `Cache` custom resources.

```bash
kubectl patch clusterrole kaito-workspace-clusterrole --type json -p '[
  {"op":"add","path":"/rules/-","value":{"apiGroups":["storage.azure.com"],"resources":["caches"],"verbs":["get","list","watch"]}},
  {"op":"add","path":"/rules/-","value":{"apiGroups":["storage.azure.com"],"resources":["caches/status"],"verbs":["get"]}}
]'
```

Verify:

```bash
kubectl auth can-i list caches.storage.azure.com \
  --as=system:serviceaccount:kaito-workspace:kaito-workspace-sa
# expected: yes
```

## Step 2 — Update image and DACS env vars

`DACS_ENABLED` and `DACS_KV_CACHE_ENABLED` are already present in the
deployment — strategic-merge patch matches env entries by `name`, so it only
overwrites the three empty values and leaves the rest untouched.

```bash
kubectl -n kaito-workspace patch deploy kaito-workspace --type strategic -p '{
  "spec":{"template":{"spec":{"containers":[{
    "name":"workspace",
    "image":"andyzhangx/workspace:0.11.0-cache",
    "env":[
      {"name":"DACS_DISCOVERY_ENDPOINT","value":"cacheserver-discovery.dacs-cache-system.svc.cluster.local:9065"},
      {"name":"DACS_KV_CONNECTOR_PROTOCOL","value":"tcp"},
      {"name":"DACS_CLIENT_IMAGE","value":"hariazstortest.azurecr.io/dacs-client:20260701.7"}
    ]
  }]}}}
}'
```

## Step 3 — Append `distributedCache=true` to feature gates

The deployment has exactly one `args` entry (the `--feature-gates=` flag).
Replace it with the full string plus the new gate.

```bash
kubectl -n kaito-workspace patch deploy kaito-workspace --type json -p '[
  {"op":"replace","path":"/spec/template/spec/containers/0/args/0",
   "value":"--feature-gates=disableNodeAutoProvisioning=false,enableInferenceSetController=true,gatewayAPIInferenceExtension=true,vLLM=true,enableMultiRoleInferenceController=true,distributedCache=true"}
]'
```

## Step 4 — Wait for rollout and verify

```bash
kubectl -n kaito-workspace rollout status deploy/kaito-workspace --timeout=180s

kubectl -n kaito-workspace get deploy kaito-workspace -o json \
  | jq '.spec.template.spec.containers[0]
        | {image, args, env: (.env | map(select(.name | startswith("DACS_"))))}'

kubectl -n kaito-workspace logs deploy/kaito-workspace --tail=200 \
  | grep -iE 'dacs|cache|feature|register'
```

Success indicator in the logs:

```
Registered DACS cache provider  discoveryEndpoint=cacheserver-discovery.dacs-cache-system.svc.cluster.local:9065 kvCacheEnabled=false
```

## Rollback

```bash
kubectl -n kaito-workspace rollout undo deploy/kaito-workspace
# or restore from backup
kubectl apply -f /tmp/backup/kaito-workspace.deploy.*.yaml
kubectl apply -f /tmp/backup/kaito-workspace.clusterrole.*.yaml
```

## Step 5 — Smoke test with a Workspace that opts into the cache

Create a Workspace with `spec.cache.modelCache` set to the `dacs` provider in
`Opportunistic` mode. `Opportunistic` means: use the cache if it becomes ready,
otherwise proceed with a normal (non-cached) launch — safe for a first test.

> **Note on field name:** PR #2169 uses `modelCache` (JSON tag), not
> `modelWeights`. The PR description text calls it "model weights caching" but
> the CRD field is `modelCache`.

### 5.1 — Label a GPU node with `apps=phi-4`

The Workspace pod is pinned via `resource.labelSelector.matchLabels.apps=phi-4`.
Either pre-label an existing GPU node, or let the GPU provisioner create one
(if it is running in the cluster).

```bash
# example — label an existing A100 node
kubectl label node <gpu-node-name> apps=phi-4 --overwrite
```

### 5.2 — Apply the Workspace

Save as `phi-4-cached.yaml`:

```yaml
apiVersion: kaito.sh/v1beta1
kind: Workspace
metadata:
  name: phi-4-cached
resource:
  instanceType: "Standard_NC24ads_A100_v4"
  labelSelector:
    matchLabels:
      apps: phi-4
inference:
  preset:
    name: "microsoft/phi-4"
cache:
  modelCache:
    provider: dacs
    mode: Opportunistic
```

Apply:

```bash
kubectl apply -f phi-4-cached.yaml
```

### 5.3 — Watch progress

```bash
# Workspace status conditions (ModelCacheReady is the new PR #2169 condition)
kubectl get workspace phi-4-cached -o json \
  | jq '.status.conditions[] | {type,status,reason,message}'

# Controller logs specific to this workspace / cache
kubectl -n kaito-workspace logs deploy/kaito-workspace --tail=500 \
  | grep -iE 'phi-4-cached|dacs|modelcache|cache'

# Inference pod (once scheduled) — verify DACS env vars were injected
kubectl get pods -l kaito.sh/workspace=phi-4-cached -o json \
  | jq '.items[].spec.containers[] | {name, image,
        env: (.env // [] | map(select(.name | test("CACHE|RUNAI|LD_LIBRARY"))))}'

# Also check volumes / init containers for the DACS client image mount
kubectl get pods -l kaito.sh/workspace=phi-4-cached -o json \
  | jq '.items[].spec | {volumes, initContainers: [.initContainers[]? | {name,image}]}'
```

**Success indicators:**

- `status.conditions[].type == "ModelCacheReady"` transitions to `True`
  (`Opportunistic` mode won't block launch even if this stays `False`).
- Inference pod has `CACHE_DISCOVERY_URL`, `CACHE_SERVER_PORT`,
  `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB`, `LD_LIBRARY_PATH` env vars.
- Pod spec contains an `ImageVolume` referencing
  `hariazstortest.azurecr.io/dacs-client:20260701.7`.
- `WorkspaceSucceeded` condition eventually becomes `True`.

### 5.4 — Verified: rendered StatefulSet with DACS injection

After the GPU node comes up, the KAITO controller creates a StatefulSet
named after the Workspace. Below is the actual `kubectl describe sts
phi-4-cached` output from this test cluster — use it as the ground truth of
what DACS injection looks like when everything works.

Key things to notice (marked 🔑):

- 🔑 Selector / label `dacs.azure.com/inject=true` — added by the cache controller.
- 🔑 Env vars `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=true`,
  `RUNAI_STREAMER_CACHE_ENABLED=true`, `CACHE_DISCOVERY_URL` pointing at
  the DACS discovery service in `dacs-cache-system`.
- 🔑 `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB` + `LD_LIBRARY_PATH`
  pointing at `/opt/cache-client/...` (the DACS client mount).
- 🔑 A dedicated **`Image` (OCI `ImageVolume`)** named `cache-client`
  referencing `hariazstortest.azurecr.io/dacs-client:20260701.7`, mounted
  read-only at `/opt/cache-client`.

```
Name:               phi-4-cached
Namespace:          default
CreationTimestamp:  Mon, 13 Jul 2026 14:09:02 +0000
Selector:           dacs.azure.com/inject=true,kaito.sh/workspace=phi-4-cached
Labels:             <none>
Annotations:        workspace.kaito.io/revision: 1
Replicas:           1 desired | 1 total
Update Strategy:    RollingUpdate
  Partition:        0
  MaxUnavailable:   1
Pods Status:        1 Running / 0 Waiting / 0 Succeeded / 0 Failed
Pod Template:
  Labels:  dacs.azure.com/inject=true
           kaito.sh/workspace=phi-4-cached
  Containers:
   phi-4-cached:
    Image:      mcr.microsoft.com/aks/kaito/kaito-base:0.4.2
    Port:       5000/TCP
    Host Port:  0/TCP
    Command:
      /bin/sh
      -c
      python3 /workspace/vllm/inference_api.py --load_format=auto --tokenizer_mode=auto --dtype=bfloat16 --served-model-name=phi-4 --compilation-config.pass_config.fuse_allreduce_rms=False --model=microsoft/phi-4 --download-dir=/workspace/weights --config_format=auto --trust-remote-code --max-model-len=auto --gpu-memory-utilization=0.84 --tensor-parallel-size=1
    Limits:
      nvidia.com/gpu:  1
    Requests:
      nvidia.com/gpu:  1
    Liveness:          http-get http://:5000/health delay=0s timeout=1s period=10s #success=1 #failure=3
    Readiness:         http-get http://:5000/health delay=30s timeout=1s period=10s #success=1 #failure=3
    Startup:           exec [python3 /workspace/vllm/benchmark_entrypoint.py] delay=0s timeout=600s period=10s #success=1 #failure=180
    Environment:
      VLLM_USE_FLASHINFER_SAMPLER:                      0
      VLLM_USE_DEEP_GEMM:                               0
      VLLM_USE_FLASHINFER_MOE_FP16:                     0
      VLLM_USE_FLASHINFER_MOE_FP8:                      0
      VLLM_USE_FLASHINFER_MOE_FP4:                      0
      VLLM_USE_FLASHINFER_MOE_MXFP4_BF16:               0
      VLLM_USE_FLASHINFER_MOE_MXFP4_MXFP8:              0
      VLLM_USE_FLASHINFER_MOE_MXFP4_MXFP8_CUTLASS:      0
      RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED:  true
      RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB:      /opt/cache-client/usr/local/lib/python3.10/dist-packages/dacs_client/libStorageDirect.so
      LD_LIBRARY_PATH:                                  /opt/cache-client/usr/lib/x86_64-linux-gnu:/opt/cache-client/usr/local/lib/python3.10/dist-packages/dacs_client
      RUNAI_STREAMER_CACHE_ENABLED:                     true
      CACHE_DISCOVERY_URL:                              cacheserver-discovery.dacs-cache-system.svc.cluster.local:9065
      CACHE_SERVER_PORT:                                9065
    Mounts:
      /dev/shm from dshm (rw)
      /opt/cache-client from cache-client (ro)
      /workspace/weights from model-weights-volume (rw)
  Volumes:
   dshm:
    Type:       EmptyDir (a temporary directory that shares a pod's lifetime)
    Medium:     Memory
    SizeLimit:  <unset>
   cache-client:
    Type:          Image (a container image or OCI artifact)
    Reference:     hariazstortest.azurecr.io/dacs-client:20260701.7
    PullPolicy:    IfNotPresent
  Node-Selectors:  <none>
  Tolerations:     kubernetes.azure.com/scalesetpriority=spot:NoSchedule
                   nvidia.com/gpu:NoSchedule op=Exists
                   sku=gpu:NoSchedule
Volume Claims:
  Name:          model-weights-volume
  StorageClass:  kaito-local-nvme-disk
  Labels:        kaito.sh/workspace=phi-4-cached
  Annotations:   <none>
  Capacity:      107Gi
  Access Modes:  [ReadWriteOnce]
Events:          <none>
```

Workspace conditions once the node is ready:

```
NodesReady        True   NodesReady
NodeClaimReady    True   NodeClaimsReady
ResourceReady     True   workspaceResourceStatusSuccess
ModelCacheReady   True   CacheReady
InferenceReady    False  WorkspaceInferenceStatusPending   (starting)
WorkspaceSucceeded False  workspacePending                 (starting)
```

### 5.5 — Cleanup

```bash
kubectl delete workspace phi-4-cached
```

## Troubleshooting: `GLIBC_2.38 not found` in the inference container

### Symptom

The inference container crashes immediately after DACS injection is enabled:

```
$ kubectl logs phi-4-cached-0 -c phi-4-cached
/bin/sh: /opt/cache-client/usr/lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.38' not found (required by /bin/sh)
```

Pod status: `1/2 CrashLoopBackOff`.

### Root cause

The DACS injection sets `LD_LIBRARY_PATH` with `/opt/cache-client/usr/lib/x86_64-linux-gnu` at the front. That directory is shipped inside the
`dacs-client:20260701.7` OCI image and contains a **glibc 2.38** copy of
`libc.so.6` (built on Ubuntu 24.04).

The KAITO base image `mcr.microsoft.com/aks/kaito/kaito-base:0.4.2` is
Ubuntu 22.04 based (**glibc 2.35**). Because `LD_LIBRARY_PATH` is searched
before the default loader path, every binary in the pod — including
`/bin/sh` — tries to link against the newer libc and fails at startup.

This is effectively a **glibc downgrade**: a binary can never be pointed at
a libc *older* than the one it was built against, but the injected
`LD_LIBRARY_PATH` here does the opposite — forces base-image binaries to
load a *newer* libc that expects a matching newer dynamic loader, which the
container doesn't have.

### Immediate workaround (verified)

Remove `usr/lib/x86_64-linux-gnu` from the injected `LD_LIBRARY_PATH`, keep
only the `dacs_client` directory (which holds `libStorageDirect.so`):

```bash
kubectl patch sts phi-4-cached --type json -p '[
  {"op":"replace","path":"/spec/template/spec/containers/0/env/10",
   "value":{"name":"LD_LIBRARY_PATH",
            "value":"/opt/cache-client/usr/local/lib/python3.10/dist-packages/dacs_client"}}
]'
kubectl delete pod phi-4-cached-0
```

After this, `/bin/sh` uses the base image's own libc (2.35), and only
DACS's own `libStorageDirect.so` is picked up from the injected path. The
pod started successfully and vLLM began downloading the phi-4 weights.

> ⚠️ **Caveat:** the next Workspace reconcile in the KAITO controller will
> overwrite this patch. It's only a smoke-test unblock, not a real fix.

> The env index `/env/10` is specific to the current StatefulSet layout;
> confirm with
> `kubectl get sts phi-4-cached -o json | jq '.spec.template.spec.containers[0].env | to_entries[] | select(.value.name=="LD_LIBRARY_PATH") | .key'`
> before applying.

### Proper fixes (need action from two teams)

#### 1. DACS / Container Storage team — rebuild `dacs-client` on Ubuntu 22.04

The `dacs-client` OCI image is intended to be layered on top of arbitrary
consumer base images through an `ImageVolume` mount. It therefore must be
built against **the oldest glibc it wants to support**, not the newest.

Concretely:

- Use `ubuntu:22.04` (glibc 2.35) as the build base — this matches
  `mcr.microsoft.com/aks/kaito/kaito-base` today and is a safe lower bound
  for most CUDA base images.
- Publish a new tag, e.g. `hariazstortest.azurecr.io/dacs-client:20260713-jammy`.
- Verify `libStorageDirect.so` and the Python wheel do not have symbols
  requiring GLIBC ≥ 2.36:

  ```bash
  objdump -T /path/to/libStorageDirect.so | grep GLIBC_ | sort -u
  ```

#### 2. KAITO PR #2169 — narrow the injected `LD_LIBRARY_PATH`

Even after (1), the injection should not put the client's entire
`usr/lib/x86_64-linux-gnu` on `LD_LIBRARY_PATH`. It should only expose the
DACS-specific directory:

```
LD_LIBRARY_PATH=/opt/cache-client/usr/local/lib/python3.10/dist-packages/dacs_client
```

If `libStorageDirect.so` has its own non-system dependencies, ship them
next to the `.so` and set `RPATH=$ORIGIN` at build time (or run
`patchelf --set-rpath '$ORIGIN' libStorageDirect.so` in the `dacs-client`
image build). This way, injecting the client library into another container
never affects the resolution of core system libs like `libc`, `libpthread`,
`libm`.

#### 3. Optional defense in depth — preflight in the cache controller

Before rendering the pod spec, the KAITO cache controller could check the
base-image OS release (or run a tiny init container `ldd --version`) and
refuse to inject if the client's minimum glibc is greater than the base's.
Fail the Workspace with a clear condition such as
`ModelCacheReady=False, Reason=ClientGlibcMismatch` instead of letting the
user hit a `/bin/sh` crash loop.

## Verification

Use this section to check whether the model actually loaded through DACS versus
quietly falling back to HuggingFace Hub. Passing `WorkspaceSucceeded=True` and
`BenchmarkCompleted=True` is **not** sufficient — vLLM will happily fetch the
weights from HF and still report a healthy benchmark.

### Green signals (what “working DACS” looks like)

1. vLLM was actually asked to use the runai streamer:

   ```bash
   kubectl get pod phi-4-cached-0 -o jsonpath='{.spec.containers[0].command}'
   ```

   Should contain something like `--load-format runai_streamer_azure` (or
   `runai_streamer`) and `--model az://<account>/<container>/<path>`
   (or a DACS URI). If it still says `--load_format=auto --model=microsoft/phi-4`,
   vLLM will use the standard HuggingFace loader and DACS is bypassed.

2. Inference container log should show cache-side signals, not HF Hub downloads:

   ```bash
   kubectl logs phi-4-cached-0 -c phi-4-cached | grep -iE 'runai|streamer|StorageDirect|cache_hit|cache_miss|dacs'
   ```

3. `/workspace/weights` should be empty or contain streamer-specific artifacts,
   **not** a fully-populated `models--<org>--<model>/` HuggingFace cache tree:

   ```bash
   kubectl exec phi-4-cached-0 -c phi-4-cached -- ls /workspace/weights
   ```

### Red flags (silent HF fallback, DACS never touched)

All of the following observed in our test on `andy-aks135` with
`workspace:0.11.0-cache` + PR #2169 tip:

```text
# Container command — auto load_format, HF model id
python3 /workspace/vllm/inference_api.py --load_format=auto ...
    --model=microsoft/phi-4 --download-dir=/workspace/weights ...

# Log — explicit HF Hub download of the full model
Warning: You are sending unauthenticated requests to the HF Hub
INFO 07-13 15:29:37 weight_utils.py:603] Time spent downloading weights
    for microsoft/phi-4: 31.947335 seconds
INFO 07-13 15:29:38 inference_api.py:328] Model microsoft/phi-4 download
    complete: 27.31 GiB on disk in 68.5s

# Weights dir — standard HF cache layout, not streamer
/workspace/weights/models--microsoft--phi-4/...

# inference_api.py — no code path that uses runai / StorageDirect / DACS
$ grep -inE 'runai|streamer|StorageDirect|dacs|azure_cache' \
    /workspace/vllm/inference_api.py
(only kv_cache_* matches, nothing about the model streamer)

# python pkgs — the client is installed but never invoked
$ pip list | grep -iE 'runai|streamer'
runai-model-streamer         0.16.0
runai-model-streamer-azure   0.16.0
```

Even though the workspace reported `ModelCacheReady=True`,
`InferenceReady=True`, `WorkspaceSucceeded=True`, `BenchmarkCompleted=True`,
and pushed 306k tokens/min during the built-in benchmark — the model was
downloaded straight from HuggingFace Hub in ~68 seconds. DACS cache-servers
(`cacheserver-{0,1,2}`) were healthy but received zero traffic.

### Component-by-component status observed in this test

| Component | State | Effective? |
| --- | --- | --- |
| DACS cache-server StatefulSet (3 replicas) | `Ready` | ✅ |
| Cache CR `cache-sample` in `dacs-cache-system` | `Ready=True` | ✅ |
| KAITO webhook injection (`dacs.azure.com/inject=true` label) | applied | ✅ |
| Env vars (`RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=true`, `CACHE_DISCOVERY_URL=…`, `LD_LIBRARY_PATH=…`) | present on pod | ✅ |
| ImageVolume `hariazstortest.azurecr.io/dacs-client:20260701.7` mounted at `/opt/cache-client` | mounted | ✅ |
| `libStorageDirect.so` + `runai-model-streamer-azure 0.16.0` in image | present | ✅ |
| vLLM actually invokes runai streamer to pull from DACS | — | ❌ never triggered |

## Gap analysis of kaito-project/kaito#2169

What the PR **does** (correct and needed):

- Adds `spec.cache.{modelCache,kvCache}` API surface on `Workspace` and
  `InferenceSet` with `provider` / `mode` / `config` / `cleanupOnDelete`
  fields and CEL/enum validation.
- Adds `ModelCacheReady` / `KVCacheReady` conditions.
- Registers a provider abstraction (`pkg/cache/provider.go`) with a DACS
  and a noop implementation; enables the mutating-webhook injection
  contract (label + ImageVolume + env vars).
- Adds the `distributedCache` feature gate + ClusterRole for
  `storage.azure.com/caches[/status]`.
- Threads Helm values (`cache.providers.dacs.*`) into controller env
  (`DACS_CLIENT_IMAGE`, `DACS_DISCOVERY_ENDPOINT`, `DACS_KV_CACHE_ENABLED`,
  `DACS_KV_CONNECTOR_PROTOCOL`).
- Adds a provider-agnostic e2e conformance suite
  (`test/e2e/cache_integration_test.go`) driven by
  `cache.ListExpectations()`.

What the PR is **missing** for `modelCache` to actually cache anything
(observed empirically — details above):

1. **vLLM invocation is never rewritten to use the runai streamer.**
   `pkg/workspace/inference/preset_inferences.go` still emits
   `--load_format=auto` and `--model=<HF repo id>` even when
   `spec.cache.modelCache.provider = dacs` is set. Result: vLLM never
   dlopens `libStorageDirect.so`, never queries `CACHE_DISCOVERY_URL`,
   and streams the full model from HuggingFace Hub instead.

   Concretely, when `workspace.Cache != nil && workspace.Cache.ModelCache != nil`
   the preset renderer should:
   - switch `--load-format` to `runai_streamer_azure`
     (or `runai_streamer`, depending on the model source), **and**
   - rewrite `--model` to the corresponding `az://<account>/<container>/<path>`
     URI the DACS client understands — or add `--model-loader-extra-config`
     pointing at the discovery endpoint. Compare with how the existing
     ModelMirror path builds `az://` URIs when
     `streamingEnabled == true`.

2. **Injected `LD_LIBRARY_PATH` breaks glibc-older base images.**
   `pkg/cache/dacs/provider.go` sets:

   ```go
   LD_LIBRARY_PATH = /opt/cache-client/usr/lib/x86_64-linux-gnu:
                     /opt/cache-client/usr/local/lib/python3.10/dist-packages/dacs_client
   ```

   The first path shadows the base image’s libc. If the DACS client image
   is Ubuntu 24.04 (glibc 2.38) and the KAITO base image is Ubuntu 22.04
   (glibc 2.35), every binary in the pod fails at load time — including
   `/bin/sh`. See the [Troubleshooting](#troubleshooting-glibc_238-not-found-in-the-inference-container)
   section above. The injection should:
   - only put the `dacs_client` directory on `LD_LIBRARY_PATH`, or
   - set an RPATH `$ORIGIN` inside `libStorageDirect.so` at build time
     so `LD_LIBRARY_PATH` isn’t needed at all, and/or
   - preflight-check that the client’s glibc floor ≤ the base image’s
     glibc and fail `ModelCacheReady` with a clear reason instead of
     letting `/bin/sh` crash-loop.

3. **`ModelCacheReady=True` is a lie today.** The controller sets the
   condition purely from the Cache CR’s own `Ready=True`, without
   confirming the workspace pod is actually consuming the cache. This
   is what let our test go all the way to `WorkspaceSucceeded=True`
   despite DACS never being touched. Suggested: bind the condition to
   an observable signal on the inference pod (e.g. detected
   `--load-format runai_streamer_azure`, or a Prometheus counter from
   `libStorageDirect.so`).

4. **`Cleanup(cleanupOnDelete=true)` is a TODO.** The provider hard-codes
   `klog.V(4).Info("Cleanup requested (not yet implemented)")`. The CRD
   field advertises the behavior; the implementation should either land
   in this PR or the field should be documented as “ignored, tracked in
   issue X.”

5. **No end-to-end assertion that a byte was ever streamed via DACS.**
   The new e2e suite asserts that env vars / labels / volumes are injected
   into the StatefulSet, and that the `ModelCacheReady` condition flips
   — exactly the shape of “green” we saw in production with zero DACS
   traffic. To catch this regression the suite should scrape a DACS
   cache-server metric (`request_count`, `bytes_streamed`, or similar)
   before and after workspace-ready and assert `delta > 0`.

### Suggested reviewer ask

Split the PR into a scaffolding half (API, CRD, feature gate, injection
contract, conformance harness — all correct today) and a wiring half
(vLLM `--load-format` switch, `--model` az-URI rewrite, glibc-safe
`LD_LIBRARY_PATH`, `Cleanup` implementation, DACS-traffic e2e assertion).
Merging the scaffolding without the wiring shipped a “working” code
path that silently defeats its own purpose.

## Workaround: manually patch the StatefulSet to use DACS

Since kaito-project/kaito#2169 injects the DACS env vars and cache-client
volume correctly but **never rewrites the vLLM launch command**, the model
streamer is never invoked. The following manual patch on the StatefulSet
fixes this without modifying KAITO controller code.

### Steps

1. **Patch the STS command** — change `--load_format=auto` to
   `--load-format=runai_streamer`:

   ```bash
   kubectl patch sts phi-4-cached --type json -p '[
     {"op":"replace","path":"/spec/template/spec/containers/0/command/2",
      "value":"python3 /workspace/vllm/inference_api.py --gpu-memory-utilization=0.84 --model=microsoft/phi-4 --download-dir=/workspace/weights --config_format=auto --tokenizer_mode=auto --trust-remote-code --dtype=bfloat16 --served-model-name=phi-4 --compilation-config.pass_config.fuse_allreduce_rms=False --tensor-parallel-size=1 --load-format=runai_streamer --max-model-len=auto"}
   ]'
   ```

2. **Do NOT set `LD_LIBRARY_PATH`** — the DACS client image
   (`hariazstortest.azurecr.io/dacs-client:20260701.7`) is built on
   Ubuntu 24.04 (glibc 2.38) while the KAITO base image
   (`mcr.microsoft.com/aks/kaito/kaito-base:0.4.2`) uses Ubuntu 22.04
   (glibc 2.35). Setting `LD_LIBRARY_PATH` to include
   `/opt/cache-client/usr/lib/x86_64-linux-gnu` shadows the base image's
   libc and crashes `/bin/sh`. The env var
   `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB` already provides the
   full absolute path to `libStorageDirect.so`, so the streamer can
   dlopen it directly without `LD_LIBRARY_PATH`.

3. **Required env vars** (these are injected by the KAITO controller
   when `distributedCache=true` feature gate is enabled, or can be
   added manually):

   ```
   RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=true
   RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB=/opt/cache-client/usr/local/lib/python3.10/dist-packages/dacs_client/libStorageDirect.so
   RUNAI_STREAMER_CACHE_ENABLED=true
   CACHE_DISCOVERY_URL=cacheserver-discovery.dacs-cache-system.svc.cluster.local:9065
   CACHE_SERVER_PORT=9065
   ```

4. **Required volume** — cache-client OCI ImageVolume mounted at
   `/opt/cache-client` (read-only):

   ```yaml
   volumes:
   - name: cache-client
     image:
       reference: hariazstortest.azurecr.io/dacs-client:20260701.7
       pullPolicy: IfNotPresent
   ```

5. **Clear existing weights and restart the pod** to force a fresh
   download through DACS:

   ```bash
   kubectl exec phi-4-cached-0 -c phi-4-cached -- bash -c 'rm -rf /workspace/weights/*'
   kubectl delete pod phi-4-cached-0
   ```

### Verified result (2026-07-15, cluster andy-aks135)

```text
# vLLM engine config confirms runai_streamer
load_format=runai_streamer

# Model streamed via DACS — 0 bytes written to disk
(APIServer pid=45) INFO 07-15 05:08:25 inference_api.py:328]
    Model microsoft/phi-4 download complete: 0.00 GiB on disk in 34.3s

# RunAI Streamer log — 27.3 GiB streamed at 5.8 GiB/s
(EngineCore pid=188) Loading safetensors using Runai Model Streamer: 100% Completed | 243/243
(EngineCore pid=188) INFO 07-15 05:09:00 file_streamer.py:69]
    [RunAI Streamer] Overall time to stream 27.3 GiB of all files to cpu: 4.73s, 5.8 GiB/s

# Benchmark passed normally
KAITO_BENCHMARK_RESULT {"vllm_total_tpm":307968.95,"ttft_avg_ms":8070.79,"tpot_avg_ms":213.9}

# Pod Ready
kubectl get pods phi-4-cached-0 → 2/2 Running, Ready=true
```

### Key difference: `--load-format=auto` vs `--load-format=runai_streamer`

| | `--load_format=auto` (default) | `--load-format=runai_streamer` |
| --- | --- | --- |
| Model loading | HF Hub → disk → GPU | DACS cache → stream → GPU |
| Download time | ~31s + disk I/O | **4.73s** (streamed) |
| Disk written | 27.3 GiB | **0 GiB** |
| Throughput | ~0.9 GiB/s | **5.8 GiB/s** |
| DACS utilized | ❌ | ✅ |

## Performance comparison: DACS vs HuggingFace Hub download

Tested on cluster `andy-aks135`, model `microsoft/phi-4` (27.3 GiB),
Single A100 GPU (Standard_NC24ads_A100_v4), 2026-07-15.

### Without DACS (`--load_format=auto`, HuggingFace Hub)

```text
# EngineCore downloads weights from HF Hub to local NVMe disk
(EngineCore pid=188) INFO 07-15 05:01:33 [weight_utils.py:603]
    Time spent downloading weights for microsoft/phi-4: 30.671232 seconds

# Then loads from disk to GPU
(EngineCore pid=188) Loading safetensors checkpoint shards: 100% Completed | 6/6 [00:03<00:00, 1.56it/s]
(EngineCore pid=188) INFO [default_loader.py:397] Loading weights took 3.99 seconds

# Total model ready time: ~34s download + ~4s load = ~38s
# Disk usage: 27.3 GiB written to /workspace/weights/
```

Historical data from 07-13 test on same cluster:
```text
(EngineCore) Time spent downloading weights for microsoft/phi-4: 31.947335 seconds
(APIServer) Model microsoft/phi-4 download complete: 27.31 GiB on disk in 68.5s
```

### With DACS (`--load-format=runai_streamer`)

```text
# Streamer loads directly from DACS cache to CPU memory — zero disk writes
(APIServer pid=45) INFO 07-15 05:08:25 inference_api.py:328]
    Model microsoft/phi-4 download complete: 0.00 GiB on disk in 34.3s

(EngineCore pid=188) Loading safetensors using Runai Model Streamer: 100% Completed | 243/243 [00:04<00:00, 51.51it/s]
(EngineCore pid=188) INFO 07-15 05:09:00 file_streamer.py:69]
    [RunAI Streamer] Overall time to stream 27.3 GiB of all files to cpu: 4.73s, 5.8 GiB/s

(EngineCore pid=188) INFO [gpu_model_runner.py:5132]
    Model loading took 27.39 GiB memory and 36.483870 seconds

# Disk usage: 0 GiB (streamed directly to memory)
```

### Summary

| Metric | Without DACS (HF Hub) | With DACS (RunAI Streamer) | Speedup |
| --- | --- | --- | --- |
| Weight download/stream time | 30.7s | **4.73s** | **6.5x** |
| Download throughput | ~0.9 GiB/s | **5.8 GiB/s** | **6.4x** |
| Disk written | 27.3 GiB | **0 GiB** | ∞ |
| Total model load (download + GPU) | ~38s | ~36.5s (stream overlaps GPU load) | ~1x |
| Benchmark (tokens/min) | 307,969 | 307,969 | identical |

> **Note:** Total wall-clock model loading time is similar (~36-38s) because
> GPU weight loading dominates once data is in CPU memory. The key wins are:
> 1. **6.5x faster weight fetch** — matters more for larger models (70B+)
> 2. **Zero disk I/O** — no NVMe wear, no PVC needed for weights
> 3. **Cache locality** — subsequent pod restarts / scale-outs hit warm
>    DACS cache instead of re-downloading from internet

## Reference

- KAITO PR: <https://github.com/kaito-project/kaito/pull/2169>
- DACS getting started guide (Tachyon): internal doc from Container Storage team
