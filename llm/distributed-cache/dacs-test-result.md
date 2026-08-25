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

All pods below load the same model: **`microsoft/phi-4-mini-instruct`** — 194 `.safetensors` shards, **7,672,066,216 bytes total (≈7.15 GiB / 7.14 GiB reported by RunAI Streamer)**, staged at `/root/.cache/vllm/assets/model_streamer/a6caa38b` and served via `load_format=runai_streamer`.

| Pod | Age at measurement | `Model loading took` | Cache samples | Remote samples |
|---|---|---|---|---|
| `phi-4-cache-pdvcj-0` (cold, 1st on 07-29) | 88 min | 12.07 s | 29 | 401 |
| `phi-4-cache-5m8l8-0` (warm, 2nd) | 40 min | **4.22 s** | 433 | **0** |
| `phi-4-cache-hnhlc-0` (warm, 3rd) | 20 min | **4.60 s** | 433 | **0** |
| `phi-4-cache-lvgbp-0` (cold, 07-31 07:18 — first-ever boot) | fresh | 12.05 s | 28 | 404 |
| `phi-4-cache-6mnkq-0` (07-31 08:22, cross-node warm) | fresh | **4.51 s** | 433 | **0** |
| `phi-4-cache-lvgbp-0` (07-31 08:55, **host-local warm** — reboot, same node as `cache-sample-0`) | fresh | **4.19 s** | 433 | **0** |
| `phi-4-cache-qtzp8-0` (07-31 09:57, cross-node warm) | fresh | **4.40 s** | 433 | **0** |
| `qwen3-coder-30b-a3b-instruct-8jdxx-0` (07-31 14:01, cold, different model) | fresh | n/a (log rolled) | — | — |
| `qwen3-coder-30b-a3b-instruct-8jdxx-0` (07-31 14:38, **host-local warm** after reboot, same node as `cache-sample-0`) | fresh | **17.13 s** | 20729 | **0** |
| `qwen3-coder-30b-a3b-instruct-66nj8-0` (07-31 15:26, **partial cold** — same node as `cache-sample-0` but cache empty after restart) | fresh | **211.01 s** | 6169 | **14543** |
| `qwen3-coder-30b-a3b-instruct-786qr-0` (08-01 02:19, **cross-node warm**, different node) | fresh | **27.52 s** | 20729 | **0** |
| `qwen3-coder-30b-a3b-instruct-82l2f-0` (08-01 02:39, **cross-node warm**, different node) | fresh | **28.19 s** | 20729 | **0** |

### 2026-07-31 14:38 UTC — qwen3-coder-30b-a3b-instruct, host-local warm reboot

After the cold fill above finished, `qwen3-coder-30b-a3b-instruct-8jdxx-0`
was deleted and the StatefulSet recreated it at `14:38:57Z`. The new
instance again landed on `aks-ws467f12d19-35590499-vmss000000`, which is
the same node as `cache-sample-0` (still the same cache-server instance,
created 12:42:47Z, now warm from the 14:01 fill). This is the host-local
warm path for a 56.9 GiB model.

```
ReadChunk stats:           Total=20729  PrefetchCache=0  RemoteCache=20729  RemoteClient=0  ZeroCopy=34  SubChunk=20695
ReadFile requested stats:  TotalReads=18913  128k=213  4MB=18602  100MB=96  1GB=2  TotalBytes=61066575656 (56.87 GiB)
GetProperties stats:       Total=18913  CacheHit=18913  CacheMiss=0
Download latencies from Cache: Samples=1000  Min=0 ms  Max=28 ms  Avg=3 ms  P50=2 ms  P95=11 ms
[RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 16.11s, 3.5 GiB/s
Model loading took 56.93 GiB memory and 17.130801 seconds
KAITO_BENCHMARK_RESULT { "vllm_total_tpm": 315276.13, "ttft_avg_ms": 0.0, "tpot_avg_ms": 59.71 }
```

Compared to the cold fill above (~57 GiB pulled from Blob in ~3 min
aggregate) the same 56.9 GiB now streams to CPU in **16.11 s** — an
~11× wall-clock speedup on the model data path. This mirrors the
rebooted phi-4 `lvgbp-0` result (host-local IPC + ZeroCopy) but with
even better chunk latency (P50 2 ms here vs 59 ms for phi-4). Two
interesting differences from phi-4:

- Model is 56.9 GiB / 18,913 files vs 7.15 GiB / 205 files for phi-4;
  the majority of ReadFile calls fall in the 4 MB bucket (`4MB=18602`)
  which is exactly the Qwen3 safetensors shard granularity.
- `ZeroCopy=34` out of 20,729 chunks (~0.16 %) vs `ZeroCopy=118 / 433`
  (~27 %) for phi-4 lvgbp-0. Almost all Qwen3 reads go through the
  SubChunk path (`SubChunk=20695`), which suggests the 32 MiB chunk
  alignment is worse for these larger shards; the aggregate throughput
  is still 3.5 GiB/s because of the same-host loopback bandwidth.

All 56.87 GiB of the model is now proven cache-resident: `GetProperties`
100 % hit, `RemoteCache=20729/20729`, `RemoteClient=0`. The next
qwen3-coder-30b-a3b pod that lands on this node will hit this same
host-local path.

---

### 2026-07-31 15:26 UTC — qwen3-coder-30b-a3b-instruct-66nj8-0, partial cold (cache empty after restart)

A new Workspace `qwen3-coder-30b-a3b-instruct-66nj8` was created on
`aks-wsbba1b3935-46884430-vmss000000` — the **same node** as
`cache-sample-0`. However, `cache-sample-0` had been restarted at
15:08 UTC with an empty snapshot, so this pod paid nearly the full
cold-path cost despite co-location.

```
ReadChunk stats:           Total=20729  PrefetchCache=17  RemoteCache=6169  RemoteClient=14543  ZeroCopy=0  SubChunk=20695
GetProperties stats:       Total=18913  CacheHit=18897  CacheMiss=16
Download latencies from Cache:  Samples=1000  Min=0 ms   Max=30 ms    Avg=1 ms   P50=1 ms   P95=4 ms
Download latencies from Remote: Samples=1000  Min=203 ms Max=1895 ms  Avg=533 ms P50=483 ms P95=955 ms
[RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 209.92s, 277.4 MiB/s
Model loading took 56.93 GiB memory and 211.007970 seconds
```

- **30% cache hit / 70% blob-direct** — the cache was filling concurrently
  as the pod read. RemoteCache fraction climbed during the load, but the
  majority of chunks still had to be fetched from Azure Blob.
- Cache latency (P50=1 ms) is excellent when it hits; blob latency
  (P50=483 ms) dominates the overall load time.
- **12.3× slower than the pure warm reboot** (17.13 s vs 211.01 s) despite
  being on the same node as cache-sample-0.

Key insight: same-node co-location means nothing if the cache is empty.
The cache must be populated before co-location benefits kick in.

---

### 2026-08-01 02:19 UTC — qwen3-coder-30b-a3b-instruct-786qr-0, cross-node warm

A new Workspace `qwen3-coder-30b-a3b-instruct-786qr` created on
`aks-ws847b6ecb9-52652368-vmss000000`, a **different node** from
`cache-sample-0` (`aks-wsbba1b3935-46884430-vmss000000`). By this time
the cache was fully populated (56.87 GiB stable from the earlier fills).

```
ReadChunk stats:           Total=20729  PrefetchCache=0  RemoteCache=20729  RemoteClient=0  ZeroCopy=34  SubChunk=20695
GetProperties stats:       Total=14759  CacheHit=14759  CacheMiss=0
Download latencies from Cache: Samples=1000  Min=1 ms  Max=397 ms  Avg=49 ms  P50=49 ms  P95=79 ms
[RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 26.37s, 2.2 GiB/s
Model loading took 56.93 GiB memory and 27.515194 seconds
```

