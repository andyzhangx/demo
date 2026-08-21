# Reducing azurefile-csi-driver Node Logs

Analysis based on `other/csi-azurefile-node-9r58c.log` (2355 lines total).

The node driver's log is dominated by the `NodePublishVolume` idempotent / success path — kubelet reconciles every mounted volume periodically, so each pod causes 4–5 log lines per reconcile even when nothing changed. Below is a breakdown of what's noise vs. what has diagnostic value.

## Top repeating patterns

| # | Count | % | Pattern |
|---|-------|-----|---------|
| 1 | 304 | 12.9% | `metrics.go` — `"Observed Request Latency" ... request="azurefile_csi_driver_node_stage_volume"` |
| 2 | 304 | 12.9% | `utils.go` — `GRPC request: {...target_path...}` |
| 3 | 301 | 12.8% | `utils.go` — `GRPC call: /csi.v1.Node/NodePublishVolume` |
| 4 | 301 | 12.8% | `nodeserver.go` — `NodePublishVolume: ephemeral volume(csi-xxx) mount on /var/lib/kubelet/...` |
| 5 | 202 |  8.6% | `utils.go` — `GRPC response: {}` |
| 6 | 197 |  8.4% | `nodeserver.go` — `cifsMountPath(...) fstype() volumeID(...)` |
| 7 | 117 |  5.0% | `metrics.go` — `"Observed Request Latency" ... request="azurefile_csi_driver_node_publish_volume"` |
| 8 | 117 |  5.0% | `nodeserver.go` — `already mounted to target ...` |
| 9 | 106 |  4.5% | `utils.go` — `GRPC error: rpc error: code = InvalidArgument desc = GetAccountInfo(...) failed` |
| 10 | 105 | 4.5% | `azurefile.go` — `GetStorageAccountFromSecret(...) failed with error: ...` |
| 11 | 83  |  3.5% | `mount_linux.go` — `Mounting cmd (mount) with arguments (-t cifs ...)` |
| 12 | 9   |  0.4% | `NodeUnpublishVolume` related (GRPC call + internal) |

## Can be removed (or dropped to `klog.V(4)`)

These lines fire on every reconcile of already-mounted volumes and carry no diagnostic value at default verbosity.

| Pattern | Count | Reason |
|---|-------|--------|
| `GRPC call: /csi.v1.Node/NodePublishVolume` | **301** | Success path Node RPC; metrics already recorded, pure noise |
| `GRPC request: {...target_path...}` | **304** | Args of the same call; only useful on error |
| `GRPC response: {}` | **202** | Empty response body, zero information |
| `metrics.go "Observed Request Latency" node_stage_volume` (success) | **304** | Prometheus already scrapes this; log is a duplicate sink |
| `metrics.go "Observed Request Latency" node_publish_volume` (success) | **117** | Same |
| `NodePublishVolume: ephemeral volume(csi-xxx) mount on ...` | **301** | Overlaps with "already mounted"; short-circuit path doesn't need it |
| `already mounted to target ...` | **117** | Idempotent short path; kubelet probes constantly |

**Removable total: ~1646 lines / 2355 ≈ 70%**

## Keep (diagnostic value)

| Pattern | Count | Why keep |
|---|-------|----------|
| `mount_linux.go` — `Mounting cmd (mount) with arguments (-t cifs ...)` | **83** | Real mount action + arguments; essential for triage |
| `nodeserver.go` — `cifsMountPath(...) fstype() volumeID(...)` | **197** | Context before an actual mount (volumeID + target path) |
| `azurefile.go` — `GetStorageAccountFromSecret(...) failed with error: ...` | **105** | Error path root cause; must keep |
| `utils.go` — `GRPC error: rpc error: code = InvalidArgument desc = GetAccountInfo(...) failed` | **106** | Error path RPC return; pairs with the above |
| `NodeStageVolume` / `NodeUnstageVolume` related | **117** | Stage/Unstage frequency << Publish; shows volume lifecycle |
| `NodeUnpublishVolume` related (GRPC call + internal) | **9** | Low frequency; reflects pod deletion path |

**Kept total: ~617 lines / 2355 ≈ 26%**

> Note: `GetStorageAccountFromSecret failed` and the subsequent `GRPC error InvalidArgument` are always emitted as a pair for a single failure. Merging them into a single line could save another ~100 lines, but keeping them separate is fine if the effort isn't worth it.

## Where to change (files)

- `pkg/csi-common/utils.go` — `logGRPC`:
  - Success path → `klog.V(4)` (or return early); only print full `GRPC call` / `GRPC request` / `GRPC response` when `err != nil`.
- `pkg/azurefile/metrics.go` — `"Observed Request Latency"`:
  - Print only when `err != nil` or `latency > threshold`. Success + fast path → `klog.V(4)`.
- `pkg/azurefile/nodeserver.go`:
  - `NodePublishVolume: ephemeral volume(...) mount on ...` → `klog.V(4)`.
  - `already mounted to target ...` → `klog.V(4)` (or throttle to 1-in-N per volume).

## Expected result

- Remove ~1646 lines of noise + keep ~617 diagnostic lines + small remainder (~90).
- Total log volume drops from **2355 → ~700 lines (~30%)**, i.e. **~70% noise removed**, without losing any troubleshooting signal.
