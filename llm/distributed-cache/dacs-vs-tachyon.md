# DACS vs Tachyon Cache — What They Are and How They Relate

Reference: [kaito-project/kaito#2169](https://github.com/kaito-project/kaito/pull/2169)

## TL;DR

**Tachyon** and **DACS** are not two competing products — they are two layers of the same stack:

- **Tachyon** = the distributed cache **server** (StatefulSet running on NVMe nodes)
- **DACS** = the transparent **client-side integration** (library-injected into inference pods) that talks to that cache server
- **KAITO** consumes DACS as a `cache.Provider` plugin

```
┌─────────────────────────────────────────────┐
│   KAITO Workspace                           │
│   featureGates.distributedCache = true      │
│         │                                   │
│         ▼  (registers DACS provider)        │
├─────────────────────────────────────────────┤
│   DACS Client Library                       │
│   • StorageIntercept via LD_LIBRARY_PATH    │
│   • Injected by DACS mutating webhook       │
│     when it sees dacs.azure.com/inject=true │
│   • ImageVolume mounts libStorageDirect.so  │
│         │                                   │
│         ▼  (CACHE_DISCOVERY_URL:9065)       │
├─────────────────────────────────────────────┤
│   Tachyon Cache Server (StatefulSet)        │
│   • CRD: caches.storage.azure.com           │
│   • Default CR name: cache-sample           │
│   • NVMe SSD local storage                  │
│   • Namespace: tachyon-cache-system         │
│     (DACS default: dacs-cache-system)       │
└─────────────────────────────────────────────┘
```

## Evidence they share the same backend

From `pkg/cache/dacs/provider.go` in PR #2169:

```go
const (
    CacheNamespace           = "dacs-cache-system"
    DefaultCacheName         = "cache-sample"
    DefaultDiscoveryPort     = 9065
)

var cacheGVR = schema.GroupVersionResource{
    Group:    "storage.azure.com",
    Version:  "v1",
    Resource: "caches",
}
```

Compared to the Tachyon Getting Started guide:

| Field | Tachyon | KAITO DACS provider |
|-------|---------|---------------------|
| CRD | `caches.storage.azure.com` | `caches.storage.azure.com` ✅ |
| Default Cache CR | `cache-sample` | `cache-sample` ✅ |
| Discovery port | `9065` | `9065` ✅ |
| Discovery service | `cacheserver-discovery.<ns>.svc.cluster.local` | same pattern ✅ |
| Namespace | `tachyon-cache-system` | `dacs-cache-system` (configurable) |

## Two client access paths on the same cache

Tachyon exposes **two ways** to consume the same cache backend:

| Path | Who uses it | Requires code change? |
|------|-------------|----------------------|
| **`py_tachyon_client` Python wheel** | Apps that call the client API directly (or via blobfile/boostedblob adapters/monkey-patch) | Yes — application-level integration |
| **DACS StorageIntercept** | Inference pods that need transparent acceleration (KAITO, vLLM, HuggingFace, etc.) | **No** — library-injected via `LD_LIBRARY_PATH` |

KAITO picks the DACS path because inference frameworks shouldn't have to know about the cache.

---

## Cache providers registered in PR #2169

The KAITO cache framework is pluggable via a registry:

```go
// pkg/cache/registry.go
var providers = map[kaitov1beta1.CacheProvider]Provider{}

func Register(p Provider) {
    providers[kaitov1beta1.CacheProvider(p.Name())] = p
}
```

`CacheProvider` is just a `string`. Providers self-register in `init()`. There is no hardcoded enum, so new backends can be added by implementing the `cache.Provider` interface (`Name()`, `IsAvailable()`, `IsReady()`, `PodMutations()`, `Cleanup()`).

### Providers shipped in PR #2169

| Provider | Package | Purpose |
|----------|---------|---------|
| **`dacs`** | `pkg/cache/dacs` | Real backend — talks to Tachyon/DACS cache server via StorageIntercept, KV cache support |
| **`noop`** | `pkg/cache/noop` | Always reports ready, no actual caching — used for testing and disabled mode |

That's it. `dacs` is the only functional provider today. `noop` is a placeholder/test stub.

### How a provider integrates

The key method is `PodMutations()`, which returns a set of things to inject into the inference pod:

- Environment variables (e.g. `CACHE_DISCOVERY_URL`, `CACHE_SERVER_PORT`, `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB`)
- Volumes and volume mounts (e.g. OCI ImageVolume for client libraries)
- Init containers (e.g. cache prewarm)
- Pod labels (e.g. `dacs.azure.com/inject=true` to trigger the DACS mutating webhook)

Any cache backend that can plug in via "add stuff to the pod spec" fits this model.

### Potential future providers (not implemented yet)

PR #2169 mentions `docs/proposals/cache-csi-migration-plan.md`, hinting at a future **CSI-based provider** (mount cache as a CSI volume instead of using library intercept).

Other hypothetical directions the architecture would allow:

- **JuiceFS / Alluxio provider** — open-source distributed cache backends
- **NVIDIA Dynamo provider** — NVIDIA's model caching stack for AKS
- **Simple PVC provider** — a lightweight backend backed by any PVC
- **Registry-based provider** — pre-pull model weights via container image caching

None of these ship with PR #2169. They would require a new provider package that calls `cache.Register()`.

---

## Can Tachyon be used as a DACS provider?

**Yes — that is exactly what the DACS provider does.** Tachyon is the cache server; DACS is KAITO's way of injecting the client library into inference pods so they transparently hit that server.

To wire an existing Tachyon deployment into KAITO:

1. **Namespace alignment** — either install Tachyon into `dacs-cache-system`, or override the DACS provider namespace in KAITO's Helm values.
2. **Set DACS env vars on the `kaito-workspace` deployment** — see [`setup.md`](./setup.md).
3. **Deploy the DACS mutating webhook** — required to inject the client library into inference pods (not covered by the Tachyon guide; contact the Container Storage team at `xcontainerstordev@microsoft.com`).
4. **Provide `DACS_CLIENT_IMAGE`** — the OCI image containing `libStorageDirect.so` (also from the DACS/RunAI team).
5. **Reference the cache in your Workspace CR**:

   ```yaml
   apiVersion: kaito.sh/v1beta1
   kind: Workspace
   metadata:
     name: my-workspace
   spec:
     cache:
       modelWeights:
         provider: dacs
         mode: Opportunistic   # or Required
         cacheName: cache-sample  # optional, auto-detected
   ```

## References

- PR: [kaito-project/kaito#2169 — feat: distributed cache integration](https://github.com/kaito-project/kaito/pull/2169)
- Design doc referenced by the PR: `docs/proposals/20260518-distributed-cache-integration.md` (proposal #2088)
- User guide (from the PR): `website/docs/distributed-cache.md`
- Contact for Tachyon/DACS access: `xcontainerstordev@microsoft.com`