- **100% cache hit, 0 blob requests** — fully served from the warm
  remote cache over the pod network.
- Cross-node cache latency P50=49 ms is higher than the host-local
  P50=2 ms (8jdxx-0 warm reboot), but still delivers 2.2 GiB/s aggregate
  streaming throughput.
- **7.7× faster than the partial-cold 66nj8-0** (27.52 s vs 211.01 s),
  confirming that cache warmth matters far more than node proximity.

---

### 2026-08-01 02:39 UTC — qwen3-coder-30b-a3b-instruct-82l2f-0, cross-node warm

A third Workspace `qwen3-coder-30b-a3b-instruct-82l2f` on yet another
node `aks-wsc586f63e2-37137876-vmss000000`, also remote from
`cache-sample-0`.

```
ReadChunk stats:           Total=20729  PrefetchCache=0  RemoteCache=20729  RemoteClient=0  ZeroCopy=34  SubChunk=20695
GetProperties stats:       Total=14881  CacheHit=14881  CacheMiss=0
Download latencies from Cache: Samples=1000  Min=1 ms  Max=304 ms  Avg=46 ms  P50=47 ms  P95=78 ms
[RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 25.93s, 2.2 GiB/s
Model loading took 56.93 GiB memory and 28.188675 seconds
```

- Near-identical to 786qr-0: 100% cache hit, P50=47 ms, 2.2 GiB/s.
- The two cross-node warm pods sit within noise of each other on every
  metric (stream 25.93–26.37 s, model loading 27.52–28.19 s, P50 47–49 ms),
  confirming the remote warm path is stable and reproducible for the
  56.9 GiB Qwen3-Coder-30B-A3B-Instruct model.

### Qwen3-Coder-30B-A3B comparison summary (3 latest pods)

| Metric | 66nj8-0 (partial cold) | 786qr-0 (cross-node warm) | 82l2f-0 (cross-node warm) |
|---|---|---|---|
| Created | 07-31 15:26 UTC | 08-01 02:19 UTC | 08-01 02:39 UTC |
| Node | wsbba1b3935 (same as cache) | ws847b6ecb9 | wsc586f63e2 |
| Model loading | **211.01 s** | **27.52 s** | **28.19 s** |
| Stream speed | 277 MiB/s | 2.2 GiB/s | 2.2 GiB/s |
| Cache hit % | 30% | **100%** | **100%** |
| RemoteCache chunks | 6169 | 20729 | 20729 |
| RemoteClient (blob) chunks | 14543 | 0 | 0 |
| Cache P50 latency | 1 ms | 49 ms | 47 ms |
| Blob P50 latency | 483 ms | — | — |
| Speedup vs 66nj8 | 1× | **7.7×** | **7.5×** |

**Key conclusion:** Cache warmth is the dominant factor. Warm cross-node
(7.5–7.7×) vastly outperforms cold same-node (1×). Once the cache is
populated, cross-node overhead is minimal — P50 latency ~50 ms, aggregate
throughput 2.2 GiB/s, model loading ~28 s for 56.9 GiB.

---

### 2026-07-31 14:01 UTC — different model (Qwen3-Coder-30B-A3B-Instruct), cold via CacheServer restart

A new Workspace `qwen3-coder-30b-a3b-instruct-8jdxx` was created after
`cache-sample-0` had been restarted at `13:57:15 UTC` on the same node
`aks-ws467f12d19-35590499-vmss000000`. On startup the CacheServer
reported *"Snapshot enabled but no snapshot found, will start with empty
cache"*, so this run is a **cold** measurement even though the pod itself
is on the same node as the cache server. The model is different from the
phi-4 runs above:

- Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct` (`az://pvc-04139f8b-…/Qwen/Qwen3-Coder-30B-A3B-Instruct`).
- vLLM args: `--load-format=runai_streamer`, `--tensor-parallel-size=1`,
  `--dtype=bfloat16`, `--gpu-memory-utilization=0.84`.
- DACS envs: `RUNAI_STREAMER_CACHE_ENABLED=true`,
  `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=true`,
  `CACHE_DISCOVERY_URL=cache-sample-discovery.dacs-cache-system.svc.cluster.local`,
  `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB=/opt/cache-client/…/libStorageDirect.so`.

The client-side `LogReadChunkStats` / `Model loading took` lines were
already rotated out of `kubectl logs` by ~33 min of ASGI errors before I
got to look (`kubectl logs … --limit-bytes=5000000` starts at 14:34), so
there is no client-side histogram to report for this run.

Instead, the ground-truth signal comes from the CacheServer side. The
`Server.cpp:CacheServerSizeBackgroundThread(318)` size samples during
the cache fill were:

| Time (UTC) | Cache size | Delta | Note |
|---|---:|---:|---|
| 13:57:15 | 0.00 GiB | — | cache-sample-0 just (re)started, empty snapshot |
| 14:03:15 | 11.14 GiB | +11.14 GiB | ~2 min after qwen3 pod start, first non-zero |
| 14:04:15 | 28.48 GiB | +17.34 GiB | ~296 MB/s |
| 14:05:15 | 43.69 GiB | +15.21 GiB | ~260 MB/s |
| 14:06:15 | 56.87 GiB | +13.19 GiB | ~225 MB/s |
| 14:06:15 onward | **56.87 GiB stable (28.4 % of 214.7 GiB limit)** | 0 | fill complete |

Takeaway:

- DACS is wired in (env + sidecar + `--load-format=runai_streamer` +
  `az://` model URL), but this run is *cold* because CacheServer was
  restarted 4 min before the pod — the co-location advantage of
  same-node cache-sample-0 does not help when the cache itself has to
  fetch from Blob first.
- **~57 GiB pulled from Azure Blob into the local cache in ~3 min,
  aggregate ~300 MB/s (~2.4 Gbps)**. That is the blob-egress ingest rate
  for Qwen3-Coder-30B-A3B-Instruct on this cluster/subscription.
- The cache is now populated for this model: a subsequent pod for the
  same Workspace on the same node should hit the **host-local warm**
  path (analogous to the rebooted `lvgbp-0` row above); a pod on a
  different node would go the **cross-node warm** path (analogous to
  `6mnkq-0`/`qtzp8-0`).

---

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

## Update 2026-07-31 10:00 UTC — third pod, fresh cross-node warm confirmation

A third Workspace `phi-4-cache-qtzp8` was created after `6mnkq-0` and after
`lvgbp-0` had been rebooted (see previous section — the rebooted `lvgbp-0`
landed co-resident with `cache-sample-0`, host-local path). The new pod
`phi-4-cache-qtzp8-0` scheduled on a **different node**
(`aks-wsc6ea289c3-21453539-vmss000000`) than `cache-sample-0`
(`aks-wse3cab073d-15829513-vmss000000`), so this is a second
cross-node remote-cache hit, independent of `6mnkq-0`.

### DACS stats and load time

```
ReadChunk stats:              Total=433  PrefetchCache=0  RemoteCache=433  RemoteClient=0  ZeroCopy=118  SubChunk=315
GetProperties stats:          Total=205  CacheHit=205    CacheMiss=0
Download latencies from Cache: Samples=433  Min=1 ms  Max=2164 ms  Avg=510 ms  P50=436 ms  P95=1388 ms
[RunAI Streamer] Overall time to stream 7.1 GiB of all files to cpu: 3.45s, 2.1 GiB/s
Model loading took 7.17 GiB memory and 4.395175 seconds
KAITO_BENCHMARK_RESULT { "vllm_total_tpm": 644633.19, "ttft_avg_ms": 8584.53, "tpot_avg_ms": 216.94 }
```

