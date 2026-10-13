# KAITO CPU Support Design Proposal

## Background

KAITO already has partial building blocks related to CPU inference, but the main Workspace/InferenceSet path is still GPU/CUDA-first.

Based on recent source/doc inspection:

- KAITO `kaito-base` is currently built from `docker/presets/models/tfs/Dockerfile`.
- That Dockerfile installs CUDA 12.9 variants of torch/vLLM/LMCache and includes CUDA-specific runtime provisioning logic.
- KAITO custom model examples still point to `mcr.microsoft.com/aks/kaito/kaito-base:<tag>` and commonly use GPU SKUs.
- AIKit already contains CPU runners such as:
  - `runners/llama-cpp-cpu.yaml`
  - `runners/vllm-cpp-cpu.yaml`
- KAITO runtime selection today is mostly expressed as `transformers` vs `vllm`, not as a first-class CPU/GPU execution target.

This means CPU support should be treated as a productized design change, not just “run current image on a CPU node”.

---

## Problem Statement

Today, KAITO does not provide a clean first-class experience for CPU-based models because:

1. **Base image is CUDA-oriented**
   - current `kaito-base` is optimized for GPU runtimes, not CPU-only deployment.
2. **Controller and provisioning flow are GPU-centric**
   - node selection, instance type assumptions, and sizing logic largely assume GPU workloads.
3. **Runtime abstraction is incomplete for CPU**
   - CPU-friendly backends such as `llama.cpp` are not modeled as first-class KAITO runtime choices.
4. **Advanced inference features are GPU-driven**
   - speculative decoding, P/D disaggregation, NIXL, DeepGEMM, and some benchmark paths are tightly coupled to vLLM/CUDA.

---

## Goals

1. Add **first-class support for CPU-based model inference** in KAITO.
2. Support both:
   - **CPU custom/BYO models**
   - selected **CPU presets** in later phases
3. Keep the GPU path stable and backward compatible.
4. Avoid overloading the existing CUDA `kaito-base` with CPU semantics.

## Non-Goals (Phase 1)

The initial CPU support should **not** try to support all GPU-era features.

Phase 1 non-goals:

- MultiRoleInference P/D disaggregation on CPU
- speculative decoding on CPU
- DeepGEMM / CUDA toolkit provisioning on CPU
- NIXL-based distributed runtime features
- full parity with all GPU presets
- aggressive CPU autoscaling optimization

---

## Design Principles

### 1. Separate backend/runtime from hardware target
CPU support is not just a different node type. It changes:

- runtime backend
- container image
- startup command
- resource estimation
- scheduling
- supported features

### 2. Do not reuse CUDA `kaito-base` as the official CPU base
Even if it can sometimes run on CPU nodes, it is too GPU-specific and too heavy to be the maintained CPU solution.

### 3. Start with CPU custom model support first
The lowest-risk path is:

- enable CPU custom/BYO model serving
- validate image/runtime scheduling flow
- add preset support later

---

## Current-State Assessment

### Image layer
Current `kaito-base` characteristics:

- installs CUDA `cu129` packages
- includes vLLM/CUDA-oriented dependencies
- includes CUDA toolkit provision helper logic
- assumes GPU-centric performance stack

### API/runtime layer
Current runtime selection in KAITO is centered on:

- `huggingface/transformers`
- `vllm`

This is insufficient for CPU because a realistic CPU path often wants:

- `llama.cpp` for GGUF/quantized CPU inference
- CPU transformers for embeddings/rerankers/classifiers
- optionally `vllm-cpp-cpu` or AIKit-aligned CPU runners later

### Control plane / scheduling layer
Current code paths strongly suggest GPU assumptions in:

- node auto-provisioning
- BYO node auto-selection
- insufficient GPU error handling
- instance type expectations
- resource validation/sizing

---

## Recommended Architecture

## 1. Reuse the existing runtime annotation in Phase 1

For Phase 1, KAITO does **not** need a new `runtimeProfile` field.

KAITO already has a runtime selector:

```yaml
apiVersion: kaito.sh/v1beta1
kind: Workspace
metadata:
  name: workspace-custom-llm-cpu
  annotations:
    kaito.sh/runtime: transformers
```

That existing annotation is enough for the initial CPU support scope, as long as Phase 1 only supports the runtimes KAITO already understands:

- `transformers`
- `vllm`

### Why this is enough for Phase 1

