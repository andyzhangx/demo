# Verifying vLLM KV Cache Events on Kaito (PR #1890)

End-to-end verification that [kaito-project/kaito#1890](https://github.com/kaito-project/kaito/pull/1890) — "feat: enable kv cache events on vLLM inference pods" — actually works: the operator injects the flag, the pod/service expose port 5557, the vLLM engine starts a ZMQ publisher, and a subscriber receives real `BlockStored` / `BlockRemoved` events triggered by real inference traffic.

Tested workspace: `phi-4-cl5w7` (single-pod vLLM, model `microsoft/phi-4-mini-instruct`, vLLM 0.22.1) on a Kaito test cluster.

---

## What PR #1890 is supposed to do

1. In `buildVLLMInferenceCommand`, inject `--kv-events-config='{"enable_kv_cache_events":true}'` into the vLLM run command when the workspace runtime is vLLM and the user hasn't overridden it.
2. On the vLLM inference pod, add a named container port `kv-events` = 5557.
3. On the workspace Service, expose the `kv-events` port **only** when service type is `ClusterIP` (i.e. not on user-opted `LoadBalancer` — the ZMQ stream is unauthenticated).

The three verifications below correspond directly to these three behaviors, plus a live subscriber test.

---

## 1. Verify the flag is on the vLLM command line

```bash
kubectl get pod phi-4-cl5w7-0 -o jsonpath='{.spec.containers[0].command}'
```

Result (trimmed):

```
python3 /workspace/vllm/inference_api.py \
    --load_format=auto --config_format=auto --tokenizer_mode=auto \
    --trust-remote-code --dtype=bfloat16 --max-model-len=auto \
    --kv-events-config='{"enable_kv_cache_events":true}' \
    --download-dir=/workspace/weights \
    --chat-template=/workspace/chat_templates/tool-chat-phi4-mini.jinja \
    --served-model-name=phi-4 --gpu-memory-utilization=0.84 \
    --compilation-config.pass_config.fuse_allreduce_rms=False \
    --model=microsoft/phi-4-mini-instruct --tensor-parallel-size=1
```

✅ `--kv-events-config='{"enable_kv_cache_events":true}'` is present.

---

## 2. Verify pod container port

```bash
kubectl get pod phi-4-cl5w7-0 -o jsonpath='{.spec.containers[0].ports}' | jq
```

```json
[
  { "name": "http",      "containerPort": 5000, "protocol": "TCP" },
  { "name": "kv-events", "containerPort": 5557, "protocol": "TCP" }
]
```

✅ Named port `kv-events` at 5557 is present.

---

## 3. Verify service port (ClusterIP only)

```bash
kubectl get svc phi-4-cl5w7 -o jsonpath='{.spec.type}{"\n"}{.spec.ports}' | jq
```

```
ClusterIP
[
  { "name": "http",      "port": 80,   "targetPort": 5000 },
  { "name": "ray",       "port": 6379, "targetPort": 6379 },
  { "name": "dashboard", "port": 8265, "targetPort": 8265 },
  { "name": "kv-events", "port": 5557, "targetPort": 5557 }
]
```

✅ ClusterIP service exposes `kv-events` = 5557.

(PR #1890 unit test `TestGenerateServiceManifest_KVEventsPort` also covers the negative cases: `vLLM + LoadBalancer` → **no** `kv-events` port; `non-vLLM + ClusterIP` → **no** `kv-events` port.)

---

## 4. Verify the ZMQ publisher started (vLLM log)

```bash
kubectl logs phi-4-cl5w7-0 | grep -iE 'kv_events|EventPublisher|ZMQ publisher'
```

Result:

```
(EngineCore pid=271) INFO 07-25 14:40:37 [kv_events.py:335] Starting ZMQ publisher thread
```

✅ vLLM `EngineCore` starts a ZMQ publisher thread (source: [`vllm/distributed/kv_events.py`](https://github.com/vllm-project/vllm/blob/main/vllm/distributed/kv_events.py)). This is the direct code path that `--kv-events-config` enables.

> Note: another line `LMCache INFO: KV events are disabled.` is unrelated — that is [LMCache](https://github.com/LMCache/LMCache)'s own independent KV events system, controlled by `enable_kv_events` in `LMCacheEngineConfig`, not by vLLM's `--kv-events-config`. PR #1890 enables the vLLM native one.

---

## 5. Verify port is actually listening

```bash
kubectl exec phi-4-cl5w7-0 -- python3 -c \
  'import socket; s=socket.socket(); s.settimeout(2); \
   print("connect_ex=", s.connect_ex(("127.0.0.1", 5557)))'
```

```
connect_ex= 0
```

✅ `0` = TCP connection accepted → 5557 is bound and listening.

---

## 6. Live end-to-end: subscribe + fire requests + assert events

### Subscriber script

vLLM's `EventPublisher` uses a 3-part ZMQ message:

```
part[0] = topic (empty by default)
part[1] = 8-byte big-endian uint64 sequence number (for lossy-subscriber detection)
part[2] = msgpack([timestamp, [events...], reserved])
```

`/tmp/kv_final.py` in the pod:

```python
import zmq, msgpack, time, collections, struct
ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("tcp://127.0.0.1:5557")
sub.setsockopt(zmq.SUBSCRIBE, b"")
sub.RCVTIMEO = 30000
counts = collections.Counter()
n_msg = n_ev = 0
samples = []
first_seq = last_seq = None
deadline = time.time() + 25
print("subscribed, collecting for 25s...", flush=True)
while time.time() < deadline:
    try:
        parts = sub.recv_multipart()
    except zmq.Again:
        break
    n_msg += 1
    topic, seq_bytes, payload_bytes = parts
    seq = struct.unpack("!Q", seq_bytes)[0]
    if first_seq is None: first_seq = seq
    last_seq = seq
    ts, events, _ = msgpack.loads(payload_bytes, raw=False)
    for ev in events:
        counts[ev[0]] += 1; n_ev += 1
        if len(samples) < 4: samples.append(ev)

print(f"zmq messages received : {n_msg}")
print(f"kv events parsed      : {n_ev}")
print(f"seq range             : {first_seq} .. {last_seq}")
print(f"event type breakdown  : {dict(counts)}")
for s in samples: print(" ", s)
```

### Traffic generator

While the subscriber is collecting, fire 8 distinct completion requests to force prefill + eviction activity:

```bash
kubectl exec phi-4-cl5w7-0 -- bash -c '
python3 /tmp/kv_final.py > /tmp/final.out 2>&1 &
SUB=$!
sleep 2
for i in $(seq 1 8); do
  curl -sS http://127.0.0.1:5000/v1/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"phi-4\",\"prompt\":\"Test $i-$RANDOM: give a unique fact about number $i in physics/math.\",\"max_tokens\":60,\"temperature\":0.9}" \
    > /dev/null &
done
wait
wait $SUB
cat /tmp/final.out
'
```

### Result

```
subscribed, collecting for 25s...

zmq messages received : 7
kv events parsed      : 72
seq range             : 706 .. 712
event type breakdown  : {'BlockRemoved': 40, 'BlockStored': 32}

sample events:
  ['BlockRemoved', [14424261397400399812], 'GPU', 0]
  ['BlockRemoved', [4111775956169861258], 'GPU', 0]
  ['BlockStored', [912756389032115660], None,
    [2414, 220, 16, 12, 2548, 2911, 25, 3543, 620, 1078, 220, 16, 12, 2092, 11],
    16, None, 'GPU', None, [None], 0, 'sliding_window', 262144]
  ['BlockRemoved', [6551221865288290545], 'GPU', 0]
```

✅ 7 real ZMQ messages, 72 real KV cache events in a 25-second window.
✅ Sequence numbers monotonically increasing (`706 .. 712`) → subscribers can detect drops.
✅ Both event types observed:
   - `BlockStored` (32) — triggered by prefill of the new prompts.
   - `BlockRemoved` (40) — triggered by KV cache eviction under load.
✅ Event payload structure matches vLLM's `KVCacheEvent` (block hash, token ids, block size, device, cache kind `sliding_window`, context length 262144).

---

## Summary

| # | Check | Result |
|---|-------|--------|
| 1 | Operator injects `--kv-events-config` into vLLM command | ✅ |
| 2 | Pod exposes container port `kv-events`=5557 | ✅ |
| 3 | ClusterIP service exposes port `kv-events`=5557 | ✅ |
| 4 | vLLM logs `Starting ZMQ publisher thread` | ✅ |
| 5 | Port 5557 is actually listening in the pod | ✅ |
| 6 | ZMQ subscriber receives real `BlockStored`/`BlockRemoved` events tied to inference traffic | ✅ (72 events / 7 msgs / seq 706→712) |

PR #1890 works end-to-end on Kaito for a vLLM workspace. Subscribers running in the same cluster can connect to `svc/<workspace>:5557` and receive vLLM KV cache lifecycle events for observability, cache coordination, or KV-aware load balancing.

## Notes / caveats

- **Security**: the ZMQ stream is unauthenticated and unencrypted. PR #1890 correctly gates the service port on ClusterIP only. If a workspace opts into a `LoadBalancer` service (`kaito.sh/enablelb: "True"`), the `kv-events` port is intentionally not exposed — users who need external access should create their own Service + NetworkPolicy.
- **User override wins**: if `--kaito-config-file` explicitly sets a different `--kv-events-config`, the operator does not overwrite it (unit test `TestGetInferenceCommandVLLMKVCacheEventsDefault`).
- **LMCache's own KV events** (`enable_kv_events` in LMCache config) is a separate feature not touched by this PR.

---

## 7. Who actually consumes KV events? (KAITO + GAIE + llm-d)

A valid follow-up question: *now that vLLM emits KV events, who in the KAITO stack subscribes to them?* Short answer:

> **The `llm-d-inference-scheduler` EPP that KAITO's GAIE integration wires up. And *only* that. Which means KV events only have a real consumer when the KAITO InferenceSet (a.k.a. MultiRoleInference) controller is enabled.**

### The GAIE / llm-d path

KAITO's [Gateway API Inference Extension docs](https://kaito-project.github.io/kaito/docs/gateway-api-inference-extension) call this out explicitly:

> The EPP image is overridden to use the [llm-d inference scheduler](https://github.com/llm-d/llm-d-inference-scheduler), which builds on the GWIE EPP with advanced scheduling plugins including **KV cache-aware routing**, prefill/decode (P/D) disaggregation, and pluggable filters/scorers.

The llm-d scheduler ships a `KVCache` scorer that subscribes to each backend pod's vLLM ZMQ publisher (`tcp://<pod>:5557`), builds a `{block_hash → pod}` index, and gives higher scores to pods that already hold the request's prefix — so identical / prefix-overlapping requests keep landing on the same replica, cutting TTFT.

### The wiring

```
     ┌────────────────────────────────────────────────────────────┐
     │ KAITO InferenceSet (MultiRoleInference) controller         │
     │  → Flux HelmRelease → GWIE InferencePool + EPP             │
     │       (EPP image = llm-d-inference-scheduler)              │
     │            │                                               │
     │            │  ZMQ SUB tcp://<workspace-pod>:5557           │
     └────────────┼───────────────────────────────────────────────┘
                  ▼
            KAITO Workspace pods (vLLM)
            --kv-events-config='{"enable_kv_cache_events":true}'
            containerPort/kv-events + Service port/kv-events
            ← PR #1890 makes this happen
```

So PR #1890 is not just "expose an event stream for future use" — it is the **producer half of KAITO's KV-cache-aware routing story**. Without it the llm-d KVCache scorer has nothing to subscribe to.

### But: only useful when MultiRoleInference is enabled

The consumer (`llm-d` EPP) only exists in the cluster when:

1. `featureGates.enableMultiRoleInferenceController=true` (default from KAITO v0.11.0+), **and**
2. `featureGates.gatewayAPIInferenceExtension=true`.

If `enableMultiRoleInferenceController` is off, there is no InferenceSet controller, no Flux-managed InferencePool, no EPP — so nothing in the cluster will ever subscribe to port 5557. In that mode, enabling the vLLM ZMQ publisher would just:

- spawn an extra ZMQ publisher thread inside every vLLM engine,
- hold an open TCP socket on 5557 in every workspace pod,
- add a container port and a Service port that point at a producer with no consumer.

All cost, no benefit.

### What PR #1890 does about it

Gate all three operator-side changes on `FeatureFlagEnableMultiRoleInferenceController`:

| File | Change |
|------|--------|
| `pkg/model/interface.go` | Only inject `--kv-events-config` into the vLLM command line when MRI is on. |
| `pkg/workspace/inference/preset_inferences.go` | Only add `containerPort/kv-events=5557` to the pod spec when the runtime is vLLM **and** MRI is on. |
| `pkg/workspace/manifests/manifests.go` | Only expose `Service port/kv-events=5557` for vLLM/ClusterIP **and** when MRI is on. (LoadBalancer is still always excluded to avoid publishing the unauth ZMQ stream.) |

Unit tests updated to match:

- **New**: `TestGetInferenceCommandVLLMKVCacheEventsDisabledWithoutMRI` — asserts the flag is **not** injected when MRI is off.
- Pinned `MRI=true` in `TestGetInferenceCommandVLLMKVCacheEventsDefault`, `TestGeneratePresetInference` (its `expectedParams` includes `kv-events-config`), and `TestGenerateServiceManifest_KVEventsPort` so those tests remain deterministic.
- Extended `TestGenerateServiceManifest_KVEventsPort` with a **vLLM + ClusterIP but MRI=false** case that asserts the Service port is **not** added.

All targeted tests pass:

```
$ go test -run 'KVCache|KVEvents' ./pkg/model/ ./pkg/workspace/manifests/ -v
=== RUN   TestGetInferenceCommandVLLMKVCacheEventsDefault
--- PASS: TestGetInferenceCommandVLLMKVCacheEventsDefault (0.00s)
=== RUN   TestGetInferenceCommandVLLMKVCacheEventsDisabledWithoutMRI
--- PASS: TestGetInferenceCommandVLLMKVCacheEventsDisabledWithoutMRI (0.00s)
=== RUN   TestBuildVLLMInferenceCommandDisablesKVCacheForHybridModels
--- PASS: TestBuildVLLMInferenceCommandDisablesKVCacheForHybridModels (0.00s)
=== RUN   TestBuildVLLMInferenceCommandNoKVCacheOverrideForNonHybrid
--- PASS: TestBuildVLLMInferenceCommandNoKVCacheOverrideForNonHybrid (0.00s)
PASS
ok  	github.com/kaito-project/kaito/pkg/model	0.011s
=== RUN   TestGenerateServiceManifest_KVEventsPort
--- PASS: TestGenerateServiceManifest_KVEventsPort (0.00s)
PASS
ok  	github.com/kaito-project/kaito/pkg/workspace/manifests	0.020s

$ go test -run TestGeneratePresetInference ./pkg/workspace/inference/
ok  	github.com/kaito-project/kaito/pkg/workspace/inference	0.021s
```

### Practical implication for KAITO users

| KAITO config | KV events behavior |
|---|---|
| `enableMultiRoleInferenceController=true` + `gatewayAPIInferenceExtension=true` (KAITO ≥ v0.11 default when GAIE is on) | ✅ vLLM emits KV events on 5557; llm-d EPP subscribes; KV-cache-aware routing works. |
| `enableMultiRoleInferenceController=true` only | ✅ Publisher runs (harmless — you can attach your own subscriber for observability, custom routing, LMCache-style KV offload, etc.). |
| `enableMultiRoleInferenceController=false` | ⛔ No publisher, no container port, no Service port — zero overhead when the feature can't be used. |

### What's still needed to fully turn on KV-cache-aware routing

PR #1890 unblocks the producer side. To close the loop on a KAITO GAIE cluster, the InferenceSet controller must also render the EPP `HelmRelease` with the llm-d KV-cache scorer plugin actually **enabled** (llm-d exposes it via env such as `ENABLE_KVCACHE_AWARE_SCORER=true` and optionally `KVCACHE_INDEXER_REDIS_ADDR` for cross-EPP sharing). Whether Kaito's InferenceSet controller already sets that today, or needs a small values-passthrough PR, is the next thing to check on the InferenceSet controller side (`pkg/inferenceset/...`).