Almost identical to `6mnkq-0`. Both cross-node warm pods land in the same
band — this is the reproducible remote-hit path on this cluster.

### Correction: `lvgbp-0` is *originally* the cold-start pod, not a warm one

Earlier chat analysis compared the three currently-Running pods
(`6mnkq-0`, `lvgbp-0`, `qtzp8-0`) as three warm-cache measurements and
ascribed `lvgbp-0`'s 3.8 GiB/s streaming rate to "node/network bandwidth
 differences." That is wrong — this section is the record of the correction.

The **original** `phi-4-cache-lvgbp-0` (first-ever boot at 07:18 UTC on
2026-07-31) is the cold-start pod on this cluster and is the one documented
in the top of this file (Samples=28 Cache / 404 Remote, `Model loading took
12.05 s`). At 08:54 UTC we deliberately deleted it to force a warm-path
measurement; the StatefulSet recreated `lvgbp-0` and — by chance — placed
the new instance on `aks-wse3cab073d-15829513-vmss000000`, the same node
that runs `cache-sample-0`. That reboot is the pod currently visible in
`kubectl get pods` under the same name `lvgbp-0` (`creationTimestamp
2026-07-31T08:55:11Z`), and it is the **host-local warm** measurement, not
a fresh cold start.

All three currently-Running pods are consistent once you stop calling the
current `lvgbp-0` a plain warm hit:

| Pod | Node | Same node as `cache-sample-0`? | Path | Stream time | Model loading | Chunk P50 |
|---|---|---|---|---:|---:|---:|
| Original `lvgbp-0` (07:18, cold) | `wse3cab073d-...` | yes | first-write, remote (blob) | 11.01 s (664 MiB/s) | 12.05 s | Cache=10 ms / Remote=938 ms |
| Rebooted `lvgbp-0` (08:55, warm) | `wse3cab073d-...` | **yes** | **host-local warm** | **1.86 s (3.8 GiB/s)** | **4.19 s** | **59 ms** |
| `6mnkq-0` (08:22, warm) | `ws6d3aa0bbb-...` | no | cross-node warm | 3.62 s (2.0 GiB/s) | 4.51 s | 399 ms |
| `qtzp8-0` (09:57, warm) | `wsc6ea289c3-...` | no | cross-node warm | 3.45 s (2.1 GiB/s) | 4.40 s | 436 ms |

Take-home:

- The speedup of the rebooted `lvgbp-0` over `6mnkq-0`/`qtzp8-0` is **not**
  "different node hardware / different cache-server headroom." It is the
  host-local optimization: same-host CacheClient → cache-server loopback,
  aligned 32 MiB chunks use `ZeroCopy=118` and the client-side memcpy fan-in
  runs at NVMe read speed. The section "Follow-up: host-local vs
  remote-cache hit" above already documents this correctly.
- The two cross-node warm pods (`6mnkq-0`, `qtzp8-0`) sit within noise of
  each other on every metric (stream time 3.45–3.62 s, model loading
  4.40–4.51 s, chunk P50 399–436 ms), which confirms that once the cache
  is populated the remote path is stable across kaito nodes.
- The cold path (original `lvgbp-0`) is not represented in the current pod
  list; do not read the currently-Running `lvgbp-0` as a cold measurement.
  If you want to reproduce cold, delete the Workspace, evict
  `cache-sample-0`'s host-path SSD, and start over.

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

---

## 2026-08-04 — new cluster, InferenceSet scale-out (3 pods)

A fresh cluster (`westeurope`, storage account `harikaito`) with a
single `cache-sample-0` on `aks-ws3ec2a5685-34418831-vmss000000`. An
InferenceSet `qwen3-coder-30b-a3b-instruct` with `replicas: 3` was
created; the first pod (`mvnsn-0`) landed on the same node as
`cache-sample-0` and had to fill the cache from Blob, then two more
replicas (`nw6lw-0`, `cx64z-0`) came up on different nodes and drove
the cache into cross-node warm.