The current Phase 1 goal is not to introduce new runtime families such as:

- `llama.cpp`
- GGUF-specific runners
- `vllm-cpp-cpu`
- other AIKit-aligned CPU backends

Instead, the immediate goal is narrower:

- support **CPU custom/BYO models** using the existing `transformers` runtime
- optionally support a **CPU vLLM path** if KAITO decides to productize that path
- keep using the current `kaito.sh/runtime` selector rather than adding a second runtime API

In other words, the main problem is not “KAITO lacks a runtime field.”
The main problem is that KAITO's implementation is still GPU/CUDA-first.

### Phase 1 supported combinations

Phase 1 should continue to use the existing runtime annotation and add CPU-aware behavior around it.

Supported combinations:

- `kaito.sh/runtime: transformers` + CPU scheduling/resources
- `kaito.sh/runtime: vllm` + GPU scheduling/resources
- optionally `kaito.sh/runtime: vllm` + CPU scheduling/resources, if that path is explicitly supported

Phase 1 should **not** introduce:

- `runtimeProfile`
- a separate `accelerator` API field
- new runtime family names like `llama-cpp-cpu`

Those can be revisited later if KAITO eventually needs to expose more than the current `transformers` and `vllm` choices.

---

## 2. Add CPU-aware validation around existing runtimes

Admission and validation must reject invalid combinations early, but this can be done without adding a new runtime field.

### Examples of validation rules

Allowed:

- `kaito.sh/runtime: transformers` on CPU nodes
- `kaito.sh/runtime: vllm` on GPU nodes
- optionally `kaito.sh/runtime: vllm` on CPU nodes, if that path is intentionally supported

Rejected:

- `kaito.sh/runtime: vllm` with GPU-only assumptions but no usable GPU resources
- `kaito.sh/runtime: transformers` combined with GPU-only preset assumptions
- MultiRoleInference with CPU runtime in Phase 1
- any CPU path that still depends on unsupported GPU/CUDA-only features

### Files likely needing changes

- `api/v1beta1/*validation*.go`
- `api/v1alpha1/workspace_validation.go`
- `pkg/inferenceset/inferenceset_custom_model.go`
- helper functions that compute the effective runtime and supported feature set

---

## 3. Make provisioning and scheduling CPU-aware

### Required behavior

For CPU workloads, KAITO should:

- allow CPU VM SKUs
- avoid `nvidia.com/gpu` assumptions
- avoid GPU-specific BYO node selection
- use CPU/memory sizing instead of GPU-memory sizing
- generate CPU-appropriate node selectors/tolerations

### Provisioning updates

The node provisioner should branch by the effective runtime plus hardware requirements:

- **GPU workloads** -> existing GPU SKU and GPU node logic
- **CPU workloads** -> general-purpose or memory-optimized CPU node logic

### BYO mode updates

In BYO mode, automatic instance/node selection must stop assuming a ready GPU node is required.

Instead:

- CPU runtime selections should accept CPU nodes that satisfy CPU/memory requirements
- GPU runtime selections should continue to require GPU nodes

### Likely code areas

- workspace controller reconciliation
- node provisioner implementations
- instance type validation
- resource estimation logic

---

## 4. Add backend-specific pod generation

Pod generation must branch by the effective runtime and whether the workload is CPU- or GPU-targeted, rather than trying to run everything through the same image and startup pattern.

### For `kaito.sh/runtime: vllm`
Keep the current GPU path, and add a separate CPU-serving variant only if KAITO explicitly decides to support a CPU vLLM path.

### For `kaito.sh/runtime: transformers`
Use a CPU-oriented image and Python entrypoint for CPU custom models.

### Pod-spec differences in Phase 1

| Area | `kaito.sh/runtime: vllm` on GPU | `kaito.sh/runtime: transformers` on CPU |
|---|---|---|
| image | CUDA/GPU base image | CPU base image |
| GPU request | yes | no |
| node selection | GPU nodes | CPU nodes |
| entrypoint | vLLM scripts | Python/FastAPI |
| benchmark path | existing vLLM path | optional/minimal |
| P/D support | yes | no (phase 1) |

### Likely code areas

- `pkg/utils/common_preset.go`
- `pkg/utils/workspace/helper.go`
- `pkg/workspace/inference/*`
- workspace/inferenceset controller logic that materializes Pod specs

---

## Image Strategy

## Recommendation: keep the current GPU image name and add runtime-specific CPU images

