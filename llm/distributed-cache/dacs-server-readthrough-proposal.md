# DACS server-side read-through: eliminating the `dacs-model-warmer` sidecar penalty

Follow-up to [`dacs-test-result.md`](./dacs-test-result.md), specifically the
[Two-phase timeline (serial, non-overlapping)](./dacs-test-result.md#two-phase-timeline-serial-non-overlapping)
section. This note explains why the current `dacs-model-warmer` sidecar design
makes the first-pod cold path strictly slower than it needs to be, and proposes
a server-side change that keeps the "second pod is fast" benefit while paying
close to zero cost on the first pod.

---

## 1. Problem restatement

The `lxg9q-0` run measured on 2026-08-29:

| Phase | Actor | Duration | Bytes | Throughput |
|---|---|---:|---:|---:|
| Phase 1 — Blob → DACS cache | `dacs-model-warmer` sidecar | **48.52 s** | 56.9 GiB | ~1.17 GiB/s |
| gap (vLLM engine boot) | — | ~4 s | — | — |
| Phase 2 — DACS cache → GPU | main container `runai_streamer` | **17.93 s** | 56.9 GiB | ~3.3 GiB/s |
| End-to-end (pod scheduled → model on GPU) | — | **~74 s** | 56.9 GiB | ~0.77 GiB/s |

Because the sidecar blocks until every chunk has been fetched from Blob **and**
persisted to the local SSD cache, the two phases are strictly serial and
non-overlapping. Their times add rather than max. The 56.9 GiB payload is
effectively moved twice (Blob → cache, then cache → GPU).

For the very first pod pulling a model, this is worse than not using DACS at
all: the earlier `phi-4-cache-pdvcj-0` cold run (no warmer, no sidecar) loaded
7.15 GiB from Blob directly through Run:ai Streamer in 12.05 s. In that run,
DACS still populated its cache opportunistically — subsequent pods got the
warm ~4.4 s path — but the first pod was never punished for it.

The sidecar design only starts to look good when compared to `66nj8-0`
(211 s partial-cold for Qwen3-Coder-30B): a case where the client itself must
carry the full Blob egress latency into the vLLM tensor-load hot path. Even
then, ~74 s is roughly 2.7× slower than the warm 27 s baseline the sidecar
was supposedly enabling.

## 2. Concrete issues observed with the current `dacs-model-warmer` sidecar

These are all directly attributable to the two-phase serial design, not to
bugs in the warmer binary itself. They come from `dacs-test-result.md` runs
on `andy-aks135` and comparisons across cluster series.

### 2.1 First-pod wall-clock regresses vs. no-DACS baseline

| Path | First-pod wall clock (Qwen3-Coder-30B, 56.9 GiB) | vs. sidecar |
|---|---:|---:|
| Sidecar warmer + main container (`lxg9q-0`) | **~74 s** | 1.00× |
| Plain Run:ai Streamer against origin Blob (same region, no DACS) | ~26–27 s | ~0.36× |
| DACS client in-process cold, Blob-direct (`8jdxx-0` early cold fill) | ~180 s (log rolled, aggregate ~300 MB/s during fill) | ~2.4× |

For small models the regression is worse in relative terms: phi-4 (7.15 GiB)
cold with just the client library was **12.05 s** (`pdvcj-0`). A sidecar
applied to the same model would add roughly the same Phase-1 duration (~10 s)
before vLLM even starts — turning a 12 s startup into ~25 s for zero benefit
to that pod.

### 2.2 Phase 1 and Phase 2 forced to be strictly serial

Measured on `lxg9q-0`:

- Phase 1 (Blob → cache, warmer): 02:58:06.69 → 02:58:58.00 = 48.52 s
- Gap (vLLM engine boot): 02:58:58 → 02:59:02 = ~4 s
- Phase 2 (cache → GPU, `runai_streamer`): 02:59:02 → 02:59:20 = 17.93 s

The 56.9 GiB payload is moved through the client-node NIC twice — once as a
cold Blob download during Phase 1 (`RemoteClient=36,520`) and once as a
host-local cache read during Phase 2 (`RemoteCache=37,984`). There is no
overlap: the sidecar’s `startupProbe` gate keeps the main container from
starting until Phase 1 reports completion, so Run:ai Streamer cannot begin
reading chunks that are already in cache while the warmer is still writing
later ones.

### 2.3 The "end-to-end throughput" number is misleading

`dacs-test-result.md` reports `~0.77 GiB/s` end-to-end throughput for the
sidecar path. This is the payload-over-wall-clock figure, computed as
56.9 GiB / 74 s. It **hides** that:

- Only 56.9 GiB of unique bytes actually needed to move over the Blob
  boundary; the rest is intra-node loopback.
- The comparable no-DACS number (Run:ai Streamer against Blob, same region)
  is ~2.2 GiB/s (`bp2kr-0` baseline), or 26.83 s wall clock.

Quoting `0.77 GiB/s` next to "cache-hit path throughput 3.3 GiB/s" invites
readers to conclude DACS is a ~4× win on the cold path when it is actually
a ~2.7× regression against the no-DACS baseline for that same first pod.

### 2.4 The sidecar consumes cluster resources indefinitely

After Phase 1 completes, the warmer container "stays alive" (per the doc's
own description). It holds:

- CPU / memory `requests` and `limits` for the entire life of the Workspace
  pod, not just the warmup window.
- One Kubernetes container slot per pod (contributes to pod restart/eviction
  bookkeeping, `containerStatuses`, log volume, and readiness aggregation).
- A persistent open connection into `cache-sample-discovery`.

An `initContainer` would give the same one-shot semantics without any of
these steady-state costs. That the current design uses a sidecar and not an
init container suggests it is trying to leave room for background prefetch
or progress reporting; neither behavior is exercised after the initial fill.

### 2.5 Concurrent scale-up hits the Blob egress quota N times

Because each pod carries its own warmer, an `InferenceSet` scaling from 0
to N replicas of a fresh model has N sidecars all downloading the same
56.9 GiB from the same storage account in parallel. There is no
de-duplication:

- N × 56.9 GiB against the storage account within the same ~50 s window.
- On this cluster's storage account that saturates the ~2.4 Gbps aggregate
  egress observed during `8jdxx-0` — the actual per-pod Phase 1 duration
  balloons proportionally to N, so 20 pods do not warm in 50 s; they warm
  in something closer to `50 × 20 / (available parallelism)`.
- Populates the DACS cache N times over (redundant SSD writes, contends with
  eviction).

Singleflight de-duplication is impossible from the client side: each
sidecar is a separate process on a separate pod and cannot see the others.
Only a shared component (the cache server) can coalesce.

### 2.6 `PrefetchCache` hit rate is low, so the warmer is not even a good
cache-warming pattern

From the `lxg9q-0` warmer histogram:

```text
ReadChunk stats: Total=38841  PrefetchCache=2197  RemoteCache=124  RemoteClient=36520
```

That is ~5.6 % of chunks satisfied by prefetch, ~94 % by direct remote fetch,
~0.3 % by cross-pool cache. The `prefetchWindowSizeInMB=64` window is not
tracking the safetensors tensor-order well when the warmer is used, so the
warmer is barely benefiting from the same prefetch machinery that helps
steady-state readers.

### 2.7 Failure semantics are ambiguous

If the warmer sidecar fails mid-fill (e.g. transient Blob 503, node SSD
full), the current design has three unspecified behaviors:

1. Does the main container still start? (If yes, it will fall into the
   partial-cold path and pay Blob latency for the missing chunks — exactly
   `66nj8-0`’s 211 s regression.)
2. Does Kubernetes restart the sidecar? (If yes, the restart re-downloads
   already-cached chunks unless the warmer is idempotent against the cache
   — not documented.)
3. Does the `Workspace` status reflect the fill error? (No: `ModelCacheReady`
   only tracks `ModelMirror`, not the DACS-side fill.)

Each of these needs its own guard rail today. A server-side read-through
design eliminates the class of question because the fill is implicit; there
is no separate object to succeed or fail.

### 2.8 `ModelMirror Ready` semantics are already misleading; the sidecar amplifies it

`dacs-test-result.md` itself calls out that `ModelMirror Ready` does not
imply the DACS cache is warm. The sidecar makes this worse: users see
`ModelMirrorReady=True` and `ModelCacheReady=True`, but the pod is *still*
doing a ~50 s Blob pull inside the sidecar. There is no user-facing signal
for "cache warmup for this specific pod is in progress"; the operator
learns it only from the container's stdout progress lines.

### 2.9 Summary of the design smell

The sidecar is doing the work that a distributed cache server is supposed
to do: fetching from origin, populating shared storage, coordinating across
requesters. Pushing that responsibility onto every client (via a sidecar or
otherwise) is exactly the anti-pattern that read-through caches were
invented to fix. The sections below propose the standard fix.

---

## 3. Why the sidecar exists in the first place

Inspection of the live `cache-sample-0` pod on cluster `andy-aks135`:

```console
$ kubectl -n dacs-cache-system get pod cache-sample-0 -o yaml
containers:
- name: cacheserver
  image: tachyonexternal.azurecr.io/cache-server:20260723.1
  command: [/bin/sh, -cx]
  args: |
    /root/CacheServer $CACHESERVER_PORT $CACHESERVER_CACHE_PATH $CACHESERVER_CACHE_SIZE_BYTES
  env:
    - CACHESERVER_THREADPOOL_SIZE=80
    - CACHESERVER_METRICS_PORT=9096
    - CACHESERVER_EVICTION_ENABLED=true
    - CACHESERVER_EVICTION_LAST_ACCESS_THRESHOLD=30d
    - CACHESERVER_EVICTION_SIZE_THRESHOLD=90
    - CACHESERVER_EVICTION_PASS_FREQUENCY=1h
    - CACHESERVER_EVICTION_MAINTAIN_FREE_SPACE=true
    - CACHESERVER_EVICTION_SIZE_TARGET=80
    - CACHESERVER_USE_ZEROCOPY=1
```

There are **no origin-related env vars**: no `AZURE_*`, no `STORAGE_*`, no
`ORIGIN_*`, no federated-token volumes projected into the container. The server
has no way to talk to Azure Blob at all — it is a pure passive block store.

The `/metrics` endpoint confirms the RPC shape:

```text
cache_server_request_counter{request_type="Download",status="Success"}            = 114838
cache_server_request_counter{request_type="Download",status="InvalidTransition"}  =  37948
cache_server_request_counter{request_type="Upload",  status="Success"}            =  19436
cache_server_cache_size_bytes                                                     =  61 GiB
cache_server_successful_request_latency_ms{request_type="Download"}  avg =  3.6 ms  P95 ≈ 10 ms
cache_server_successful_request_latency_ms{request_type="Upload"}    avg =  168 ms  P95 ≈ 250 ms
```

Two RPCs are in play: `Download` (client reads a chunk from the server) and
`Upload` (client sends a chunk to the server for storage). `InvalidTransition`
on `Download` is the wire-level signal for a cache miss.

The miss path is therefore entirely client-side:

```
client (libStorageDirect.so) requests chunk C:
  Download RPC → server
    ├─ Success            → use cache-server data (~3 ms)
    └─ InvalidTransition  → client itself GETs C from Azure Blob
                          → client Upload RPC to server (~168 ms) to persist
                          → deliver bytes to caller (vLLM / warmer)
```

Given this shape, `dacs-model-warmer` is a client — same library
(`libStorageDirect.so`, same `AZURE_CACHE_LIB` env), just running in a sidecar
so its Blob-fetch-and-Upload work happens before the main container starts.
The warmer's serial two-phase penalty is baked into this "cache server has no
origin backend" architectural choice; there is no way to fix it with better
sidecar scheduling.

## 4. Proposal: move the origin backend into the cache server

Turn the cache server from a passive block store into a proper **read-through
cache with asynchronous write-back**. The design goal is: on a miss, the client
pays only Blob-egress latency (~50–200 ms same-region), never SSD-write
latency, and the SSD fill happens on a background fiber.

### 3.1 New Download semantics

```
server receives Download(chunk_id):
  if cache HIT:
      return SSD data                                          # unchanged (~3 ms)

  if cache MISS and readthrough_enabled:
      singleflight-dedup by chunk_id                           # coalesce concurrent misses
      foreground fiber:
          Blob GET(chunk_id) → memory pipe → stream to client  # ~50–200 ms same-region
      background fiber:
          same memory pipe → SSD write                         # off critical path
          on failure: increment dropped_writes metric, do not retry inline

  if cache MISS and !readthrough_enabled:
      return InvalidTransition                                 # legacy behavior
```

Concrete pieces:

1. **Origin config on the `Cache` CR** (`storage.azure.com/v1beta1`):
   ```yaml
   spec:
     origin:
       type: azureBlob
       endpoint: harikaito.blob.core.windows.net
       authMode: workloadIdentity        # or sasSecret / storageAccountKeySecret
       readThrough:
         enabled: true
         asyncWritebackQueueDepth: 512   # bounded backlog, drop when full
         asyncWritebackMinAgeSeconds: 30 # eviction grace so freshly filled chunks aren't reaped
   ```
   Helm chart maps this into new CacheServer env:
   `CACHESERVER_ORIGIN_TYPE`, `CACHESERVER_ORIGIN_ENDPOINT`,
   `CACHESERVER_ORIGIN_AUTH_MODE`, `CACHESERVER_READTHROUGH_ENABLED`,
   `CACHESERVER_ASYNC_WRITEBACK_QUEUE_DEPTH`, `AZURE_CLIENT_ID`,
   `AZURE_TENANT_ID`, `AZURE_FEDERATED_TOKEN_FILE`.

2. **Workload identity on the server pod.** The cache-server pod's
   ServiceAccount is annotated with `azure.workload.identity/client-id` and
   `azure.workload.identity/tenant-id`, matching how Kaito Workspaces are
   wired today. `azure-workload-identity` webhook projects the federated token
   into the pod. This grants `cache-sample-0` its own identity for
   `Storage Blob Data Reader` role assignments on the origin storage account.

3. **Singleflight de-duplication.** When a WorkspaceInferenceSet scales to N
   pods on the same model, the first pod's miss must fetch each unique chunk
   exactly once even though up to N clients are simultaneously requesting it.
   Without this, first-scale-up bursts trivially blow through the storage
   account's egress bandwidth quota. Existing DACS clients cannot do this
   because they don't see each other; only the server can.

4. **Bounded async writeback + backpressure.** SSD write throughput on the
   node cache path (`/var/lib/ssd/cacheserver`) is finite. Under sustained
   large-model fills the writeback queue can grow unbounded, spike memory,
   and starve the read-through fibers. Cap the queue at
   `asyncWritebackQueueDepth`; when full, degrade to "read-around" for
   further misses (fetch from Blob and stream to client, skip SSD write).
   Metric `cache_server_readthrough_dropped_writes_total` exposes this so
   operators can tune queue depth or SSD size.

5. **Eviction grace window.** The current eviction settings
   (`CACHESERVER_EVICTION_LAST_ACCESS_THRESHOLD=30d`,
   `CACHESERVER_EVICTION_MAINTAIN_FREE_SPACE=true`,
   `CACHESERVER_EVICTION_SIZE_THRESHOLD=90`) reap by last-access time. A
   just-async-written chunk has last-access = write time, so it looks fresh —
   but under memory pressure the eviction fiber could still race with a
   client's second Download of the same chunk. `asyncWritebackMinAgeSeconds`
   protects freshly filled chunks from being evicted before at least one
   client has had a chance to read them from SSD.

6. **New metrics.** Read-through is invisible in the current
   `cache_server_request_counter` schema; add:
   - `cache_server_readthrough_hits_total` — misses that were fetched from Blob and streamed
   - `cache_server_readthrough_bytes_total` — Blob egress in bytes (capacity-planning signal)
   - `cache_server_readthrough_inflight_writes` — current writeback queue depth
   - `cache_server_readthrough_dropped_writes_total` — writes dropped due to backpressure
   - `cache_server_singleflight_coalesced_total` — number of concurrent misses coalesced into one Blob GET
   - `cache_server_blob_get_latency_ms{quantile}` — Blob-side latency histogram distinct from cache-side

### 3.2 Client-side changes (small)

`libStorageDirect.so` learns a new capability flag: when the server advertises
`ReadThrough=true` at handshake time, the client stops treating
`InvalidTransition` as "self-serve from Blob" and instead just waits on the
server (with a longer client-side timeout, say 30 s per chunk, since P95 Blob
GET latency is ~50–200 ms not 500 ms). The self-serve fallback path stays as
a safety net for `NetworkError` / server-unreachable scenarios.

`dacs-model-warmer` becomes optional. It is still useful for large
`InferenceSet` scale-up events (see §6), but it is no longer needed on the
critical path of the first pod.

### 3.3 Wire compatibility

The RPC surface does not change. `Download` still returns the chunk on hit,
still returns an error status on unrecoverable miss. What changes is that a
`readthrough_enabled` server never emits `InvalidTransition` under normal
conditions — it either serves the chunk (from cache or from Blob) or reports
`NetworkError`. Clients built against the old server (that already handle
`InvalidTransition` by self-serving) continue to work; they just never hit
that code path when talking to a new server.

## 5. Expected performance

Measured baseline (from `dacs-test-result.md`, this cluster):

| Scenario | Current end-to-end | Blob egress | SSD-write on critical path |
|---|---:|---:|:---:|
| First pod, no warmer, small model (phi-4 7.15 GiB, `pdvcj-0`) | 12.05 s | 100 % | yes (client Upload) |
| First pod, no warmer, big model (Qwen3 56.9 GiB, `66nj8-0` partial-cold) | 211.01 s | ~94 % | yes (client Upload) |
| First pod, sidecar warmer (Qwen3 56.9 GiB, `lxg9q-0`) | ~74 s | 100 % | yes (client Upload, moved before vLLM) |
| Second pod, warm cross-node (Qwen3, `786qr-0`) | 27.52 s | 0 % | no |
| Second pod, warm host-local reboot (Qwen3, `8jdxx-0`) | 17.13 s | 0 % | no |

With server-side read-through:

| Scenario | Predicted end-to-end | How it gets there |
|---|---:|---|
| First pod, small model (phi-4) | **~10–12 s** | Same as current no-warmer path; Blob → client goes through server but adds negligible latency (~1 ms proxy). SSD fill happens off-path. |
| First pod, big model (Qwen3) | **~35–45 s** | Bounded by Blob-egress bandwidth (~1.5–1.7 GiB/s aggregate through the server's `maxConnsPerBlobClient=84` pool), not by client-serial tensor-load. Wall clock ≈ payload / Blob-egress-BW + 4 s engine boot + 17 s Phase-2 read from cache. Under read-through, Phase 1 and Phase 2 partially overlap — Phase 2 can start reading chunks the moment they are streamed through the server, so the "17 s Phase 2" tail collapses into Phase 1. |
| Second pod, warm | **~17–28 s** | Unchanged. |
| Sidecar warmer path (`lxg9q-0` shape) | **~30–35 s** | If the sidecar is still used (see §6), it is much faster too because its own reads go through the same read-through path. |

Concretely: `74 s → ~35 s` is a ~2× first-pod speedup, achieved without any
change to Workspace / InferenceSet CRDs and without the sidecar. The
second-pod path (already fast) is unchanged.

## 6. When the sidecar warmer is still useful

Read-through does not obsolete the warmer entirely; it only obsoletes it as
the *default per-pod* path. Two scenarios where an explicit warmer is still
the right tool:

1. **Multi-pod fan-out.** An `InferenceSet` scales from 0 to 20 replicas of
   the same model simultaneously. Read-through + singleflight ensures the
   Blob is only hit once, but all 20 pods block on the first pod's Blob
   fetch — they still see ~35–45 s of latency each. A cluster-scoped
   pre-warmer Job (not a per-pod sidecar) run *before* the scale-up produces
   the same warm state and lets all 20 pods start on the ~17 s path.

2. **Egress quota control.** If the workload requires strict accounting of
   "how many times has this model been pulled from Blob", a warmer with
   explicit progress reporting and checksum verification remains the
   auditable answer. Read-through fills are implicit.

Both cases are opt-in and cluster-level, not per-pod.

## 7. Migration plan

Rough ordering (server-side changes tracked in the DACS repo, client-side in
the Kaito integration):

1. **DACS server v-next**: add read-through code path, gated by
   `CACHESERVER_READTHROUGH_ENABLED=false` (opt-in). Origin config plumbed
   from Cache CR through the helm chart.
2. **Cache CRD extension**: add `spec.origin` field. Server pod
   ServiceAccount gets workload-identity annotations. Storage account grants
   `Storage Blob Data Reader` to the server identity.
3. **`dacs_client` handshake**: negotiate `readThrough` capability; when
   enabled, stop self-serving on `InvalidTransition`. Keep self-serve as
   fallback for `NetworkError`.
4. **Kaito Workspace injection**: when the target `Cache` reports
   `.status.readThroughEnabled=true`, the mutating webhook stops injecting
   the `dacs-model-warmer` sidecar for new Workspaces. Existing Workspaces
   are unaffected until they are recreated.
5. **Rollout**: canary on one preview cluster with a mid-size model
   (Qwen3-Coder-30B), compare first-pod wall-clock against the historical
   sidecar numbers in `dacs-test-result.md`, then GA.

## 8. Interim mitigations (no server changes required)

While the server-side work lands, two client-side changes can be made in
parallel:

1. **Stop injecting the sidecar by default.** Fall back to the pre-warmer-era
   behavior: the first pod runs the client library in-process (as `phi-4-cache-pdvcj-0` did) and pays the client-side Upload latency itself. For phi-4-sized models this was 12 s — faster than the sidecar's 74 s. For Qwen3-sized models it was 211 s (`66nj8-0`), so this only helps small-to-medium
   models until Option A lands.
2. **Ensure the client's `Upload` RPC is truly fire-and-forget.** The
   observed `Upload` P95 of 250 ms suggests the client may still be waiting
   on the Upload before returning to vLLM. If so, moving that to a detached
   fiber (log-and-forget) shaves that fraction off every client miss even
   in the current architecture.

Neither substitutes for §4, but they are safe defaults today and give
consistent measurements to compare Option A against.

---

## Appendix: evidence collected while writing this proposal

Cluster: `andy-aks135` (westeurope). Snapshot taken 2026-08-31 UTC.

```console
$ kubectl -n dacs-cache-system get all
NAME                            READY   STATUS    RESTARTS   AGE
pod/cache-sample-0              1/1     Running   0          47h
pod/cache-server-prereq-gg5b9   1/1     Running   0          47h

NAME                             TYPE        CLUSTER-IP     PORT(S)
service/cache-sample             ClusterIP   None           9065/TCP,9096/TCP
service/cache-sample-discovery   ClusterIP   10.0.150.137   9065/TCP

daemonset.apps/cache-server-prereq   1/1  READY  nodeSelector: kaito.sh/machine-type=gpu
statefulset.apps/cache-sample        1/1  READY
```

CacheServer args (no origin backend):

```console
/root/CacheServer $CACHESERVER_PORT $CACHESERVER_CACHE_PATH $CACHESERVER_CACHE_SIZE_BYTES
# CACHESERVER_PORT=9065
# CACHESERVER_CACHE_PATH=/var/lib/ssd/cacheserver/cache-sample/cache
# CACHESERVER_CACHE_SIZE_BYTES=214748364800 (200 GiB)
```

`/metrics` at time of writing:

```text
cache_server_request_counter{request_type="Download",status="Success"}            = 114838
cache_server_request_counter{request_type="Download",status="InvalidTransition"}  =  37948   # miss RPCs
cache_server_request_counter{request_type="Upload",  status="Success"}            =  19436   # client fills
cache_server_cache_size_bytes                                                     ≈  56.9 GiB (Qwen3-Coder-30B footprint)

Download latency histogram (Success): P50 ≈ 3 ms, P95 ≈ 10 ms, P99 ≈ 50 ms, max 500 ms
Upload   latency histogram (Success): P50 ≈ 168 ms, P95 ≈ 250 ms, P99 ≈ 500 ms, max 500 ms
```

Interpretation:
- The `Download` latency distribution (P95 10 ms) is what a first pod would
  see for every chunk *if the miss path also went through the server*.
- The `Upload` latency distribution (P95 250 ms) is what every first-pod
  miss currently costs the client on the critical path. Moving it off the
  critical path via read-through is where the ~50 s Phase-1 penalty
  disappears.
