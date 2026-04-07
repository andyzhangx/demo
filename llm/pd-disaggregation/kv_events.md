# KV Events in PD Disaggregation

KV events let the router know **which KV cache blocks exist on which worker**, enabling intelligent prefix-aware routing decisions.

## Without KV Events (Round-Robin)

```
Request 1: "Tell me about Kubernetes"     → Prefill Worker A (computes KV cache)
Request 2: "Tell me about Kubernetes pods" → Prefill Worker B (recomputes entire KV cache)
```

Request 2 shares a large common prefix with Request 1, but the router doesn't know this — it sends the request to Worker B, wasting GPU compute to recalculate KV cache from scratch.

## With KV Events (kv_aware Policy)

### Step 1: Workers Broadcast KV Events (via ZMQ PUB/SUB)

```
Worker A publishes: "kv@" topic → block_ids=[hash("Tell"), hash("me"), hash("about"), hash("Kubernetes")]
                                → engine_id=A
```

The router's KVBlockIndex records:

```
hash("Tell")       → Worker A
hash("me")         → Worker A
hash("about")      → Worker A
hash("Kubernetes") → Worker A
```

### Step 2: New Request Arrives, Router Does Prefix Matching

```
Request 2: "Tell me about Kubernetes pods"
  → tokenize → [hash("Tell"), hash("me"), hash("about"), hash("Kubernetes"), hash("pods")]
  → lookup KVBlockIndex: first 4 blocks are all on Worker A!
  → prefix match score: 4/5 = 80%
  → route to Worker A ✅
```

Worker A only needs to compute the single new block for `hash("pods")`, reusing the existing 4 blocks of KV cache.

## Real-World Example: Multi-Turn Chat with Shared System Prompt

```
User 1: {"system": "You are a helpful assistant", "user": "what is 1+1?"}
  → Worker A prefills, KV events broadcast system prompt blocks

User 2: {"system": "You are a helpful assistant", "user": "what is 2+2?"}
  → Router finds system prompt blocks on Worker A
  → Routes to Worker A, reuses system prompt KV cache
  → Prefill only needs to compute "what is 2+2?" portion, saving ~50% compute
```

## Data Flow

```
vLLM Workers ──ZMQ PUB──→ KVEventPool ──→ KVBlockIndex (hash → worker mapping)
                              ↑                    ↓
                         port 5557            KvAwarePolicy
                         topic "kv@"          (prefix match routing)
                                                   ↓
                              Client Request ──→ Router ──→ Best Worker
```

**In short: KV events = workers tell the router "what I have cached", and the router uses this to send similar requests to the same worker, maximizing KV cache hit rate.**

## Understanding `remote_block_ids` in KV Transfer

When a prefill request completes, the response includes `kv_transfer_params` with a `remote_block_ids` field:

```json
"kv_transfer_params": {
  "do_remote_prefill": true,
  "remote_block_ids": [3],
  "remote_engine_id": "90416045-3658-4d9b-b989-a6b4809ad9ff",
  "remote_host": "10.244.8.146",
  "remote_port": 5600
}
```

### What are `remote_block_ids`?