### Existing image

#### 1. `kaito-base` (current)
Keep the existing `kaito-base` image name as-is.

There is no immediate need to rename it to `kaito-base-cuda`.

The important implementation detail is that today's `kaito-base` is already a **combined GPU image**:

- it carries the Hugging Face / TFS serving path under `/workspace/tfs`
- it also carries the vLLM serving path under `/workspace/vllm`
- it installs CUDA-oriented dependencies such as `vllm`, LMCache, NIXL CUDA bindings, Ray, and related GPU runtime helpers

So GPU currently appears to have “only one Dockerfile” not because there is only one runtime, but because both GPU runtime paths are already bundled into the same image.

### Why CPU currently has two Dockerfiles

CPU is different because the two runtime paths are intentionally split:

- `docker/presets/models/tfs-cpu/Dockerfile`
- `docker/presets/models/vllm-cpu/Dockerfile`

That split exists for practical reasons:

1. **The CPU transformers path is a minimal Python-based image**
   - starts from a slim Python base
   - installs a small CPU-focused dependency set
   - is aimed at custom/BYO Hugging Face model serving

2. **The CPU vLLM path is based on the upstream vLLM CPU image**
   - starts from `vllm/vllm-openai-cpu`
   - reuses the upstream CPU vLLM runtime stack directly
   - is operationally different from the transformers CPU path

3. **Keeping them separate avoids bloating the transformers CPU image**
   - the minimal transformers CPU image should not be forced to carry the full vLLM CPU runtime stack
   - the vLLM CPU experiment should not dictate the dependency shape of the generic CPU custom-model image

In other words, CPU has two Dockerfiles today because KAITO is exposing two distinct CPU runtime implementations, while GPU still happens to package both runtime implementations into one combined image.

### New images required

#### 2. `kaito-base-tfs-cpu`

Purpose:

- CPU-only Python runtime base
- used for transformers-based CPU inference and generic custom CPU model serving

Suggested contents:

- Python slim base
- CPU-only torch wheels
- transformers
- accelerate (if needed)
- fastapi/uvicorn
- shared KAITO scripts needed for custom model serving
- no CUDA toolkit
- no CUDA wheels
- no NIXL CUDA packages

#### 3. `kaito-base-vllm-cpu`

Purpose:

- CPU vLLM runtime image for the experimental or optional vLLM-on-CPU path
- built around the upstream CPU vLLM runtime stack plus KAITO-specific entrypoints/scripts

Suggested contents:

- upstream `vllm-openai-cpu` base image
- KAITO vLLM serving scripts
- CPU-specific environment defaults for the vLLM runtime

### Naming strategy

The image naming scheme for this phase can stay simple:

- `mcr.microsoft.com/aks/kaito/kaito-base:<tag>` -> existing combined GPU image
- `mcr.microsoft.com/aks/kaito/kaito-base-tfs-cpu:<tag>` -> transformers CPU image
- `mcr.microsoft.com/aks/kaito/kaito-base-vllm-cpu:<tag>` -> vLLM CPU image

This preserves backward compatibility for the existing GPU path while making the new CPU runtime split explicit.

---

## Proposed Runtime Support Matrix

## Runtime recommendation for mainstream Hugging Face CPU models

If the question is "which runtime is most suitable today for mainstream, general-purpose CPU models on Hugging Face", the practical answer is:

- **Primary default:** `transformers-cpu`
- **Specialized CPU LLM path:** `llama-cpp-cpu`
- **Optional later / not phase-1 default:** `vllm-cpp-cpu`

### Why `transformers-cpu` should be the default

For the majority of mainstream Hugging Face models, the native distribution format is still:

- `transformers`
- PyTorch / safetensors
- `AutoModel*` / `pipeline` loading patterns

That means `transformers-cpu` provides the widest coverage with the least friction for:

- text generation with small or medium causal LMs
- embeddings
- rerankers
- classifiers
- encoder/decoder models
- most custom/BYO Hugging Face models

This is the best phase-1 default for a minimal KAITO CPU POC because it:

- reuses the existing Hugging Face-style serving path
- avoids introducing a new model format requirement
- minimizes controller and image changes
- matches the most common user expectation for "run a Hugging Face model on CPU"

### Where `llama-cpp-cpu` fits

`llama-cpp-cpu` is highly relevant for:

