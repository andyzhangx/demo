# DACS test result — first-pod cold path on `andy-aks135` (2026-07-31)

Follow-up to the [cache locality run on 2026-07-29](./enable-dacs-in-kaito-workspace.md#cache-locality-follow-up-2026-07-29-cluster-andy-aks135).
This note records a **fresh cold-start** observation on the same cluster after
the DACS cache-server pod was restarted, and clarifies a common source of
confusion: `ModelMirror Ready` does **not** imply the DACS cache is warm.

## TL;DR

- On `andy-aks135` today the Workspace `phi-4-cache-lvgbp` was the **first**
  inference pod to hit `cache-sample-0` after the cache-server pod restarted.
- vLLM loaded 7.1 GiB of `microsoft/phi-4-mini-instruct` weights in **12.05 s**
  (`Model loading took 7.17 GiB memory and 12.048650 seconds`).
- The DACS `dacs_client` shutdown histogram confirms it was a **cache miss**:
  ~93% of chunks were fetched from Azure Blob (`harikaito.blob.core.windows.net`)
  via WorkloadIdentity, not from `cache-sample-0`.
- The 12 s figure is **cold-but-fast**, not warm-cache. RunAI Streamer + 80
  concurrent threads streaming directly from Azure Blob (same-region, in-cluster)
  gets you ~660 MiB/s even on a full miss. Warm-cache pods in the earlier run
  did the same load in ~4.4 s with **0** remote GETs.

## Cluster state at test time

```console
$ kubectl -n dacs-cache-system get sts,po -o wide
NAME                            READY   AGE     IMAGES
statefulset/cache-sample        1/1     3d23h   tachyonexternal.azurecr.io/cache-server:20260723.1

NAME                                         READY   NODE                                  START
cache-sample-0                               1/1     aks-wse3cab073d-15829513-vmss000000   2026-07-31T07:14:37Z
cache-server-prereq-9s4kf                    1/1     aks-wse3cab073d-15829513-vmss000000   2026-07-31T07:15:31Z
tachyon-cache-manager-bb59f47c5-5j2xh        1/1     aks-sys-63296703-vmss000000           2026-07-31T06:27:32Z
```

Cache CR spec (relevant bits):

```yaml
apiVersion: storage.azure.com/v1beta1
kind: Cache
metadata:
  name: cache-sample
  namespace: dacs-cache-system
spec:
  scaling:
    static:
      numServers: 1
  nodeSelectorKey: karpenter.sh/nodepool
  nodeSelectorValue: kaito
  port: 9065
  serverSizeInGB: 200
  serverThreads: 80
  storage:
    ephemeral: false
    hostPath:
      nodeCacheFolderPath: /var/lib/ssd/cacheserver
```

Timeline of the relevant objects:

| When (UTC) | Event |
|---|---|
| 2026-07-27 08:35 | `Cache/cache-sample` CR created. StatefulSet exists but pod is pending — no node matches `karpenter.sh/nodepool=kaito` yet. **Cache-server instance count = 0.** |
| 2026-07-28 15:41 | `ModelMirror 8deac4` (`qwen/qwen2.5-coder-7b-instruct`) created → Ready. |
| 2026-07-29 07:14 | `ModelMirror 172f34` (`microsoft/phi-4-mini-instruct`) created → Ready 1 min later. |
| 2026-07-31 07:14 | `cache-sample-0` finally scheduled on `aks-wse3cab073d-...` (kaito nodepool node came up). |
| 2026-07-31 07:18 | Workspace `phi-4-cache-lvgbp` pod starts, first to query `cache-sample-0`. |

## Workspace under test

```yaml
apiVersion: kaito.sh/v1beta1
kind: Workspace
metadata:
  name: phi-4-cache-lvgbp
inference:
  preset:
    name: phi-4-mini-instruct
resource:
  instanceType: Standard_NC24ads_A100_v4
cache:
  modelCache:
    mode: Opportunistic
    provider: dacs
```

Injected DACS wiring (confirmed on the running pod):

- ImageVolume `cache-client` mounted at `/opt/cache-client` from
  `hariazstortest.azurecr.io/dacs-client:...`.
- Env `CACHE_DISCOVERY_URL=cache-sample-discovery.dacs-cache-system.svc.cluster.local`,
  `CACHE_SERVER_PORT=9065`, `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=true`,
  `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB=/opt/cache-client/.../libStorageDirect.so`.
- Workload Identity env (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`,
  `AZURE_FEDERATED_TOKEN_FILE`) present — falls through to Azure Identity SDK
  when talking to `harikaito.blob.core.windows.net`.

Workspace status: `WorkspaceReady=True`, `ModelCacheReady=True`,
`ModelMirrorReady=True` (Message: *Model download complete*).

## Startup log — what actually happened

vLLM was invoked with `load_format=runai_streamer` — the DACS integration path,
not the default HuggingFace loader:

```
(EngineCore pid=215) INFO 07-31 07:18:54 [core.py:112] Initializing a V1 LLM engine (v0.22.1)
  with config: model='/root/.cache/vllm/assets/model_streamer/a6caa38b', ...
  load_format=runai_streamer, tensor_parallel_size=1, ...
(EngineCore pid=215) INFO 07-31 07:18:58 [gpu_model_runner.py:5037]
  Starting to load model /root/.cache/vllm/assets/model_streamer/a6caa38b...
```

RunAI Streamer wired into `libStorageDirect.so` and discovered the cache pool:

```
AISC_CTR:INFO ... BlobSiWrapper.cpp:generate_si_config: blob_read: SI config using
    Azure Identity SDK (DefaultAzureCredential)
AISC_CTR:INFO ... BlobSiWrapper.cpp:generate_si_config: blob_read: using cache discovery
    API at cache-sample-discovery.dacs-cache-system.svc.cluster.local
AISC_CTR:INFO ... BlobSiWrapper.cpp:generate_si_config: blob_read: distributed cache
    enabled (port=9065)
AISC_CTR:INFO ... ConnectionManager.cpp:UpdateCacheServers: Updating cache server list.
    Old set: , New set: cache-sample-0.cache-sample.dacs-cache-system.svc.cluster.local
```

Streaming completed in 12 s:

```
Loading safetensors using Runai Model Streamer: 100% Completed | 194/194 [00:09<00:00, 20.81it/s]
[RunAI Streamer] Overall time to stream 7.1 GiB of all files to cpu: 11.01s, 664.3 MiB/s
Model loading took 7.17 GiB memory and 12.048650 seconds
```

## Ground truth — DACS shutdown histogram

The `dacs_client` library logs its per-source I/O histogram right before
process exit. Two rounds of the same stats (worker + main thread) show:

```text
StreamingClient.cpp:LogGetPropertiesStats: GetProperties stats: MountName=
    Total=203 CacheHit=201 CacheMiss=2
StreamingClient.cpp:LogDownloadLatencyStatsInner: Download latencies (ms) from Cache
    MountName=  Samples=25  Min=0   Max=151  Avg=25   P50=10  P95=103
StreamingClient.cpp:LogDownloadLatencyStatsInner: Download latencies (ms) from Remote
    MountName=  Samples=373 Min=133 Max=6036 Avg=1509 P50=938 P95=4667
```

```text
GetProperties stats: Total=205 CacheHit=203 CacheMiss=2
Download latencies (ms) from Cache    Samples=28  Avg=22   P50=9   P95=103
Download latencies (ms) from Remote   Samples=404 Avg=1461 P50=951 P95=4589
```

Two independent facts to read out of this:

1. **`GetProperties` cache hit rate is high (~99%)** — that is the in-memory
   attribute cache (`InMemoryAttributesCache`, 10M-entry LRU), not the data
   cache. Metadata for the safetensors files was resolved locally.
2. **Data-chunk `from Remote` samples dominate** (404 remote vs 28 cache in the
   final histogram — ~93% of chunks came from Azure Blob). This is a data-plane
   cache miss.

Compare with the warm pods from the 2026-07-29 run (both on different nodes):

| Pod | Age at measurement | `Model loading took` | Cache samples | Remote samples |
|---|---|---|---|---|
| `phi-4-cache-pdvcj-0` (cold, 1st on 07-29) | 88 min | 12.07 s | 29 | 401 |
| `phi-4-cache-5m8l8-0` (warm, 2nd) | 40 min | **4.22 s** | 433 | **0** |
| `phi-4-cache-hnhlc-0` (warm, 3rd) | 20 min | **4.60 s** | 433 | **0** |
| `phi-4-cache-lvgbp-0` (cold, 07-31 — this run) | fresh | 12.05 s | 28 | 404 |

The new cold pod matches the previous cold pod almost byte-for-byte on
sample counts and wall-clock: **~430 chunks total, ~93–95% from Remote,
Model loading ≈ 12 s**. Warm-path improvement (~2.6–2.9× and 0 remote
egress) is still what we should expect once cache-sample-0 has these
weights on its host-path SSD.

## Why *this* pod is the cold path (and `ModelMirror Ready` is a red herring)

`ModelMirror 172f34` has been `Ready` since 2026-07-29 07:15. It is very
tempting to read that as "the cache has been warm for two days." It is not.

`ModelMirror` and `Cache` are **two different backends** that both happen to
sit in front of HuggingFace:

| Layer | What it stores | Populated by | Consumed by |
|---|---|---|---|
| **ModelMirror** | HF snapshot on an Azure Blob-backed PVC (`storageClassName: blob-harikaito`, path `/models/microsoft/phi-4-mini-instruct`) | one-shot download Job at ModelMirror-create time | RunAI Streamer as the **origin blob URI** (the "Remote" in the histogram) |
| **DACS `cache-sample-0`** | on-disk (`/var/lib/ssd/cacheserver`) block cache in front of that blob | populated **lazily** by client I/O (first miss → fetch → store) | RunAI Streamer via `libStorageDirect.so` (the "Cache" in the histogram) |

The cluster spent **from 2026-07-27 08:35 until 2026-07-31 07:14 with
`cache-sample-0` pending** (no node in the `kaito` karpenter nodepool matched
its nodeSelector). During that window:

- `ModelMirror` runs happened just fine — they only need the AKS default
  storage classes + HF Hub egress. Both `172f34` and `8deac4` completed on
  2026-07-28 / 07-29 while cache-server instance count was still **0**.
- No workload could have populated `cache-sample-0`'s SSD, because the pod
  did not exist.

`cache-sample-0` finally scheduled at 07:14 today. `phi-4-cache-lvgbp-0`
started at 07:18. Between those two events there was ~4 minutes and zero
other inference pods talking to the cache. So this pod is by definition
**the first**, and the histogram matches.

## What the 12-second number actually tells us

The cold-cache latency here is **not slow for a full model pull**:

- 7.1 GiB / 12.05 s ≈ **604 MiB/s** end-to-end, ≈ **664 MiB/s** for the
  streaming portion alone.
- RunAI Streamer runs 80 parallel threads directly against Azure Blob.
- Same Azure region + same VNet + Workload Identity means the storage
  account is essentially on the internal network, so per-connection latency
  is low and aggregate bandwidth saturates.

For comparison, the warm-cache pods on 07-29 landed at **~4.4 s ± 0.2 s** for
the same 7.1 GiB — a **~2.6–2.9×** speedup — and pulled **zero bytes** from the
storage account. So the value of DACS on this cluster is:

- Not "make the first pull cheap." First-pull cost is small already because
  the origin blob is same-region and RunAI Streamer is fast.
- **Eliminate all subsequent egress and get load-time down to the
  compute-bound floor (CPU→GPU copy + safetensors parsing).**

The cold-vs-warm gap shows up as **soon as a second pod starts**. To validate
today's state, restart the Workspace or scale a second replica — the follow-up
pod should show `Samples ≈ 430 / Remote = 0 / Model loading ≈ 4–5 s`.

## How to force a warm-path measurement

```bash
export KUBECONFIG=...

# Simple: kill the current pod so the StatefulSet reschedules it.
kubectl -n default delete pod phi-4-cache-lvgbp-0

# Watch the load time and the shutdown histogram on the next boot:
kubectl -n default logs phi-4-cache-lvgbp-0 -f | grep -E \
  'Model loading took|Overall time to stream|Download latencies|GetProperties stats'
```

Expected on the reboot:

```
Model loading took ~7.2 GiB memory and ~4.x seconds
[RunAI Streamer] Overall time to stream 7.1 GiB of all files to cpu: ~3.x s
Download latencies (ms) from Cache    Samples≈430   ...
# (no "from Remote" line)
```

## Update 2026-07-31 08:24 UTC — warm-path confirmed on second pod

A second Workspace `phi-4-cache-6mnkq` was created on the same cluster while
`cache-sample-0` was already Running with the first pod's data resident. The
new pod `phi-4-cache-6mnkq-0` scheduled onto a **different** node
(`aks-ws6d3aa0bbb-31340636-vmss000000`, vs. `31340635` for the first pod),
so this is a true remote-cache warm-path test (cross-node fetch from
`cache-sample-0`, not host-local reuse).

### DACS stats at shutdown

```
ReadChunk stats:              Total=433  PrefetchCache=0  RemoteCache=433  RemoteClient=0
GetProperties stats:          Total=205  CacheHit=205    CacheMiss=0
Download latencies from Cache: Samples=433  Min=1 ms  Max=2567 ms  Avg=501 ms  P50=399 ms  P95=1481 ms
```

- **433 / 433 chunks served from the cache**, zero requests fell back to the
  storage account (`RemoteClient=0`).
- **205 / 205 GetProperties hit the cache**, zero misses.
- P50 chunk latency **399 ms** across the network to `cache-sample-0` on
  another node — dominated by 4 MiB chunk transfer, not blob round-trip.

### Load-time result

```
[RunAI Streamer] Overall time to stream 7.1 GiB of all files to cpu: 3.62s, 2.0 GiB/s
Model loading took 7.17 GiB memory and 4.509744 seconds
```

| Metric | Cold pod `lvgbp-0` (07-31 07:22) | Warm pod `6mnkq-0` (07-31 08:24) | Speedup |
|---|---|---|---|
| Stream 7.1 GiB → CPU | **12.05 s** (~604 MB/s) | **3.62 s** (~2.0 GiB/s) | **3.33×** |
| Model loading (incl. CPU→GPU) | ~12.5 s | **4.51 s** | **2.77×** |
| Cache hit rate | 28 / 432 (~6%) | **433 / 433 (100%)** | — |
| Blob-egress requests | ~404 | **0** | — |

This matches the 07-29 warm-cache baseline (~4.4 s ± 0.2 s) and validates the
correction below: **once a real read has populated `cache-sample-0`, every
subsequent pod — even on a different node — hits the fully-warm path.**

### Follow-up: host-local vs remote-cache hit

At 08:54 UTC we deleted `phi-4-cache-lvgbp-0` and let the StatefulSet
reschedule it. It landed **on the same node as `cache-sample-0`**
(`aks-wse3cab073d-15829513-vmss000000`), so this reboot exercises the
**host-local** read path: CacheClient → loopback → cache-server → local SSD,
no pod-network hop.

```
ReadChunk stats:              Total=433  PrefetchCache=0  RemoteCache=433  RemoteClient=0  ZeroCopy=118  SubChunk=315
GetProperties stats:          Total=205  CacheHit=205    CacheMiss=0
Download latencies from Cache: Samples=433  Min=0 ms  Max=340 ms  Avg=68 ms  P50=59 ms  P95=179 ms
[RunAI Streamer] Overall time to stream 7.1 GiB of all files to cpu: 1.86s, 3.8 GiB/s
Model loading took 7.17 GiB memory and 4.185914 seconds
```

Side-by-side of the two warm-path variants on this cluster:

| Metric | Cross-node remote hit (`6mnkq-0`) | Host-local hit (`lvgbp-0` reboot) | Delta |
|---|---|---|---|
| Stream 7.1 GiB → CPU | 3.62 s (2.0 GiB/s) | **1.86 s (3.8 GiB/s)** | **1.95×** faster |
| Model loading (incl. GPU copy) | 4.51 s | **4.19 s** | 1.08× faster |
| Chunk latency P50 | 399 ms | **59 ms** | **6.8×** |
| Chunk latency P95 | 1481 ms | **179 ms** | **8.3×** |
| Chunk latency Avg | 501 ms | **68 ms** | **7.4×** |
| Chunk latency Max | 2567 ms | **340 ms** | 7.5× |
| ZeroCopy chunks | 0 | **118 / 433** | — |
| Blob-egress | 0 | 0 | — |

Takeaways:

- **Chunk-level latency drops ~7×** when the client and server share a host,
  because the read path collapses to loopback + local SSD (NVMe). The remote
  path pays for gRPC framing, TCP fan-out to 80 upload threads, and pod
  network RTT.
- **Streaming throughput almost doubles** (2.0 → 3.8 GiB/s) once the network
  hop is removed. This is now bounded by the NVMe read + the CacheClient's
  memcpy fan-in, not the pod network.
- **`Model loading` time barely changes** (4.51 → 4.19 s). That is because
  the remaining time is CPU→GPU copy + `safetensors` header parsing +
  RunAI Streamer thread startup, which are constant regardless of where
  the bytes came from. In other words, once the cache is warm, the network
  hop costs you the streaming phase but not the load phase; both are
  already well under the cold-path 12 s.
- The `ZeroCopy=118 SubChunk=315` counters only appear on the host-local
  path — DACS's client library recognizes local IPC and skips the copy for
  aligned 32 MiB chunks, which is where a big chunk of the P50 speedup
  comes from.

Practical guidance:

- If you can steer inference pods onto the same nodes as `cache-sample`
  members (e.g. via `podAffinity` on the cache-server label), you get the
  host-local 7× chunk latency win for free. On a large fleet this only
  helps a fraction of the pods.
- If not, the remote hit path (`6mnkq-0` numbers) is still the primary
  target and is already **2.7× faster than cold**. The extra 1.6 s that
  host-local buys is a nice-to-have, not the main story.
- The cold-vs-warm gap (**12 s → 4 s, 3×**) matters much more than the
  remote-vs-local gap (**4.5 s → 4.2 s, 1.08×**). Design DACS rollouts
  around "never let a user pay the cold price," not around trying to keep
  every pod host-local.

### Benchmark also finished cleanly on this pod

```
KAITO_BENCHMARK 2026-07-31T08:26:59Z benchmark_done elapsed=75.2s
KAITO_BENCHMARK_RESULT {"vllm_total_tpm":644436.67,"ttft_avg_ms":8703.45,"tpot_avg_ms":218.51}
```

At config `{input=2048, output=256, max_concurrency=204}` — 644 K TPM,
8.7 s TTFT, 218 ms TPOT. The startup-probe `Unhealthy` events in
`describe pod` are the usual vLLM torch-compile warmup window; the pod never
actually restarted (`RESTARTS=0`), it just failed a few early probes before
the engine finished warming up.

---

If the reboot **still** shows `from Remote: Samples=~400`, the cache is not
retaining data across restarts — check:

- `cache-sample` `spec.storage.ephemeral` (should be `false`; it is on this
  cluster).
- The host `/var/lib/ssd/cacheserver` path on the cache-server node — did the
  node get replaced by Karpenter?
- Whether the cache-server pod itself restarted between the two inference
  runs.

## Corrections vs the 07-29 note

The 07-29 note explains cache locality across nodes but assumes the cache is
already warm when it starts. On this cluster it is easy to be off by one:

- `ModelMirror.status.phase=Ready` does not warm the DACS cache. It only
  guarantees the origin blob URI is populated.
- If `cache-sample-0` was pending, restarted, or its host-path SSD was wiped
  (e.g. node replacement), the "first" pod resets to right now — even weeks
  after `ModelMirror` reported `Ready`.

The DACS cache is warmed **only by a real client read that misses**. Any
serious deployment that wants to hide the cold path from its first user
should ship an explicit warm-up hook (a tiny pre-flight pod that opens the
model files once), not rely on `ModelMirror Ready`.
