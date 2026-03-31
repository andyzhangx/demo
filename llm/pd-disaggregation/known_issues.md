# PD Disaggregation Known Issues

## Q: NIXL handshake fails with "Remote NIXL agent engine ID mismatch"

### Error

When running PD disaggregation with NIXL KV transfer, the decode worker fails with:

```
NIXL transfer failure: handshake_failed
RuntimeError: Remote NIXL agent engine ID mismatch. Expected <prefill-engine-id>, received <decode-engine-id>.
```

### Root Cause

The prefill worker returns `"remote_host": "localhost"` in `kv_transfer_params`. When the decode worker tries to connect to `localhost:5600` for the NIXL handshake, it connects to itself (the decode pod) instead of the prefill pod. This causes an engine ID mismatch because the decode worker receives its own engine ID instead of the prefill worker's.

### Solution

Set the `VLLM_NIXL_SIDE_CHANNEL_HOST` environment variable on **both prefill and decode workers** so that vLLM advertises a routable address instead of `localhost`:

```yaml
env:
  - name: VLLM_NIXL_SIDE_CHANNEL_HOST
    valueFrom:
      fieldRef:
        fieldPath: status.podIP
```

Alternatively, use the pod FQDN:

```yaml
env:
  - name: VLLM_NIXL_SIDE_CHANNEL_HOST
    value: "<pod-name>.<headless-svc>.default.svc.cluster.local"
```