- GGUF models
- quantized CPU-first LLM serving
- cost-sensitive, low-throughput chat/inference scenarios on CPU

However, it should be treated as a **specialized LLM runtime**, not the default answer for mainstream Hugging Face CPU model support, because it usually requires a different model format and does not cover the full breadth of Hugging Face-native model types.

### Where `vllm-cpp-cpu` fits

`vllm-cpp-cpu` is better treated as an optional later exploration. It is not the broadest-coverage or lowest-risk starting point for CPU support, and it should not be the default for a minimal CPU POC.

### Why `vllm-cpp-cpu` is not the default phase-1 choice

There is real upstream work around **vLLM CPU backend** support, and it is worth tracking. However, it is still not the best default starting point for KAITO CPU support.

Reasons:

- **vLLM is historically GPU-first.** The upstream documentation explicitly notes that the CPU backend differs significantly from the GPU backend because the vLLM architecture was originally optimized for GPU use.
- **CPU deployment usually requires more tuning.** The documented CPU path depends more heavily on host-level tuning such as OpenMP thread binding, NUMA awareness, allocator choice, and in some environments Intel Extension for PyTorch (IPEX).
- **It is not the broadest compatibility path.** For mainstream Hugging Face-native models, `transformers-cpu` is still the more natural fit because it works directly with standard `AutoModel*` / safetensors / pipeline loading patterns.
- **It is not the most CPU-native LLM path either.** For quantized GGUF-style chat serving, `llama-cpp-cpu` is usually a more obvious CPU-specialized choice than a vLLM-family CPU stack.
- **The operational story is still evolving.** Upstream CPU backend docs, tuning guidance, and issue history all suggest an actively improving path rather than a universally default, low-friction production baseline.

In practice, that means `vllm-cpp-cpu` is better treated as:

- a future exploration path
- a possible AIKit/runtime-family alignment path
- an optional optimization path for selected scenarios

rather than the default answer for phase-1 KAITO CPU support.

### Recommended phase-1 default

If phase 1 must optimize for **minimum code change** and **maximum compatibility with mainstream Hugging Face CPU workloads**, the initial default should be:

- **Phase-1 default runtime:** `transformers-cpu`
- **Optional later addition for quantized LLMs:** `llama-cpp-cpu`
- **Deferred:** `vllm-cpp-cpu`

### How the current CPU example maps to these three runtime choices

The example at:

- `examples/custom-model-integration/custom-model-deployment-cpu.yaml`

is best classified as **`transformers-cpu`**, not `llama-cpp-cpu` or `vllm-cpp-cpu`.

Why:

- it sets `kaito.sh/runtime: transformers`
- it launches a Python entrypoint:
  - `/workspace/tfs/inference_api.py`
- it loads a standard Hugging Face model ID directly:
  - `microsoft/Phi-3-mini-4k-instruct`
- it forces CPU execution using:
  - `--device_map cpu`
- it uses a CPU-oriented KAITO base image rather than a llama.cpp server image

That means the current POC is effectively:

- **backend family:** Hugging Face `transformers`
- **hardware target:** CPU
- **practical classification:** `transformers-cpu`

It is **not** `llama-cpp-cpu` because it does not:

- use GGUF
- use a llama.cpp runtime/server
- use llama.cpp-style model loading or serving flags

It is **not** `vllm-cpp-cpu` because it does not:

- use a vLLM CPU runner
- use a vLLM-style serving entrypoint
- rely on a vLLM-specific CPU execution stack

This is an important distinction for the design proposal:

- the current example proves the **minimum-change `transformers-cpu` path** is viable
- it does **not** yet prove the `llama-cpp-cpu` path
- it does **not** yet justify `vllm-cpp-cpu` as the default CPU runtime

### Comparison of the three CPU runtime directions