vLLM uses [paged attention](https://arxiv.org/abs/2309.06180) to manage GPU memory — KV cache is split into fixed-size **blocks** (default: 16 tokens per block). `remote_block_ids` are the **GPU memory block numbers** on the prefill worker where this request's KV cache is stored.

In the example above, `remote_block_ids: [3]` means the prompt "what is kubernetes?" (~5-6 tokens) fits in a single block (#3) on the prefill worker's GPU.

### How the Decode Worker Uses Them

The decode worker receives these block IDs and uses **NIXL** (a high-performance network transport, often RDMA-capable) to pull the KV cache data directly from the prefill worker's GPU memory at those specific block locations — no recomputation needed.

### Block Count Scales with Prompt Length

| Prompt Length | Approx Blocks (16 tokens/block) | Example `remote_block_ids` |
|---|---|---|
| ~16 tokens | 1 | `[3]` |
| ~200 tokens | ~13 | `[3, 7, 12, 15, 22, ...]` |
| ~2000 tokens | ~125 | `[3, 7, 12, 45, 67, ...]` (125 entries) |

---

## llm-d KV Events Deep Dive

The [llm-d](https://github.com/llm-d/llm-d) project implements a production-grade KV events collection system through the [`llm-d-kv-cache`](https://github.com/llm-d/llm-d-kv-cache) library. Below is a detailed breakdown of the architecture, event protocol, and concrete examples.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Inference Scheduler (EPP)               │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │  Scheduler    │──▶│kvcache.Indexer│──▶│kvblock.Index │ │
│  │  (Score pods) │◀──│              │   │(LRU cache)   │ │
│  └──────────────┘   └──────────────┘   └──────┬───────┘ │
│                                                │ Update  │
│                                        ┌───────┴───────┐ │
│                                        │kvevents.Pool  │ │
│                                        │(ZMQ SUB)      │ │
│                                        └───────┬───────┘ │
└────────────────────────────────────────────────┼─────────┘
                                                 │ ZMQ PUB/SUB
                    ┌────────────────────────────┼────────────┐
                    │          vLLM Fleet         │            │
                    │  ┌─────────┐  ┌─────────┐  │            │
                    │  │ vLLM    │  │ vLLM    │  │            │
                    │  │ Pod 1   │  │ Pod 2   │  │ ...        │
                    │  │(ZMQ PUB)│  │(ZMQ PUB)│  │            │
                    │  └─────────┘  └─────────┘  │            │
                    └─────────────────────────────────────────┘
```

### Event Types

vLLM emits 3 types of KV events via ZMQ (msgpack encoded):

| Event | Description |
|---|---|
| `BlockStored` | A KV block was created/cached — contains block hash keys and pod identity |
| `BlockRemoved` | A KV block was evicted from cache |
| `AllBlocksCleared` | All blocks cleared (e.g., engine restart) |

### ZMQ Topic Format

```
kv@<pod-id>@<model-name>
```

Example: `kv@vllm-pod-abc123@Qwen/Qwen3-8B`

### Event Processing Pipeline

1. **vLLM** publishes events as ZMQ multipart messages: `[topic, sequence_number, msgpack_payload]`
2. **`kvevents.Pool`** subscribes via ZMQ SUB, uses `EngineAdapter.ShardingKey()` (FNV-1a hash on pod-id) to shard events to worker queues — guaranteeing per-pod ordering
3. **`EngineAdapter` (vLLM adapter)** parses the topic format and decodes msgpack payload into `EventBatch`
4. **Workers** apply events to `kvblock.Index`: `BlockStored` → `Index.Add()`, `BlockRemoved` → `Index.Evict()`

### Two Subscription Modes

| Mode | Config | Use Case |
|---|---|---|
| **Global socket** | `zmqEndpoint: "tcp://..."` | All pods publish to a single ZMQ endpoint |
| **Pod discovery** | `discoverPods: true` | Auto-creates per-pod ZMQ subscribers via `SubscriberManager` |

### KV Block Hashing (Must Match vLLM!)

The indexer must produce identical block hashes as vLLM:

- **Token Chunking**: Tokens are grouped into fixed-size chunks (default: 16, configurable via `blockSize`)
- **Hash Algorithm**: Chained FNV-64a hash over CBOR-encoded `[parentHash, tokenChunk, extra]` tuple
- **Hash Seed**: Must match the `PYTHONHASHSEED` env var on vLLM pods
- **Extra Parameter**: Differentiates LoRA adapters, multi-modal content, etc. (`nil` for standard prompts)

> ⚠️ **Critical**: `blockSize` and `PYTHONHASHSEED` must be identical between vLLM and the indexer, otherwise block hashes won't match and prefix cache scoring will fail silently.

### Speculative Indexing

The `PrecisePrefixCacheScorer` plugin supports **speculative indexing** — after routing a request to a pod, it proactively adds predicted cache entries to the index before the actual KV events arrive from vLLM. This closes the "blind spot" between routing decision and event arrival (~2s default TTL).

```yaml
- type: precise-prefix-cache-scorer
  parameters:
    speculativeIndexing: true
    speculativeTTL: "2s"
```

### Concrete Example: vLLM KV Events Configuration

#### vLLM Side (Python)

```python
from vllm.config.kv_events import KVEventsConfig

kv_events_config = KVEventsConfig(
    enable_kv_cache_events=True,
    publisher="zmq",
    endpoint="tcp://*:5557",
    topic="kv@my-pod@Qwen/Qwen3-8B",
)

llm = LLM(
    model="Qwen/Qwen3-8B",
    enable_prefix_caching=True,
    kv_events_config=kv_events_config,
    block_size=16,
    prefix_caching_hash_algo="sha256_cbor",
)
```

#### Listening for Events (Python)

```python
import zmq
from msgspec.msgpack import Decoder
from vllm.distributed.kv_events import KVEventBatch, BlockStored, BlockRemoved

ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("tcp://localhost:5557")
sub.setsockopt_string(zmq.SUBSCRIBE, "kv@")  # subscribe to all KV events

topic, seq_bytes, payload = sub.recv_multipart()
event_batch = Decoder(type=KVEventBatch).decode(payload)

for event in event_batch.events:
    if isinstance(event, BlockStored):
        print(f"Block stored: keys={event.block_hashes}, pod={event.engine_id}")
    elif isinstance(event, BlockRemoved):
        print(f"Block removed: key={event.block_hash}")
```

#### EPP Scheduler Configuration (YAML)

```yaml
apiVersion: inference.networking.x-k8s.io/v1alpha1
kind: EndpointPickerConfig
plugins:
  - type: single-profile-handler
  - type: decode-filter
  - type: precise-prefix-cache-scorer
    parameters:
      tokenProcessorConfig:
        blockSize: 64                 # must match vLLM block size
        hashSeed: "42"               # must match vLLM PYTHONHASHSEED
      indexerConfig:
        kvBlockIndexConfig:
          enableMetrics: true
      kvEventsConfig:
        discoverPods: true            # auto-discover and subscribe to pods
        # Alternative: global socket mode
        # zmqEndpoint: "tcp://zmq-aggregator:5557"
        # topicFilter: "kv"
  - type: kv-cache-utilization-scorer
  - type: queue-scorer
  - type: max-score-picker
schedulingProfiles:
  - name: default
    plugins:
      - pluginRef: decode-filter
      - pluginRef: precise-prefix-cache-scorer
        weight: 2.0
      - pluginRef: kv-cache-utilization-scorer
        weight: 1.0
      - pluginRef: queue-scorer
        weight: 1.0
      - pluginRef: max-score-picker
```

#### Online Demo with Helm

```bash
# Deploy vLLM with KV events enabled
helm upgrade --install demo ./vllm-setup-helm \
  --set secret.hfTokenValue=$HF_TOKEN \
  --set kvCacheManager.enabled=true \
  --set vllm.model.name="Qwen/Qwen3-8B" \
  --set vllm.replicaCount=2

# Port-forward
kubectl port-forward svc/demo-kv-cache-manager 8080:8080
kubectl port-forward svc/demo-vllm-qwen3-8b 8000:8000

# Step 1: Score before inference (expect empty scores)
curl -X POST "http://localhost:8080/score_completions" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Tell me about Kubernetes", "model":"Qwen/Qwen3-8B"}'

# Step 2: Run inference (triggers KV block creation → KV events emitted)
curl -X POST "http://localhost:8000/v1/completions" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Tell me about Kubernetes","max_tokens":50}'

# Step 3: Score again (now shows cache hit scores per pod)
curl -X POST "http://localhost:8080/score_completions" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Tell me about Kubernetes", "model":"Qwen/Qwen3-8B"}'
```

### Index Backend Options

| Backend | Description |
|---|---|
| **In-Memory (default)** | Two-level LRU cache (`hashicorp/golang-lru`), fast, ephemeral |
| **Cost-Aware Memory** | `hypermodeinc/ristretto` based, memory-footprint-aware eviction |
| **Redis** | Distributed, shared across multiple indexer replicas |

### Key Repos

| Repo | Purpose |
|---|---|
| [llm-d-kv-cache](https://github.com/llm-d/llm-d-kv-cache) | Core KV events library (`kvevents/`, `kvblock/`, `kvcache/`) |
| [llm-d-inference-scheduler](https://github.com/llm-d/llm-d-inference-scheduler) | EPP with `PrecisePrefixCacheScorer` plugin |
| [llm-d](https://github.com/llm-d/llm-d) | Guides including tiered prefix cache and inference scheduling |
