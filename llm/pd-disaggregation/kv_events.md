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