| Runtime | Performance on CPU | Compatibility | Implementation complexity in KAITO | Best-fit scenarios | Recommended role |
|---|---|---|---|---|---|
| `transformers-cpu` | Usually the slowest for CPU LLM generation, but predictable and acceptable for small/medium models, smoke tests, embeddings, rerankers, and classifiers | **Highest** for mainstream Hugging Face-native models (`AutoModel*`, safetensors, pipeline-based loading) | **Lowest**. Reuses the existing Hugging Face-style custom model path with the fewest new abstractions | mainstream Hugging Face CPU models, BYO custom models, embeddings, rerankers, classifiers, minimal-change POCs | **phase-1 default** |
| `llama-cpp-cpu` | Usually the **best practical CPU LLM path**, especially for GGUF and quantized chat/instruct models on cost-sensitive hardware | **Medium**. Strong for GGUF/quantized LLMs, but not a generic runtime for the full Hugging Face model spectrum | **Medium**. Requires a dedicated runtime image, llama.cpp serving path, and format-aware validation/model handling | quantized CPU-first LLM serving, GGUF chat models, low-throughput cost-sensitive CPU deployments | **specialized CPU LLM path** |
| `vllm-cpp-cpu` | Potentially better than plain `transformers-cpu` in some serving-oriented cases, but usually more tuning-sensitive and less obviously practical than `llama-cpp-cpu` for CPU-first LLM workloads | **Medium to low** as a phase-1 default. It is not the broadest Hugging Face path and not the most CPU-native quantized path either | **Highest** among the three for a phase-1 rollout. It introduces more runtime-specific operational, tuning, and validation complexity | future AIKit/runtime-family alignment, deeper serving-framework experiments, selected optimized CPU serving scenarios | **optional later** |

### Phase 1

| Scenario | Support | Recommended runtime |
|---|---|---|
| CPU custom LLM (GGUF) | yes | `llama-cpp-cpu` |
| CPU custom transformers model | yes | `transformers-cpu` |
| CPU embeddings / rerankers / classifier | yes | `transformers-cpu` |
| CPU preset LLM | limited/no | later |
| CPU MultiRoleInference | no | out of scope |
| CPU speculative decoding | no | out of scope |

### Phase 2

| Scenario | Support | Recommended runtime |
|---|---|---|
| selected CPU presets | yes | `llama-cpp-cpu` or `transformers-cpu` |
| AIKit-aligned CPU runner integration | optional | `vllm-cpp-cpu` |
| CPU benchmark improvements | optional | profile-specific |

---

## Detailed Code Change Areas

## 1. API / CRD changes

Add a new runtime profile field or equivalent structured configuration.

### Example

```yaml
spec:
  template:
    inference:
      runtimeProfile: transformers-cpu
```

Possible implementation choices:

- add a new field to the inference template schema
- or add a new KAITO annotation first as an incremental step

Recommendation: **prefer a structured field** over long-term annotation hacks.

### Expected code touchpoints

- API types under `api/v1beta1`
- CRD generation
- docs/examples
- defaulting/validation logic

---

## 2. Runtime resolution logic

Current logic resolves runtime mostly between vLLM and transformers. That should be extended to resolve:

- effective runtime profile
- execution target characteristics
- supported feature set

### Add helpers like

- `GetWorkspaceRuntimeProfile(...)`
- `IsCPURuntimeProfile(...)`
- `IsGPURuntimeProfile(...)`
- `SupportsMultiRoleInference(...)`
- `SupportsSpeculativeDecoding(...)`

---

## 3. Image selection logic

Currently image assumptions are tied to the current base image and runtime. This must become profile-driven.

### Example behavior

- `kaito.sh/runtime: vllm` on GPU -> `kaito-base`
- `kaito.sh/runtime: transformers` on CPU -> `kaito-base-tfs-cpu`
- `kaito.sh/runtime: vllm` on CPU -> `kaito-base-vllm-cpu` (only if KAITO explicitly supports that path)

This logic should be centralized, not scattered across custom-model and preset flows.

---

## 4. Resource and scheduling generation

### GPU profile behavior

- preserve existing GPU requests and selectors
- preserve GPU provisioning behavior

### CPU profile behavior

- no `nvidia.com/gpu` resource requests
- CPU/memory-based scheduling
- CPU-capable node class / node selector / instance selection
- optional storage tuning for local weights/model cache

---

## 5. Benchmark and readiness behavior

The current benchmark flow is vLLM-centric.

### Recommendation

Phase 1:

- disable benchmark by default for CPU runtime profiles
- or implement a lightweight CPU profile-specific smoke benchmark only

### Why

Because throughput/latency expectations and CLI behavior differ significantly between vLLM CUDA and CPU-serving backends.

---

## 6. Model format support

CPU support should be explicit about model formats.

### Recommended Phase 1 formats

- small/medium Hugging Face transformer models via the transformers CPU path
- optionally selected models via the CPU vLLM path, if KAITO explicitly supports that runtime

### Not recommended as phase-1 default