This run confirms end-to-end that Kaito's
[Model Mirror and Streaming](https://kaito-project.github.io/kaito/docs/model-mirror-streaming)
is active on this cluster:

```console
$ kubectl get modelmirror
NAME     MODEL                               PHASE   AGE
172f34   microsoft/phi-4-mini-instruct       Ready   5d21h
43903f   Qwen/Qwen3-Coder-30B-A3B-Instruct   Ready   3d14h
8deac4   qwen/qwen2.5-coder-7b-instruct      Ready   6d13h

$ kubectl get pvc -A | grep pvc-04139f8b
default  43903f  Bound  pvc-04139f8b-4c55-41b0-ad83-039aa18194eb  136Gi  RWX  blob-harikaito
```

The ModelMirror `43903f` has been `Ready` for 3d14h — every subsequent
Workspace on this cluster reuses the blob-backed PVC and never touches
HuggingFace. The vLLM invocation on every pod uses:

```
--load-format=runai_streamer
--model=az://pvc-04139f8b-4c55-41b0-ad83-039aa18194eb/Qwen/Qwen3-Coder-30B-A3B-Instruct
```

which points RunAI Streamer at the mirrored PVC. On top of Streaming,
the DACS `libStorageDirect.so` intercept layer routes the reads
through `cache-sample-0` before falling back to
`harikaito.blob.core.windows.net`.

### 2026-08-04 02:58 UTC — `mvnsn-0`, host-local partial cold (first pod, fills the cache)

Workspace `qwen3-coder-30b-a3b-instruct-mvnsn` was the first pod on
this cluster to read `Qwen3-Coder-30B-A3B-Instruct`. It landed on
`aks-ws3ec2a5685-...`, which is the **same node** as `cache-sample-0`,
but the DACS cache had zero chunks for this model — so this is the
**host-local partial-cold** pattern (same layout as `66nj8-0` in the
earlier run).

DACS wiring confirmed on the pod:

- Sidecar `cache-client` ImageVolume from
  `hariazstortest.azurecr.io/dacs-client:20260714.10` mounted at
  `/opt/cache-client`.
- Envs: `RUNAI_STREAMER_CACHE_ENABLED=true`,
  `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=true`,
  `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB=/opt/cache-client/usr/local/lib/python3.10/dist-packages/dacs_client/libStorageDirect.so`,
  `CACHE_DISCOVERY_URL=cache-sample-discovery.dacs-cache-system.svc.cluster.local`,
  `CACHE_SERVER_PORT=9065`.
- Workload Identity envs (`AZURE_CLIENT_ID=20b065b7-5981-455a-ad3b-a2cdb32bd48c`,
  `AZURE_TENANT_ID`, `AZURE_FEDERATED_TOKEN_FILE`) present.

Startup log:

```
(EngineCore pid=242) INFO 08-04 03:01:27 [core.py:112] Initializing a V1 LLM engine (v0.22.1)
  with config: model='/root/.cache/vllm/assets/model_streamer/a301d1bf', load_format=runai_streamer, ...
(EngineCore pid=242) INFO 08-04 03:01:31 [gpu_model_runner.py:5037]
  Starting to load model /root/.cache/vllm/assets/model_streamer/a301d1bf...
AISC_CTR:INFO ... BlobSiWrapper.cpp:generate_si_config: blob_read: SI config using Azure Identity SDK (DefaultAzureCredential)
AISC_CTR:INFO ... BlobSiWrapper.cpp:generate_si_config: blob_read: using cache discovery API at cache-sample-discovery.dacs-cache-system.svc.cluster.local
AISC_CTR:INFO ... BlobSiWrapper.cpp:generate_si_config: blob_read: distributed cache enabled (port=9065)
AISC_CTR:INFO ... ConnectionManager.cpp:UpdateCacheServers: New set: cache-sample-0.cache-sample.dacs-cache-system.svc.cluster.local
AISC_CTR:INFO ... BlobClient.cpp:GetBlobClient: Creating new blob client for account=harikaito, endpoint=https://harikaito.blob.core.windows.net
(EngineCore pid=242) Loading safetensors using Runai Model Streamer: 100% Completed | 18867/18867 [03:44<00:00, 84.17it/s]
(EngineCore pid=242) INFO 08-04 03:05:21 file_streamer.py:69] [RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 228.8s, 254.5 MiB/s
(EngineCore pid=242) INFO 08-04 03:05:22 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 229.909696 seconds
```

Final DACS shutdown histogram:

```text
ReadChunk stats:           Total=20729  PrefetchCache=32  RemoteCache=5053  RemoteClient=15644  ZeroCopy=0  SubChunk=20695
ReadFile requested stats:  TotalReads=18913  128k=213  4MB=18602  100MB=96  1GB=2  TotalBytes=61066575656 (56.87 GiB)
GetProperties stats:       Total=18913  CacheHit=18897  CacheMiss=16
Download latencies from Cache:  Samples=1000  Min=0 ms   Max=33 ms    Avg=1 ms    P50=1 ms    P95=6 ms
Download latencies from Remote: Samples=1000  Min=191 ms Max=2484 ms  Avg=508 ms  P50=469 ms  P95=965 ms
```

**Data plane: ~75.5 % of chunks (15,644 / 20,729) came from Blob** —
the cache was populated **by this pod as it read**. Same-node
co-location with `cache-sample-0` does not help when the cache is
empty for this model; `cache-sample-0` itself has to fetch from Blob.

### 2026-08-04 04:39 UTC — `nw6lw-0` + `cx64z-0`, cross-node warm (InferenceSet scale-out)

After `mvnsn-0` finished filling the cache, the InferenceSet scaled
out to 3 replicas. Two new pods came up on different nodes:

```console
$ kubectl -n default get pods -l inferenceset.kaito.sh/created-by=qwen3-coder-30b-a3b-instruct -o wide
NAME                                   READY   NODE
qwen3-coder-30b-a3b-instruct-cx64z-0   1/1     aks-ws6b2df096c-16013696-vmss000000
qwen3-coder-30b-a3b-instruct-mvnsn-0   1/1     aks-ws3ec2a5685-34418831-vmss000000
qwen3-coder-30b-a3b-instruct-nw6lw-0   1/1     aks-ws85c688f12-27197094-vmss000000
```

Both `nw6lw-0` and `cx64z-0` are on nodes **different from**
`cache-sample-0` — this is the cross-node warm path.

Startup log — `nw6lw-0`:

```
(EngineCore pid=248) INFO 08-04 04:40:32 [gpu_model_runner.py:5037] Starting to load model /root/.cache/vllm/assets/model_streamer/a301d1bf...
(EngineCore pid=248) Loading safetensors using Runai Model Streamer: 100% Completed | 18867/18867 [00:44<00:00, 420.27it/s]
(EngineCore pid=248) INFO 08-04 04:41:18 file_streamer.py:69] [RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 45.19s, 1.3 GiB/s
AISC_CTR:INFO ... ReadChunk stats: Total=20729 PrefetchCache=0 RemoteCache=20729 RemoteClient=0 ZeroCopy=34 SubChunk=20695
AISC_CTR:INFO ... GetProperties stats: Total=18913 CacheHit=18913 CacheMiss=0
(EngineCore pid=248) INFO 08-04 04:41:19 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 46.132885 seconds
```

Startup log — `cx64z-0`:

```
(EngineCore pid=250) INFO 08-04 04:40:38 [gpu_model_runner.py:5037] Starting to load model /root/.cache/vllm/assets/model_streamer/a301d1bf...
(EngineCore pid=250) Loading safetensors using Runai Model Streamer: 100% Completed | 18867/18867 [00:46<00:00, 410.00it/s]
(EngineCore pid=250) INFO 08-04 04:41:25 file_streamer.py:69] [RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 46.39s, 1.2 GiB/s
AISC_CTR:INFO ... ReadChunk stats: Total=20729 PrefetchCache=0 RemoteCache=20729 RemoteClient=0 ZeroCopy=34 SubChunk=20695
AISC_CTR:INFO ... GetProperties stats: Total=18913 CacheHit=18913 CacheMiss=0
(EngineCore pid=250) INFO 08-04 04:41:26 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 47.367450 seconds
```

**Both new pods: `RemoteClient=0` — zero Blob egress; 100 % of the
20,729 chunks came from `cache-sample-0`. `ZeroCopy=34` also appears
(vs 0 on `mvnsn-0`), the warm-path optimization is taking effect.**

### Qwen3-Coder-30B-A3B comparison summary (3 latest pods, same cluster, 2026-08-04)

All three pods load the same 56.87 GiB model
(`Qwen/Qwen3-Coder-30B-A3B-Instruct`, 18,913 files, 20,729 33-MiB
chunks) via `--load-format=runai_streamer` from
`az://pvc-04139f8b-.../Qwen/Qwen3-Coder-30B-A3B-Instruct`. What
differs is the DACS cache state each pod hits.

| Pod | Created (UTC) | Node vs `cache-sample-0` | Scenario | `Model loading` | RunAI stream speed | RunAI wall-clock | RemoteCache | RemoteClient (blob) | ZeroCopy | Data cache hit % | Cache lat P50 / P95 (final) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `qwen3-coder-30b-a3b-instruct-mvnsn-0` | 02:58:44 | **same** (`ws3ec2a5685`) | **host-local partial cold** (fills cache) | **229.91 s** | 254.5 MiB/s | 228.8 s | 5,053 | **15,644** | 0 | **24.4 %** | 1 ms / 6 ms |
| `qwen3-coder-30b-a3b-instruct-nw6lw-0` | 04:39:xx | different (`ws85c688f12`) | **cross-node warm** | **46.13 s** | 1.3 GiB/s | 45.19 s | 20,729 | **0** | 34 | **100 %** | 98 ms / 209 ms |
| `qwen3-coder-30b-a3b-instruct-cx64z-0` | 04:39:xx | different (`ws6b2df096c`) | **cross-node warm** | **47.37 s** | 1.2 GiB/s | 46.39 s | 20,729 | **0** | 34 | **100 %** | 48 ms / 82 ms |

Wall-clock speedup vs the first pod:

| Pod | Speedup vs `mvnsn-0` |
|---|---:|
| `mvnsn-0` (host-local partial cold, cache fill) | 1× |
| `nw6lw-0` (cross-node warm) | **4.98×** |
| `cx64z-0` (cross-node warm) | **4.85×** |

### Takeaways

- **Model Mirror + Streaming is in use.** `ModelMirror 43903f` has
  been `Ready` for 3d14h; every pod streams from
  `pvc-04139f8b-...` via `--load-format=runai_streamer` and never
  touches HuggingFace. This is the Kaito
  [Model Mirror and Streaming](https://kaito-project.github.io/kaito/docs/model-mirror-streaming)
  path.
- **DACS is layered on top of Streaming.** RunAI Streamer's reads go
  through `libStorageDirect.so` → `cache-sample-0` → Blob. When the
  cache has the chunks, Blob is skipped entirely.
- **The 254.5 MiB/s on `mvnsn-0` is not a Streaming regression** — it
  is the one-time DACS cache-fill cost. Compare with the earlier
  cross-cluster reference of `--load-format=auto` from HuggingFace
  (~0.9 GiB/s at best): the very next replicas on this cluster
  (`nw6lw-0` / `cx64z-0`) do 1.2–1.3 GiB/s, matching or exceeding HF
  direct download and with **zero Blob egress**.
- **Cross-node warm on this cluster is ~1.2–1.3 GiB/s**, slightly
  slower than the 2.2 GiB/s in the 08-01 reference run because both
  `nw6lw-0` and `cx64z-0` hit the **single** `cache-sample-0`
  concurrently and share its network / worker threads; `cx64z-0`
  started ~6 s later and already sees P50 48 ms vs `nw6lw-0`'s 98 ms.
- **Expected next data point:** if a 4th replica lands on
  `aks-ws3ec2a5685-...` (same node as `cache-sample-0`), it should
  see the **host-local warm** path — model loading ≈ 17–20 s at
  ~3.5 GiB/s (analogous to `8jdxx-0` in the earlier run).

Investment-vs-payoff view of DACS on this cluster:

| Phase | Pod | Cost / Payoff |
|---|---|---|
| **Investment** | `mvnsn-0` | 229.9 s (pod also filled the shared cache from Blob) |
| **Payoff #1** | `nw6lw-0` | 46.1 s (5× faster, 0 Blob egress) |
| **Payoff #2** | `cx64z-0` | 47.4 s (5× faster, 0 Blob egress) |

The cost is amortized on the very first scale-out event.


---

## 2026-08-05 / 2026-08-06 — Qwen3-Coder-30B-A3B-Instruct (56.9 GiB, VM SKU: Standard_NC24ads_A100_v4)

| Pod | Date (UTC) | Node | Cache / download path | RunAI streamer time | **Model download throughput** | Model loading time | Pod Ready time | Summary |
|---|---|---|---|---:|---:|---:|---:|---|
| `qwen3-coder-30b-a3b-instruct-ccx24-0` | 2026-08-05 | `aks-ws824879e3f-28114834-vmss000000` | DACS enabled, but mostly origin / remote client: `PrefetchCache=2037`, `RemoteCache=1955`, `RemoteClient=34325` | 68.96s | **844.5 MiB/s** | 70.11s | 5m36s | Low cache-hit DACS run; most model chunks fetched from remote source. |
| `qwen3-coder-30b-a3b-instruct-zdz9x-0` | 2026-08-06 | `aks-ws4d1d2affe-11877758-vmss000000` | DACS hot-cache hit: `PrefetchCache=0`, `RemoteCache=38317`, `RemoteClient=0`, `ZeroCopy=786` | 25.88s | **2.2 GiB/s** | 27.33s | 6m40s | Fastest path; model chunks served from distributed cache. |
| `qwen3-coder-30b-a3b-instruct-kd2rg-0` | 2026-08-06 | `aks-wsed7ffa655-15239804-vmss000000` | No DACS/cache injection visible; direct Azure-source streaming with Workload Identity | 34.41s | **1.7 GiB/s** | 35.56s | 6m55s | Direct Azure-source load; faster than low-hit DACS, slower than hot-cache DACS. |

---

## 2026-08-09 — Qwen3-Coder-30B-A3B-Instruct follow-up comparison (VM SKU: Standard_NC24ads_A100_v4)

All pods below use the same model source and loader:

```text
--model=az://pvc-58e234e9-ebc3-4dda-b4c6-451243e48251/Qwen/Qwen3-Coder-30B-A3B-Instruct
--load-format=runai_streamer
```

All pods in this comparison ran on GPU nodes with VM SKU **`Standard_NC24ads_A100_v4`**.

DACS/cache configuration was present on all of them:

```text
RUNAI_STREAMER_CACHE_ENABLED=true
RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=true
CACHE_DISCOVERY_URL=cache-sample-discovery.dacs-cache-system.svc.cluster.local
```

### Download throughput comparison

| Pod | Node | Cache / download path | ReadChunk stats | RunAI streamer time | **Download throughput** | Model loading time | Notes |
|---|---|---|---|---:|---:|---:|---|
| `qwen3-coder-30b-a3b-instruct-v2wzt-0` | `aks-ws3362a5a00-32140693-vmss000000` | **Uncached remote path** | `PrefetchCache=0`, `RemoteCache=0`, `RemoteClient=19787` | 55.24s | **1.0 GiB/s** | 56.86s | No DACS cache hit; chunks fetched through RemoteClient/origin. |
| `qwen3-coder-30b-a3b-instruct-lskhj-0` | `aks-ws3362a5a00-32140693-vmss000000` | **DACS remote-cache hit** | `PrefetchCache=0`, `RemoteCache=19787`, `RemoteClient=0` | 25.92s | **2.2 GiB/s** | 26.99s | Warm-cache fast path. |
| `qwen3-coder-30b-a3b-instruct-q8tp4-0` | `aks-ws38180e667-64195973-vmss000000` | **DACS remote-cache hit** | `PrefetchCache=0`, `RemoteCache=19787`, `RemoteClient=0` | 26.45s | **2.2 GiB/s** | 27.40s | Warm-cache fast path on another node. |

### Timing evidence for `q8tp4-0`

```text
ReadChunk stats: MountName= ChunkSize=3145728 Total=19787 PrefetchCache=0 RemoteCache=19787 RemoteClient=0 ZeroCopy=19292 SubChunk=495
[RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 26.45s, 2.2 GiB/s
Model loading took 56.93 GiB memory and 27.401224 seconds
```

### Interpretation

- `v2wzt-0` is the slow path in this set:
  - **1.0 GiB/s**
  - `RemoteCache=0`, `RemoteClient=19787`
  - model chunks came directly from the remote source
- `lskhj-0` and `q8tp4-0` are both DACS warm-cache runs:
  - both reached about **2.2 GiB/s**
  - both had `RemoteCache=19787`, `RemoteClient=0`
  - both finished model loading in about **27 seconds**

### Throughput delta vs `v2wzt-0`

| Pod | Throughput vs `v2wzt-0` |
|---|---:|
| `v2wzt-0` | 1.00× |
| `lskhj-0` | **2.20×** |
| `q8tp4-0` | **2.20×** |

### Conclusion
On 2026-08-09, the main performance differentiator was whether DACS `RemoteCache` served the model chunks:
- **No cache hit (`v2wzt-0`)** → about **1.0 GiB/s**, **56.86s** total model load
- **Cache hit (`lskhj-0`, `q8tp4-0`)** → about **2.2 GiB/s**, about **27s** total model load

So for this 56.9 GiB Qwen3-Coder-30B-A3B-Instruct model, the warm-cache path is roughly **2× faster** than the uncached remote-client path.

---

## 2026-08-10 — `qwen3-coder-30b-a3b-instruct-zd9p2-0` on larger GPU node size

Pod under test:

- Pod: `qwen3-coder-30b-a3b-instruct-zd9p2-0`
- Cluster: `andy-aks135`
- Node: `aks-wsbc0b0ca81-11400277-vmss000000`
- **GPU node size:** `Standard_NC48ads_A100_v4`

### What path was used?

This pod used **RunAI Model Streamer**:

```text
load_format=runai_streamer
model='/root/.cache/vllm/assets/model_streamer/2c82cfef'
Loading safetensors using Runai Model Streamer
```

Unlike the earlier DACS-focused runs, this log does **not** show the usual cache-client summary lines such as:

```text
ReadChunk stats: ...
RemoteCache=...
RemoteClient=...
```

So from the pod log alone, this run is best described as:

- **RunAI Streamer path confirmed**
- **No pod-side DACS `ReadChunk stats` evidence available in the current log window**
- therefore **cannot attribute this run to `RemoteCache` vs `RemoteClient` with the same confidence** as the 2026-08-09 cases above

### Timing

Relevant startup lines:

```text
02:17:33 Starting to load model /root/.cache/vllm/assets/model_streamer/2c82cfef...
02:17:49 [RunAI Streamer] Overall time to stream 56.9 GiB of all files to cuda:0: 15.24s, 3.7 GiB/s
02:17:50 Model loading took 56.93 GiB memory and 16.270193 seconds
```

### Result summary

| Pod | GPU node size | Confirmed path from log | RunAI streamer time | **Download throughput** | Model loading time | Notes |
|---|---|---|---:|---:|---:|---|
| `qwen3-coder-30b-a3b-instruct-zd9p2-0` | `Standard_NC48ads_A100_v4` | `runai_streamer` | 15.24s | **3.7 GiB/s** | 16.27s | Fastest result in this note set so far; pod log does not include `ReadChunk stats`, so cache-hit source is not proven from this log alone. |

### Interpretation

Compared with the 2026-08-09 results on `Standard_NC24ads_A100_v4` nodes:

- `v2wzt-0` (uncached remote-client path): **1.0 GiB/s**, **56.86s**
- `lskhj-0` / `q8tp4-0` (warm remote-cache path): **2.2 GiB/s**, about **27s**
- `zd9p2-0` on **`Standard_NC48ads_A100_v4`**: **3.7 GiB/s**, **16.27s**

So this `zd9p2-0` run is materially faster than both the uncached path and the earlier warm remote-cache runs. The key confirmed difference from the log we inspected is the **larger GPU node size (`Standard_NC48ads_A100_v4`)** plus a very fast RunAI streaming path to `cuda:0`.

---

## 2026-08-11 — `qwen3-coder-30b-a3b-instruct` DACS/streaming spot checks on `andy-aks135`

These notes now keep only the two pods that were still available for live re-check with the shared kubeconfig, and drop the earlier pods that were already gone.

### What was under test?

- Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct`
- vLLM load path: `--load-format=runai_streamer`
- Model source: `az://pvc-58e234e9-ebc3-4dda-b4c6-451243e48251/Qwen/Qwen3-Coder-30B-A3B-Instruct`
- Tensor parallelism: `--tensor-parallel-size=1`

Both retained pods in this comparison ran on GPU nodes with VM SKU **`Standard_NC24ads_A100_v4`**:

- `qwen3-coder-30b-a3b-instruct-4fwkc-0` → node `aks-ws0c015ab37-41624886-vmss000000`
- `qwen3-coder-30b-a3b-instruct-bp2kr-0` → node `aks-ws1568bb9e4-24671092-vmss000000`

### Result summary

| Date (UTC) | Pod | Observed path | Cache evidence | Stream time | Throughput | Model load time |
|---|---|---|---|---:|---:|---:|
| 2026-08-11 | `qwen3-coder-30b-a3b-instruct-4fwkc-0` | **Uncached remote-client path** | `RemoteCache=0`, `RemoteClient=19787` | 56.29s | **1.0 GiB/s** | 58.27s |
| 2026-08-11 | `qwen3-coder-30b-a3b-instruct-bp2kr-0` | **DACS remote-cache hit** | `RemoteCache=19787`, `RemoteClient=0` | 25.9s | **2.2 GiB/s** | 26.83s |

### Timing evidence for `4fwkc-0`

```text
ReadChunk stats: MountName= ChunkSize=3145728 Total=19787 PrefetchCache=0 RemoteCache=0 RemoteClient=19787 ZeroCopy=0 SubChunk=495
[RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 56.29s, 1.0 GiB/s
Model loading took 56.93 GiB memory and 58.268750 seconds
```

### Timing evidence for `bp2kr-0`

```text
ReadChunk stats: MountName= ChunkSize=3145728 Total=19787 PrefetchCache=0 RemoteCache=19787 RemoteClient=0 ZeroCopy=19292 SubChunk=495
Download latencies (ms) from Cache MountName= Samples=1000 Min=0 Max=161 Avg=53 P50=50 P95=91
[RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 25.9s, 2.2 GiB/s
Model loading took 56.93 GiB memory and 26.828880 seconds
```

### Interpretation

For the two live-verified pods on 2026-08-11, the dominant variable was again **whether DACS `RemoteCache` served the model chunks**:

- **`4fwkc-0`: uncached remote-client path**
  - `RemoteCache=0`, `RemoteClient=19787`
  - **1.0 GiB/s**
  - **58.27 s** total model load
- **`bp2kr-0`: DACS remote-cache hit**
  - `RemoteCache=19787`, `RemoteClient=0`
  - **2.2 GiB/s**
  - **26.83 s** total model load

### Conclusion

For this Qwen3-Coder-30B-A3B-Instruct workload on `andy-aks135`, the two live 2026-08-11 checks show a clear warm-cache advantage:

- **DACS cache-hit path (`bp2kr-0`)**: **2.2 GiB/s**, **26.83 s** model load
- **Uncached remote-client path (`4fwkc-0`)**: **1.0 GiB/s**, **58.27 s** model load

So within the same model family and same RunAI Streamer integration, the DACS cache-hit path was about **2.2× higher throughput** and roughly **2.17× faster wall-clock model load**, saving about **31.44 s** versus `4fwkc-0`.

---

## 2026-08-24 — `qwen3-coder-30b-a3b-instruct` two back-to-back uncached runs on `andy-aks135`

Two pods were spun up on this cluster within ~40 min of each other. Both
show the DACS cache client wired in but **neither hit `RemoteCache`** —
both ended up on the pure remote-client (blob-direct) path, so this note
records two consecutive **uncached** baselines under otherwise identical
setup.

### Setup (both pods)

- Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct` (56.93 GiB, 18,867 tensor chunks)
- Model source: `az://pvc-58e234e9-ebc3-4dda-b4c6-451243e48251/Qwen/Qwen3-Coder-30B-A3B-Instruct`
- vLLM load path: `--load-format=runai_streamer`, `--tensor-parallel-size=1`, `--dtype=bfloat16`
- Storage account: `fuse27e8e9b66850e485189` (via Azure Workload Identity, `AZURE_CLIENT_ID=4d91b548-…`)
- DACS wiring present: `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=1`,
  `CACHE_DISCOVERY_URL=cache-sample-discovery.dacs-cache-system.svc.cluster.local`,
  `RUNAI_STREAMER_CHUNK_BYTESIZE=3145728`
- **VM SKU on both nodes: `Standard_NC24ads_A100_v4`** (A100 80 GB × 1)

### Result summary

| Time (UTC) | Pod | Node | Observed path | Cache evidence | Stream / model-load time | **Download throughput** |
|---|---|---|---|---|---:|---:|
| 2026-08-24 08:51 | `qwen3-coder-30b-a3b-instruct-rcgrj-0` | `aks-wsc45b85930-29303857-vmss000000` | **Uncached remote-client (blob-direct)** | `PrefetchCache=0`, `RemoteCache=0`, `RemoteClient=19508+`, `GetProperties CacheHit=0 / CacheMiss=16` | 46.28 s model load | **~1.23 GiB/s** |
| 2026-08-24 09:31 | `qwen3-coder-30b-a3b-instruct-d7l26-0` | `aks-ws2d413dc2e-15611082-vmss000000` | **Uncached remote-client (blob-direct)** | `PrefetchCache=0`, `RemoteCache=0`, `RemoteClient=19787`, `GetProperties CacheHit=0 / CacheMiss=16` | 43.94 s model load | **~1.30 GiB/s** |
| 2026-08-24 12:39 | `qwen3-coder-30b-a3b-instruct-pr8t4-0` | (Standard_NC24ads_A100_v4) | **Warm DACS remote cache hit** | `PrefetchCache=0`, `RemoteCache=19787`, `RemoteClient=0`, `GetProperties CacheHit=16 / CacheMiss=0` | 27.44 s model load (26.3 s stream) | **~2.20 GiB/s** |

### Timing evidence for `rcgrj-0`

```text
INFO 08-24 08:52:33 [gpu_model_runner.py:5037] Starting to load model /root/.cache/vllm/assets/model_streamer/2c82cfef...
StreamingClient.cpp:LogReadChunkStats: ReadChunk stats: MountName= ChunkSize=3145728 Total=19487 PrefetchCache=0 RemoteCache=0 RemoteClient=19508 ZeroCopy=0 SubChunk=479
StreamingClient.cpp:LogGetPropertiesStats: GetProperties stats: MountName= Total=16 CacheHit=0 CacheMiss=16
StreamingClient.cpp:LogDownloadLatencyStatsInner: Download latencies (ms) from Remote Samples=1000 Min=24 Max=399 Avg=46 P50=41 P95=77
INFO 08-24 08:53:21 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 46.281176 seconds
```

### Timing evidence for `d7l26-0`

```text
INFO 08-24 09:31:24 [gpu_model_runner.py:5037] Starting to load model /root/.cache/vllm/assets/model_streamer/2c82cfef...
StreamingClient.cpp:LogReadChunkStats: ReadChunk stats: MountName= ChunkSize=3145728 Total=19787 PrefetchCache=0 RemoteCache=0 RemoteClient=19787 ZeroCopy=0 SubChunk=495
StreamingClient.cpp:LogGetPropertiesStats: GetProperties stats: MountName= Total=16 CacheHit=0 CacheMiss=16
StreamingClient.cpp:LogDownloadLatencyStatsInner: Download latencies (ms) from Remote Samples=1000 Min=22 Max=364 Avg=46 P50=42 P95=77
INFO 08-24 09:32:09 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 43.941432 seconds
```

### Timing evidence for `pr8t4-0` (warm DACS cache hit)

```text
INFO 08-24 12:39:16 [gpu_model_runner.py:5037] Starting to load model /root/.cache/vllm/assets/model_streamer/2c82cfef...
StreamingClient.cpp:LogReadChunkStats: ReadChunk stats: MountName= ChunkSize=3145728 Total=19787 PrefetchCache=0 RemoteCache=19787 RemoteClient=0 ZeroCopy=19292 SubChunk=495
StreamingClient.cpp:LogGetPropertiesStats: GetProperties stats: MountName= Total=16 CacheHit=16 CacheMiss=0
INFO 08-24 12:39:43 file_streamer.py:69 [RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 26.3s, 2.2 GiB/s
INFO 08-24 12:39:44 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 27.438513 seconds
```

### Interpretation

- Both `rcgrj-0` and `d7l26-0` ran on `Standard_NC24ads_A100_v4` and
  landed on the **uncached remote-client (blob-direct) path** —
  `RemoteCache=0`, `RemoteClient=~19,500–19,787`.
- Blob-side latency was very similar on both uncached runs (P50 41–42 ms,
  P95 ~77 ms), and end-to-end throughput came out at
  **~1.23 GiB/s** and **~1.30 GiB/s** respectively — well above the
  1.0 GiB/s uncached number in the 2026-08-11 runs on this cluster.
- Interestingly, `d7l26-0` ran ~40 min after `rcgrj-0` finished but
  **still did not hit the DACS cache**: `CacheHit=0`, no `RemoteCache`
  chunks. Two plausible reasons:
  1. Cache upload has a 60 s start delay (`cacheUploadStartDelaySeconds=60`)
     but `rcgrj-0` loaded in only 46 s → the first pod finished before
     the async upload window really engaged, so the cache never got
     populated with these chunks.
  2. Even if some chunks did upload, `d7l26-0` landed on a different
     node from `cache-sample-0`, and consistent-hashing / server pool
     changes could keep it from finding those keys.
- By the time `pr8t4-0` started (~3 h later, 12:39 UTC), the DACS
  remote cache had been fully populated — all 19,787 chunks served
  as `RemoteCache` hits, `RemoteClient=0` (no blob-direct fallback),
  `GetProperties CacheHit=16/16`. End-to-end throughput jumped to
  **~2.20 GiB/s** (26.3 s stream, 27.44 s total model load), i.e.
  **~1.7× faster** than the two uncached runs and back in line with
  the 2026-08-11 warm-cache baseline (`bp2kr-0`: 2.2 GiB/s, 26.83 s).

### Conclusion

On 2026-08-24 the same 56.93 GiB `qwen3-coder-30b-a3b-instruct` model
was loaded three times on `Standard_NC24ads_A100_v4` with DACS wired
in, and produced a clean uncached-vs-cached comparison on this same
cluster:

- `rcgrj-0` (08:51) and `d7l26-0` (09:31): both **blob-direct**, ~44–46 s
  to bring the model in, **~1.23–1.30 GiB/s**.
- `pr8t4-0` (12:39): **warm DACS cache hit** (`RemoteCache=19787/19787`),
  **26.3 s stream / 27.44 s model load, ~2.20 GiB/s** — about **1.7×
  faster** than the two uncached runs, matching the 2026-08-11
  `bp2kr-0` warm-cache baseline (~2.2 GiB/s, 26.83 s).

So once the DACS cache is actually populated for this model, the
real-world payoff on this SKU is roughly a **1.7× speedup** over the
blob-direct path.

## 2026-08-24 — `qwen3-coder-30b-a3b-instruct`: back-to-back **cache-warm-up + hit** on `andy-aks135`

Same cluster as the previous section. Three additional pods were spun
up within ~40 min of each other; this time the sequence produced the
textbook DACS behavior we wanted to see: the first run went blob-direct
and populated the remote cache, the two subsequent runs hit that cache
100% with essentially identical timing.

### Setup (both pods)

- Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct` (56.93 GiB, 18,867 tensor chunks)
- Model source: `az://pvc-58e234e9-ebc3-4dda-b4c6-451243e48251/Qwen/Qwen3-Coder-30B-A3B-Instruct`
- vLLM load path: `--load-format=runai_streamer`, `--tensor-parallel-size=1`, `--dtype=bfloat16`
- Storage account: `fuse27e8e9b66850e485189` (via Azure Workload Identity)
- DACS wiring present: `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=1`,
  `CACHE_DISCOVERY_URL=cache-sample-discovery.dacs-cache-system.svc.cluster.local`,
  `RUNAI_STREAMER_CHUNK_BYTESIZE=3145728`
- **VM SKU: `Standard_NC24ads_A100_v4`** (A100 80 GB × 1)

### Result summary

| Time (UTC) | Pod | Observed path | Cache evidence | Stream time | Model-load time | **Download throughput** |
|---|---|---|---|---:|---:|---:|
| 2026-08-24 14:32 | `qwen3-coder-30b-a3b-instruct-6tgdc-0` | **Uncached remote-client (blob-direct)** | `PrefetchCache=0`, `RemoteCache=0`, `RemoteClient=19787`, `ZeroCopy=0`, `GetProperties CacheHit=0 / CacheMiss=16` | 41.8 s | 42.85 s | **~1.4 GiB/s** |
| 2026-08-24 14:50 | `qwen3-coder-30b-a3b-instruct-wv7xc-0` | **Warm DACS remote cache hit** ⚡ | `PrefetchCache=0`, `RemoteCache=19787`, `RemoteClient=0`, `ZeroCopy=19292`, `GetProperties CacheHit=16 / CacheMiss=0` | **25.87 s** | **26.84 s** | **~2.2 GiB/s** |
| 2026-08-24 15:13 | `qwen3-coder-30b-a3b-instruct-w9qnz-0` | **Warm DACS remote cache hit** ⚡ | `PrefetchCache=0`, `RemoteCache=19787`, `RemoteClient=0`, `ZeroCopy=19292`, `GetProperties CacheHit=16 / CacheMiss=0` | **25.88 s** | **26.88 s** | **~2.2 GiB/s** |
| 2026-08-25 01:12 | `qwen3-coder-30b-a3b-instruct-xk87g-0` | **Runai Streamer, no DACS** (baseline reference) | No `AISC_CTR` / `StreamingClient` logs at all — pod has no `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED` / `CACHE_DISCOVERY_URL` env, so the DACS StorageIntercept isn't loaded | **32.27 s** | **33.29 s** | **~1.8 GiB/s** |

### Timing evidence for `6tgdc-0` (uncached blob-direct)

```text
INFO 08-24 14:32:17 [gpu_model_runner.py:5037] Starting to load model /root/.cache/vllm/assets/model_streamer/2c82cfef...
StreamingClient.cpp:LogReadChunkStats: ReadChunk stats: MountName= ChunkSize=3145728 Total=19787 PrefetchCache=0 RemoteCache=0 RemoteClient=19787 ZeroCopy=0 SubChunk=495
StreamingClient.cpp:LogGetPropertiesStats: GetProperties stats: MountName= Total=16 CacheHit=0 CacheMiss=16
INFO 08-24 14:33:00 file_streamer.py:69 [RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 41.8s, 1.4 GiB/s
INFO 08-24 14:33:01 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 42.846253 seconds
```

### Timing evidence for `wv7xc-0` (warm DACS cache hit)

```text
INFO 08-24 14:50:41 [gpu_model_runner.py:5037] Starting to load model /root/.cache/vllm/assets/model_streamer/2c82cfef...
StreamingClient.cpp:LogReadChunkStats: ReadChunk stats: MountName= ChunkSize=3145728 Total=19787 PrefetchCache=0 RemoteCache=19787 RemoteClient=0 ZeroCopy=19292 SubChunk=495
StreamingClient.cpp:LogGetPropertiesStats: GetProperties stats: MountName= Total=16 CacheHit=16 CacheMiss=0
INFO 08-24 14:51:08 file_streamer.py:69 [RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 25.87s, 2.2 GiB/s
INFO 08-24 14:51:09 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 26.836729 seconds
```

### Timing evidence for `w9qnz-0` (warm DACS cache hit)

```text
INFO 08-24 15:13:39 [gpu_model_runner.py:5037] Starting to load model /root/.cache/vllm/assets/model_streamer/2c82cfef...
StreamingClient.cpp:LogReadChunkStats: ReadChunk stats: MountName= ChunkSize=3145728 Total=19787 PrefetchCache=0 RemoteCache=19787 RemoteClient=0 ZeroCopy=19292 SubChunk=495
StreamingClient.cpp:LogGetPropertiesStats: GetProperties stats: MountName= Total=16 CacheHit=16 CacheMiss=0
INFO 08-24 15:14:06 file_streamer.py:69 [RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 25.88s, 2.2 GiB/s
INFO 08-24 15:14:07 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 26.883669 seconds
```

### Timing evidence for `xk87g-0` (Runai Streamer, no DACS)

This pod was deployed **without** the DACS wiring env vars
(`RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED`,
`CACHE_DISCOVERY_URL`), so the DACS StorageIntercept isn't loaded and
there are **no `AISC_CTR` / `StreamingClient` log lines at all**. Only
Workload Identity envs are present
(`AZURE_STORAGE_ACCOUNT_NAME=fuse27e8e9b66850e485189`,
`AZURE_CLIENT_ID=4d91b548-…`,
`AZURE_FEDERATED_TOKEN_FILE=/var/run/secrets/azure/tokens/azure-identity-token`),
so the streamer talks straight to Azure Blob.

```text
INFO 08-25 01:12:08 [gpu_model_runner.py:5037] Starting to load model /root/.cache/vllm/assets/model_streamer/2c82cfef...
INFO 08-25 01:12:41 file_streamer.py:69 [RunAI Streamer] Overall time to stream 56.9 GiB of all files to cpu: 32.27s, 1.8 GiB/s
INFO 08-25 01:12:42 [gpu_model_runner.py:5132] Model loading took 56.93 GiB memory and 33.287981 seconds
```

### Interpretation

- `6tgdc-0` at 14:32 landed on the **uncached remote-client (blob-direct)
  path**: `RemoteCache=0`, `RemoteClient=19787/19787`, `ZeroCopy=0`,
  `GetProperties CacheHit=0/16`. Throughput came out at **~1.4 GiB/s**,
  consistent with the two uncached runs earlier the same day
  (`rcgrj-0`: ~1.23 GiB/s, `d7l26-0`: ~1.30 GiB/s).
- `wv7xc-0` at 14:50 (~18 min later, no other changes) landed on the
  **warm DACS remote-cache path**: `RemoteCache=19787/19787`,
  `RemoteClient=0` (no blob-direct fallback), `ZeroCopy=19292/19787`,
  `GetProperties CacheHit=16/16`. End-to-end throughput jumped to
  **~2.2 GiB/s** (25.87 s stream, 26.84 s total model load).
- `w9qnz-0` at 15:13 (~40 min after cache was populated) hit the
  DACS cache with the identical pattern: `RemoteCache=19787/19787`,
  `RemoteClient=0`, `ZeroCopy=19292/19787`, `GetProperties
  CacheHit=16/16`. Timing came in within 40 ms of `wv7xc-0`
  (25.88 s stream, 26.88 s model load) — the warm-cache path is
  **reproducible run-to-run**.
- Unlike the earlier `rcgrj-0` → `d7l26-0` sequence, this run worked
  end-to-end as designed: the first pod's uncached run populated the
  DACS cache, and the two subsequent pods (~18 min and ~40 min later)
  both hit that cache 100%.
- The warm-cache numbers are identical to `pr8t4-0` (12:39, same
  cluster): **~26–27 s / ~2.2 GiB/s** — so the warm-cache path is
  reproducibly landing at this level on `Standard_NC24ads_A100_v4`.

### Conclusion

Back-to-back `qwen3-coder-30b-a3b-instruct` runs on the same
`Standard_NC24ads_A100_v4` node, within ~40 min of each other, produced
the expected DACS cache warm-up + hit pattern:

- `6tgdc-0` (14:32): **uncached blob-direct**, 42.85 s model load,
  **~1.4 GiB/s**.
- `wv7xc-0` (14:50): **warm DACS cache hit** (`RemoteCache=19787/19787`,
  `GetProperties CacheHit=16/16`), **25.87 s stream / 26.84 s model
  load, ~2.2 GiB/s** — about **1.6× faster** than the uncached run.
- `w9qnz-0` (15:13): **warm DACS cache hit** (`RemoteCache=19787/19787`,
  `GetProperties CacheHit=16/16`), **25.88 s stream / 26.88 s model
  load, ~2.2 GiB/s** — within 40 ms of `wv7xc-0`, confirming the
  warm-cache path is reproducible run-to-run.
- `xk87g-0` (2026-08-25 01:12): **Runai Streamer with no DACS**
  (baseline reference), **32.27 s stream / 33.29 s model load,
  ~1.8 GiB/s**. Sits between the warm-cache path (~2.2 GiB/s) and the
  DACS uncached blob-direct path (~1.4 GiB/s): plain streamer is
  ~1.3× faster than the DACS uncached fallback, but the warm-cache
  path is still ~1.2× faster than plain streamer.

All three warm-cache runs on this cluster (`pr8t4-0` at 12:39,
`wv7xc-0` at 14:50, `w9qnz-0` at 15:13) converge on the **same
~26–27 s / ~2.2 GiB/s** window, matching the 2026-08-11 `bp2kr-0`
baseline (~2.2 GiB/s, 26.83 s). Once the DACS remote cache is
populated for a given model, the end-to-end payoff on this SKU is a
consistent **~1.6–1.7× speedup** over the DACS uncached blob-direct
path, and **~1.2× speedup** over plain Runai Streamer without DACS.
