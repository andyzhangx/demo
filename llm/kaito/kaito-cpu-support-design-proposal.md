# KAITO CPU Support Design Proposal

## Background

KAITO already has partial building blocks related to CPU inference, but the main Workspace/InferenceSet path is still GPU/CUDA-first.

Based on recent source/doc inspection:

- KAITO `kaito-base` is currently built from `docker/presets/models/tfs/Dockerfile`.
- That Dockerfile installs CUDA 12.9 variants of torch/vLLM/LMCache and includes CUDA-specific runtime provisioning logic.
- KAITO custom model examples still point to `mcr.microsoft.com/aks/kaito/kaito-base:<tag>` and commonly use GPU SKUs.
- AIKit already contains CPU-oriented runner patterns that may be relevant for later phases.
- KAITO runtime selection today is mostly expressed as `transformers` vs `vllm`, not as a first-class CPU/GPU execution target.

This means CPU support should be treated as a productized design change, not just “run current image on a CPU node”.

---

## Problem Statement

Today, KAITO does not provide a clean first-class experience for CPU-based models because:

1. **Base image is CUDA-oriented**
   - current `kaito-base` is optimized for GPU runtimes, not CPU-only deployment.
2. **Controller and provisioning flow are GPU-centric**
   - node selection, instance type assumptions, and sizing logic largely assume GPU workloads.
3. **Runtime handling is still GPU-first for CPU scenarios**
   - even though KAITO already distinguishes `transformers` vs `vllm`, the surrounding validation, image selection, and scheduling behavior are still biased toward GPU execution.
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

## Phase 1 Scope

Phase 1 is intentionally narrow.

### In scope

- CPU custom/BYO model support
- `kaito.sh/runtime: transformers` as the default CPU path
- optional `kaito.sh/runtime: vllm` on CPU, only if KAITO explicitly supports and validates that path
- CPU-aware validation, image selection, and scheduling/provisioning
- the new CPU images needed for those runtime paths

### Out of scope

- MultiRoleInference / P/D disaggregation on CPU
- speculative decoding on CPU
- DeepGEMM / CUDA toolkit provisioning on CPU
- NIXL-based distributed runtime features
- full preset parity on CPU
- aggressive CPU autoscaling optimization
- new runtime APIs or new CPU runtime families beyond the existing `transformers` / `vllm` choices

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

For Phase 1, this runtime model is sufficient in principle because KAITO already distinguishes:

- `transformers`
- `vllm`

The gap is not the lack of another runtime name. The gap is that the current implementation around these runtimes is still largely GPU/CUDA-first. CPU support therefore needs CPU-aware validation, image selection, and scheduling around the existing runtime choices.

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

The immediate goal is to make the existing runtime choices work cleanly for CPU scenarios, not to expand KAITO's runtime surface area.

In other words, the main problem is not “KAITO lacks a runtime field.” The main problem is that KAITO's implementation around `transformers` and `vllm` is still GPU/CUDA-first.

### Phase 1 supported combinations

- `kaito.sh/runtime: transformers` + CPU scheduling/resources
- `kaito.sh/runtime: vllm` + GPU scheduling/resources
- optionally `kaito.sh/runtime: vllm` + CPU scheduling/resources, if that path is explicitly supported

Anything beyond that should be treated as later-phase work.

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

## Runtime recommendation for Phase 1 CPU support

For this proposal, Phase 1 should stay tightly aligned to the runtime choices KAITO already exposes today:

- `kaito.sh/runtime: transformers`
- `kaito.sh/runtime: vllm`

### Recommended Phase 1 default

If Phase 1 optimizes for **minimum code change** and **maximum compatibility with mainstream Hugging Face CPU workloads**, the default CPU path should be:

- **default CPU runtime:** `kaito.sh/runtime: transformers`
- **optional CPU runtime:** `kaito.sh/runtime: vllm`, only if KAITO explicitly supports that path

### Why `transformers` should be the default CPU path

For the majority of mainstream Hugging Face models, the native distribution format is still:

- `transformers`
- PyTorch / safetensors
- `AutoModel*` / `pipeline` loading patterns

That makes the existing `transformers` runtime the broadest and lowest-friction starting point for CPU support, especially for:

- text generation with small or medium causal LMs
- embeddings
- rerankers
- classifiers
- most custom/BYO Hugging Face models

It is also the best match for the current CPU POC because it:

- reuses the existing Hugging Face-style serving path
- avoids introducing a new model format requirement
- minimizes controller and image changes
- matches the most common user expectation for "run a Hugging Face model on CPU"