- large BF16 GPU-oriented checkpoints directly on CPU
- CPU support that depends on CUDA-built vLLM image reuse
- introducing GGUF / `llama.cpp` as part of the initial CPU scope

---

## Implementation Plan

## Phase 1: CPU custom model MVP

### Deliverables

1. Reuse the existing `kaito.sh/runtime` annotation
2. New `kaito-base-tfs-cpu` image
3. New `kaito-base-vllm-cpu` image
4. CPU-aware validation
5. CPU-aware scheduling/provisioning
6. CPU custom model examples and docs

### User-visible scenarios

- deploy a custom Hugging Face model on CPU using `kaito.sh/runtime: transformers`
- optionally deploy a CPU vLLM workspace using `kaito.sh/runtime: vllm`, if that path is intentionally supported

### Explicit exclusions

- no MRI/PD disaggregation
- no speculative decoding
- no CPU preset parity

---

## Phase 2: Selected CPU preset support

### Deliverables

1. mark selected presets as CPU-compatible
2. define CPU resource sizing heuristics
3. improve benchmark/readiness support
4. add optional AIKit runner alignment if needed

---

## Phase 3: Advanced optimization

### Possible future work

- CPU autoscaling tuning
- profile-specific performance presets
- local weight cache optimization for CPU nodes
- broader CPU model catalog support

---

## Risks and Tradeoffs

## 1. Feature fragmentation

If CPU is added without clear runtime-specific rules, logic can spread across annotations and special cases.

**Mitigation:** keep Phase 1 narrow, centralize effective runtime/image selection, and clearly document the supported CPU runtime combinations.

## 2. Image sprawl

More images increase release complexity.

**Mitigation:** keep phase 1 minimal:

- preserve the existing combined GPU image as `kaito-base`
- add only two CPU images aligned to the two currently relevant runtimes
  - `kaito-base-tfs-cpu`
  - `kaito-base-vllm-cpu`

## 3. User confusion around “CPU support”

Users may assume every existing preset and advanced KAITO feature now works on CPU.

**Mitigation:** document scope clearly and reject unsupported combinations at validation time.

## 4. Performance expectations

CPU inference for LLMs will often be much slower than GPU inference.

**Mitigation:** position CPU support primarily for:

- lightweight workloads
- development/test
- embeddings/reranking/classification
- small quantized models
- cost-sensitive low-throughput scenarios

---

## Recommendation

The recommended path is:

1. **Do not treat current `kaito-base` as the official CPU solution.**
2. **Do not rename `kaito-base` to `kaito-base-cuda` in this phase.**
3. **Add two new CPU images aligned to the two supported CPU runtime paths:**
   - `kaito-base-tfs-cpu`
   - `kaito-base-vllm-cpu`
4. **Make validation + scheduling + provisioning CPU-aware.**
5. **Ship CPU custom model support first, then add preset support later.**

This preserves backward compatibility for the current GPU image name while making the CPU runtime split explicit and maintainable.

---

## Proposed Initial Work Breakdown

### PR 1: API + validation
- add runtime profile field / annotation
- add validation rules
- reject unsupported CPU+MRI combinations

### PR 2: CPU image pipeline
- add `kaito-base-tfs-cpu` Dockerfile/build target
- add `kaito-base-vllm-cpu` Dockerfile/build target
- document tags and release flow

### PR 3: controller + scheduling
- CPU-aware image selection
- CPU-aware resource generation
- CPU-aware BYO / auto-provision logic

### PR 4: docs + examples
- CPU custom model example
- GGUF example
- transformers CPU embedding example
- support matrix doc

---

## Appendix: Summary Answer to the Original Questions

### What code/config changes are needed?

At minimum:

- API/runtime profile support
- validation changes
- controller/workspace generation changes
- node provisioning/scheduling changes
- benchmark/feature gating changes
- docs/examples updates

### What new images need to be built?

Required:

- `kaito-base-tfs-cpu`
- `kaito-base-vllm-cpu`

Optional later:

- additional CPU-specialized runtime images if KAITO broadens beyond the current transformers/vLLM scope
- possible Dockerfile-source consolidation, while still keeping separate CPU runtime images

### What is the implication of current `kaito-base`?

It confirms that current KAITO inference packaging is GPU-oriented and already bundles both GPU runtime paths into one combined image. CPU support should therefore be implemented as an explicit runtime/image split, not as a soft extension of the existing base image.
