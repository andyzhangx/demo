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