### Where CPU vLLM fits in Phase 1

CPU vLLM is worth supporting only as an explicit, bounded path.

It should not become the default CPU assumption, because:

- vLLM remains historically GPU-first
- the CPU path has different operational and tuning characteristics than the GPU path
- not every CPU use case needs the extra runtime-specific complexity

So the right Phase 1 stance is:

- `transformers` on CPU is the baseline supported path
- `vllm` on CPU is optional and should be treated as a separately validated path

### How the current CPU example should be classified

The example at:

- `examples/custom-model-integration/custom-model-deployment-cpu.yaml`

is a CPU **transformers** example.

Why:

- it sets `kaito.sh/runtime: transformers`
- it launches `/workspace/tfs/inference_api.py`
- it loads a standard Hugging Face model ID directly
- it forces CPU execution with `--device_map cpu`
- it uses the transformers-oriented CPU image path

This matters because the current POC proves the minimum-change **transformers on CPU** flow is viable. It does not by itself prove that additional CPU runtime families are needed in Phase 1.

### Phase 1 support matrix

| Scenario | Status | Runtime |
|---|---|---|
| CPU custom Hugging Face model | supported | `kaito.sh/runtime: transformers` |
| CPU embeddings / rerankers / classifiers | supported | `kaito.sh/runtime: transformers` |
| CPU vLLM workspace | optional | `kaito.sh/runtime: vllm` |
| CPU presets | later | n/a |
| CPU MRI / speculative decoding | out of scope | n/a |

Later phases can expand beyond this narrow scope.

---

## Detailed Code Change Areas

## 1. API / CRD changes

Phase 1 does **not** need a new `runtimeProfile` field. It should keep using the existing `kaito.sh/runtime` annotation.

### Expected code touchpoints

- validation/defaulting logic around supported CPU combinations
- docs/examples
- controller logic that interprets runtime plus hardware/resource intent

---

## 2. Runtime resolution logic

Current logic already resolves runtime mostly between vLLM and transformers. For CPU support, that logic should be extended to resolve:

- effective runtime (`transformers` or `vllm`)
- execution target characteristics (CPU vs GPU)
- supported feature set
- image selection

### Add helpers like

- `GetWorkspaceRuntime(...)`
- `IsCPURuntime(...)`
- `RequiresGPU(...)`
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

The current benchmark flow is vLLM-centric. For Phase 1, disable benchmark by default for CPU runtime paths, or keep only a lightweight CPU smoke benchmark.

---

## 6. Model format support

Phase 1 should focus on standard Hugging Face model flows on CPU, with optional CPU vLLM support only where KAITO explicitly validates it. Large GPU-oriented checkpoints on CPU, CUDA-image reuse, and broader CPU model-format expansion should stay out of scope for this phase.

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

See **Phase 1 Scope** above for exclusions.

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

**Mitigation:** keep Phase 1 narrow, centralize effective runtime/image selection, and enforce the scoped combinations listed earlier.

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

1. keep `kaito-base` unchanged for the existing GPU path
2. add `kaito-base-tfs-cpu` and `kaito-base-vllm-cpu`
3. make validation, image selection, and scheduling/provisioning CPU-aware
4. ship the narrow Phase 1 scope first, then expand later

This preserves backward compatibility while making the CPU runtime split explicit and maintainable.

---

## Proposed Initial Work Breakdown

### PR 1: validation + runtime handling
- keep using `kaito.sh/runtime`
- add validation rules for supported CPU runtime combinations
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
- optional CPU vLLM example if that path is intentionally supported
- transformers CPU embedding example
- support matrix doc

---

## Appendix: Summary Answer to the Original Questions

### What code/config changes are needed?

At minimum:

- runtime handling based on the existing `kaito.sh/runtime` annotation
- validation changes
- controller/workspace generation changes
- node provisioning/scheduling changes
- benchmark/feature gating changes
- docs/examples updates

All of these should stay within the narrow Phase 1 scope defined above.

### What new images need to be built?

Required:

- `kaito-base-tfs-cpu`
- `kaito-base-vllm-cpu`

Optional later:

- additional CPU-specialized runtime images if KAITO broadens beyond the current transformers/vLLM scope
- possible Dockerfile-source consolidation, while still keeping separate CPU runtime images

### What is the implication of current `kaito-base`?

It confirms that current KAITO inference packaging is GPU-oriented and already bundles both GPU runtime paths into one combined image. CPU support should therefore be implemented as an explicit runtime/image split, not as a soft extension of the existing base image.
