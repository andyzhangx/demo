# Tensor Parallelism (TP) vs Data Parallelism (DP) in LLM Inference

## Tensor Parallelism — Splitting one model across multiple GPUs

```
GPU 0: [Layer1 upper] → [Layer2 upper] → ... → [LayerN upper]
GPU 1: [Layer1 lower] → [Layer2 lower] → ... → [LayerN lower]
         ↕ AllReduce    ↕ AllReduce            ↕ AllReduce
```

- A **single request's** computation is distributed across multiple GPUs for parallel execution
- Each GPU only stores a portion of the model parameters (weight matrices split by rows/columns)
- **AllReduce communication** is required after each layer to synchronize intermediate results
- **Use case: model is too large to fit on a single GPU** (e.g., 70B models need TP=4 or TP=8)

## Data Parallelism — Multiple complete model replicas handling different requests

```
GPU 0: [Full Model] → Processes Request A, C, E ...
GPU 1: [Full Model] → Processes Request B, D, F ...
```

- Each GPU has a **complete copy of the model**
- Different requests are dispatched to different replicas, **no interference**
- **No cross-GPU communication** during inference, throughput scales linearly
- **Use case: model fits on a single GPU, use multiple GPUs to increase throughput**

## Core Differences

| | **Tensor Parallelism (TP)** | **Data Parallelism (DP)** |
|---|---|---|
| **What's split** | Model (weight matrices) | Requests (different requests to different replicas) |
| **Per-GPU storage** | 1/TP of the model | Full model |
| **Cross-GPU communication** | AllReduce every layer, **bandwidth-sensitive** | **Zero communication** during inference |
| **Latency** | Reduced (multiple GPUs compute one request in parallel) | Unchanged (each request still computed by a single replica) |
| **Throughput** | Slightly improved | Linear scaling (×DP) |
| **Use case** | Large models that don't fit on a single GPU | Smaller models where you want higher QPS |

## Can Be Combined

```
2 GPU node, TP=1, DP=2:  One full model per GPU
8 GPU node, TP=4, DP=2:  2 replicas, each spanning 4 GPUs
8 GPU node, TP=8, DP=1:  1 replica spanning all 8 GPUs
```

## Real-World Example: KAITO OOM Issue (#1905)

llama-3.1-8b-instruct fits on a single GPU (TP=1). On a 2-GPU node (Standard_NC48ads_A100_v4), vLLM auto-sets DP=2. This means there are **2 independent vLLM worker processes**, each launching its own LMCache instance. The original code only divided CPU memory by TP=1, so each worker allocated 50% of memory × 2 workers = 100%, causing OOM.

**Fix:** Divide LMCache CPU memory budget by `TP × DP` instead of just `TP`.
- Before: `220GB * 0.5 / 1 = 110GB` per worker × 2 = 220GB → OOM
- After: `220GB * 0.5 / 2 = 55GB` per worker × 2 = 110GB → OK
