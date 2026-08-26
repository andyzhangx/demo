# KAITO speculative decoding — user-facing design walkthrough

Reference issue: [kaito-project/kaito#2286](https://github.com/kaito-project/kaito/issues/2286)

This doc walks through what the proposed **preset-driven speculative decoding
toggle** feels like for users, what preset maintainers do, and where the
per-preset configuration lives in code. The design is a proposal in
issue #2286 — the code snippets below are the target shape, not what's on
`main` today.

---

## 1. Background — what is speculative decoding?

LLM decoding is fundamentally token-by-token: each step produces one token
and the GPU is heavily under-utilized. **Speculative decoding** is a pure
**lossless** speedup:

1. **Draft** — cheaply guess the next N tokens (small model / n-gram lookup /
   MTP head bundled in the checkpoint).
2. **Verify** — run the target model **once**, in parallel, over those N
   candidates.
3. Accept the matching prefix, resample at the first mismatch.

Net: multiple tokens per GPU forward pass; end-to-end tok/s goes up; the
output distribution is identical to normal decoding.

vLLM 0.10 collapsed the older `--speculative-model` / `--num-speculative-tokens`
CLI flags into a single JSON blob passed to `--speculative-config`:

```bash
# MTP — DeepSeek-R1, no extra download, no extra memory
vllm serve deepseek-ai/DeepSeek-R1 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":3}'

# ngram — zero-cost across any preset that opts in
--speculative-config '{"method":"ngram","num_speculative_tokens":5,"prompt_lookup_max":4}'
```

### The four methods (vLLM `speculative_config.method`)

| Method | How it drafts | Extra GPU memory? | Best-fit workload |
|---|---|---|---|
| `mtp` | Multi-Token Prediction head bundled in the checkpoint (DeepSeek-V3 / R1, etc.) | No | Any workload on that model family |
| `dspark` | DeepSeek-V4's own semi-autoregressive block drafting; bundled in checkpoint | No | Any workload on DeepSeek-V4 |
| `eagle` / `eagle3` | Separate draft model trained to mimic the target | Yes (separate checkpoint loaded alongside target) | General-purpose; mainstream across vLLM/SGLang/TensorRT-LLM |
| `ngram` / `suffix` | Pure lookup against prompt + generation history | No | Code completion, RAG, summarization, translation, agent tool-call echo |

### Why it isn't always on

Throughput can *regress* at high QPS (draft is wasted work when the batch is
already saturated). It has to stay **opt-in**, never default. Several vLLM
compatibility caveats also exist (pipeline parallelism, prefix caching,
chunked prefill, logprob stability, LoRA/tool-calling) that need per-preset
re-verification against KAITO's pinned vLLM version.

### Evidence cited in the issue

- DeepSeek DSpark paper (arXiv:2607.05147): **60–85% faster per-user
  generation** vs the prior MTP baseline.
- vLLM's MTP benchmark on DeepSeek-R1 (vllm-project/vllm#12755):
  **~1.6–1.7× speedup at QPS = 1**, decaying toward ~1.0× above QPS ~6–8.
- `deepseek-v3-0324` and `deepseek-r1-0528` (existing KAITO presets) already
  support `mtp` at zero extra memory / download cost.

---

## 2. The user experience

### Today (before this issue) — painful

To turn speculative decoding on for DeepSeek-R1, the user has to write a
ConfigMap that forwards raw JSON to vLLM via the `vllm:` passthrough:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-inference-config
data:
  inference_config.yaml: |
    vllm:
      # The user has to know:
      #  - that this JSON key exists
      #  - that their model supports mtp
      #  - what num_speculative_tokens value is reasonable
      speculative-config: '{"method":"mtp","num_speculative_tokens":3}'
---
apiVersion: kaito.sh/v1beta1
kind: Workspace
metadata:
  name: workspace-r1
inference:
  preset:
    name: deepseek-r1-distill-llama-8b
  config: my-inference-config
```

Every misspelled field / wrong method / wrong param → pod fails to start or
silently produces garbage.

### After — one annotation

```yaml
apiVersion: kaito.sh/v1beta1
kind: Workspace
metadata:
  name: workspace-r1
  annotations:
    kaito.sh/enable-speculative-decoding: "true"     # ← that's it
inference:
  preset:
    name: deepseek-r1-distill-llama-8b
```

`kubectl apply -f` and KAITO:

1. Looks up the preset's `SpeculativeDecoding` config (validated in advance
   by preset maintainers).
2. Injects `--speculative-config '{"method":"mtp","num_speculative_tokens":3}'`
   into the vLLM command.
3. Pod comes up with speculative decoding enabled.

The user does **not** need to know what `mtp` / `eagle` / `ngram` are,
what the parameters mean, or what the JSON schema looks like.

### Side-by-side

| Aspect | Before | After |
|---|---|---|
| Steps | Write ConfigMap + reference from Workspace | Add 1 annotation |
| Required knowledge | vLLM speculative decoding API, method taxonomy, parameter tuning | How to write `annotations:` |
| Error probability | High (JSON typo, wrong field, method/model mismatch) | Very low |
| Switching preset | Rewrite the JSON | Annotation unchanged; KAITO picks up new preset's config |
| Unsupported preset | Pod starts, inference errors out | Rejected at `kubectl apply` by admission webhook |

Expected latency win for interactive chat / agent workloads on `deepseek-r1-*`
at low-to-medium QPS: roughly **1.5×–1.7×** based on the vLLM MTP benchmark.

### What happens on an unsupported preset

```yaml
metadata:
  annotations:
    kaito.sh/enable-speculative-decoding: "true"
inference:
  preset:
    name: llama-3.1-8b-instruct    # no SpeculativeDecoding entry
```

`kubectl apply` is rejected by the admission webhook:

```
Error from server (Forbidden): admission webhook "workspace-validation.kaito.sh"
denied the request: preset "llama-3.1-8b-instruct" does not have a validated
speculative decoding configuration; remove kaito.sh/enable-speculative-decoding
annotation or choose a supported preset (e.g. deepseek-r1-*, deepseek-v3-*).
```

---

## 3. Is the per-preset config user-tunable?

**No — it is baked in by KAITO maintainers, not a user knob.** The issue is
explicit about this:

- *"no method choice exposed; each preset defines its own validated method"*
- *"typed struct ... so invalid field/method combinations can't be authored
  by mistake"*
- Compatibility caveats *"need re-verifying against KAITO's pinned vLLM
  version"* → verification cost is paid once per preset, not once per user.

### Who decides what

| Who | Controls |
|---|---|
| **KAITO maintainers** (code) | Which method (`mtp` / `dspark` / `ngram` / …), the parameters (`num_speculative_tokens`, `prompt_lookup_max` …), which presets are enabled |
| **User** (annotation) | On / off |

### Escape hatch for power users

The existing `inference_config.yaml` ConfigMap `vllm:` passthrough (see
"Today" section above) is **not going away** — a researcher who wants to
sweep `num_speculative_tokens` or try `eagle` can still write raw
`--speculative-config` themselves. A typed override field on `InferenceSpec`
is called out as **out of scope** for this issue.

---

## 4. Where does the per-preset config live in code?

Two locations. The pattern reuses the existing `catalogOverrides` mechanism
in the KAITO code generator.

### Location 1 — source of truth: `catalogOverrides` map

File: [`presets/workspace/generator/generator.go`](https://github.com/kaito-project/kaito/blob/main/presets/workspace/generator/generator.go)

This map already exists to override fields that HuggingFace `config.json`
gets wrong or omits (e.g. gemma-3's `ModelTokenLimit`, mistral-large-3's
`Architectures`). Adding speculative decoding just extends that pattern.

### Location 2 — generated artifact: `model_catalog.yaml`

File: `presets/workspace/generator/model_catalog.yaml`

Produced by running `go run ./presets/workspace/generator/update_model_catalog`.
This is what the KAITO controller and admission webhook actually read at
runtime.

---

## 5. End-to-end example — enabling MTP for DeepSeek-R1

### Step 1 — extend the type

`presets/workspace/generator/model_catalog.go`:

```go
type SpeculativeDecodingConfig struct {
    Method string        `yaml:"method"`         // "mtp" / "dspark" / "ngram" / ...
    MTP    *MTPConfig    `yaml:"mtp,omitempty"`
    NGram  *NGramConfig  `yaml:"ngram,omitempty"`
    // future: EAGLE *EAGLEConfig
}

type MTPConfig struct {
    NumSpeculativeTokens int `yaml:"numSpeculativeTokens"`
}

type NGramConfig struct {
    NumSpeculativeTokens int `yaml:"numSpeculativeTokens"`
    PromptLookupMax      int `yaml:"promptLookupMax"`
}

type CatalogEntry struct {
    // ... existing fields ...
    SpeculativeDecoding *SpeculativeDecodingConfig `yaml:"speculativeDecoding,omitempty"`
}
```

The typed sub-structs make invalid method/parameter combinations impossible
to author — the issue calls this out explicitly.

### Step 2 — declare per-preset config in `catalogOverrides`

`presets/workspace/generator/generator.go`:

```go
catalogOverrides = map[string]CatalogEntry{
    // ... existing gemma / mistral overrides ...

    "deepseek-ai/deepseek-r1-0528": {
        SpeculativeDecoding: &SpeculativeDecodingConfig{
            Method: "mtp",
            MTP: &MTPConfig{
                NumSpeculativeTokens: 3,
            },
        },
    },
    "deepseek-ai/deepseek-v3-0324": {
        SpeculativeDecoding: &SpeculativeDecodingConfig{
            Method: "mtp",
            MTP: &MTPConfig{
                NumSpeculativeTokens: 3,
            },
        },
    },
}
```

### Step 3 — regenerate the catalog

```
go run ./presets/workspace/generator/update_model_catalog
```

Produces (fragment):

```yaml
models:
  - name: deepseek-r1-0528
    architectures: [DeepseekV3ForCausalLM]
    modelTokenLimit: 163840
    # ...
    speculativeDecoding:
      method: mtp
      mtp:
        numSpeculativeTokens: 3
```

### Step 4 — preset controller reads the field and injects the vLLM flag

Roughly (issue's design step 3):

```go
if ws.Annotations["kaito.sh/enable-speculative-decoding"] == "true" {
    if entry.SpeculativeDecoding != nil {
        blob, _ := json.Marshal(vllmFormat(entry.SpeculativeDecoding))
        vllmArgs = append(vllmArgs, "--speculative-config", string(blob))
    }
}
```

Where `vllmFormat` serializes the typed struct into vLLM's flat JSON, e.g.:

```json
{"method":"mtp","num_speculative_tokens":3}
```

### Step 5 — admission webhook fails fast on unsupported presets

```go
if ws.Annotations["kaito.sh/enable-speculative-decoding"] == "true" {
    entry := catalog.Get(ws.Inference.Preset.Name)
    if entry.SpeculativeDecoding == nil {
        return admission.Denied(fmt.Sprintf(
            "preset %q does not have a validated speculative decoding configuration",
            ws.Inference.Preset.Name,
        ))
    }
}
```

---

## 6. Scope summary

**In scope** (issue #2286):

- Boolean annotation `kaito.sh/enable-speculative-decoding` on Workspace.
- Typed `SpeculativeDecoding` field on `CatalogEntry`, populated per preset
  via `catalogOverrides`.
- Preset controller injects the vLLM `--speculative-config` flag.
- Admission webhook rejects mismatched preset + annotation combinations.
- Initial preset coverage: `mtp` for `deepseek-r1-0528`, `deepseek-v3-0324`
  (checkpoints already ship the MTP head — zero extra memory / download).

**Out of scope** (deliberately deferred):

- EAGLE / Medusa-style separate-draft-model methods (need a
  checkpoint-sourcing design; real ongoing maintenance cost per preset).
- Typed override field on `InferenceSpec` for power users.
- DeepSeek-V4 preset onboarding with `dspark` — lands once that preset
  exists.

---

## 7. Using it with `InferenceSet`

`InferenceSet` fans a preset out across `spec.replicas` child `Workspace`
objects (with optional autoscaling and MIG partitioning). The speculative
decoding toggle works exactly the same way — just put the annotation on
`spec.template.metadata.annotations` and the InferenceSet controller
propagates it to every child `Workspace`.

### How the propagation works (evidence)

In `pkg/utils/inferenceset/inferenceset.go`, `NewWorkspaceForInferenceSet`
literally clones the template annotations onto each child Workspace:

```go
func NewWorkspaceForInferenceSet(iObj *kaitov1beta1.InferenceSet) *kaitov1beta1.Workspace {
    annotations := maps.Clone(iObj.Spec.Template.Annotations)
    // ...
    workspaceObj := &kaitov1beta1.Workspace{
        ObjectMeta: metav1.ObjectMeta{
            Labels:      workspaceLabels,
            Annotations: annotations,
            // ...
        },
        // ...
    }
}
```

So any annotation the preset controller / admission webhook understands
on a standalone `Workspace` also works when set on
`InferenceSet.spec.template.metadata.annotations`. **No InferenceSet-specific
code change is needed** for the speculative decoding toggle — the same
annotation, in the template block, is enough.

### Example — DeepSeek-R1 InferenceSet with speculative decoding on

Start from an existing example
([`kaito_inferenceset_phi_4_mini.yaml`](https://github.com/kaito-project/kaito/blob/main/examples/inference/kaito_inferenceset_phi_4_mini.yaml))
and adapt it to `deepseek-r1-0528` with the annotation on
`spec.template.metadata`:

```yaml
apiVersion: kaito.sh/v1alpha1
kind: InferenceSet
metadata:
  # Scaling annotations belong on the InferenceSet itself.
  annotations:
    scaledobject.kaito.sh/auto-provision: "true"
    scaledobject.kaito.sh/metricName: "vllm:num_requests_waiting"
    scaledobject.kaito.sh/threshold: "10"
  name: deepseek-r1
  namespace: default
spec:
  replicas: 2
  nodeCountLimit: 5
  labelSelector:
    matchLabels:
      apps: deepseek-r1
  template:
    metadata:
      # ← Per-Workspace annotation goes here. Propagated verbatim to every
      #   child Workspace by NewWorkspaceForInferenceSet.
      annotations:
        kaito.sh/enable-speculative-decoding: "true"
    inference:
      preset:
        accessMode: public
        name: deepseek-r1-0528
    resource:
      instanceType: Standard_ND96isr_H100_v5
```

`kubectl apply -f` and the InferenceSet controller creates
`replicas` Workspaces, each with
`kaito.sh/enable-speculative-decoding: "true"` in its own annotation map.
Each child then goes through the exact same preset-controller injection
and admission-webhook validation flow described in sections 2–5.

### Which annotations go where

| Annotation location | Purpose | Reaches child Workspace? |
|---|---|---|
| `InferenceSet.metadata.annotations` | Cluster-level policy on the InferenceSet itself (e.g. `scaledobject.kaito.sh/*` autoscaling, `inferenceset.kaito.io/hash`) | ❌ No — controller-scoped |
| `InferenceSet.spec.template.metadata.annotations` | Per-Workspace behavior (**this is where `kaito.sh/enable-speculative-decoding` goes**) | ✅ Yes — cloned to each child Workspace |

### Rejection semantics for InferenceSet

If the template's preset has no `SpeculativeDecoding` entry in the catalog:

- On `kubectl apply -f <InferenceSet>`, the InferenceSet **itself** may be
  accepted (it validates its own schema), but each child Workspace that
  the controller tries to create is rejected by the Workspace admission
  webhook with the same `preset %q does not have a validated speculative
  decoding configuration` error shown in section 2.
- The rejection surfaces on the InferenceSet's status (create-workspace
  event / condition), so the user still sees a fast, clear failure — just
  at reconciliation time rather than at `apply` time.
- (Optional hardening left as follow-up: teach the InferenceSet admission
  webhook to also validate the annotation against the templated preset,
  so rejection happens at `apply` time too. Not required for correctness.)

### Scaling implication (unchanged)

Speculative decoding is a **per-replica** speedup — MTP verifies within a
single vLLM engine. Turning it on across an InferenceSet's replicas just
means every replica gets the same per-request latency win. It does **not**
share draft state across replicas and does **not** replace autoscaling —
you still want KEDA / auto-provision to grow replicas under high QPS,
because the throughput of speculative decoding degrades toward 1.0× as
QPS climbs. The two features are complementary.

---

## 8. Model coverage — today vs. what could be onboarded next

Cross-referencing the KAITO preset catalog
([`presets/workspace/models/model_catalog.yaml`](https://github.com/kaito-project/kaito/blob/main/presets/workspace/models/model_catalog.yaml))
against vLLM's speculative-decoding docs
([features/speculative_decoding/](https://github.com/vllm-project/vllm/tree/main/docs/features/speculative_decoding))
gives a clear picture of what issue #2286 actually ships versus what could be
layered on later.

### 8.1. Committed by issue #2286 (initial preset coverage)

| KAITO preset | HF ID | Method | `num_speculative_tokens` | Extra memory / download |
|---|---|---|---|---|
| `deepseek-r1-0528` | `deepseek-ai/DeepSeek-R1-0528` | `mtp` | 3 | none — MTP head is in the checkpoint |
| `deepseek-v3-0324` | `deepseek-ai/DeepSeek-V3-0324` | `mtp` | 3 | none — same |

Source: issue #2286 —

> *"deepseek-v3-0324 and deepseek-r1-0528 (existing KAITO presets) already
> support mtp at zero extra memory/download cost."*

Explicitly out of scope for this issue:

- EAGLE / Medusa separate-draft-model methods (need checkpoint sourcing).
- Typed override field on `InferenceSpec` for power users.
- DeepSeek-V4 preset onboarding with `dspark` (lands once that preset exists).

### 8.2. Free-to-onboard next (same `mtp` path, still no extra memory / download)

These presets already exist in the KAITO catalog and the vLLM upstream MTP
docs
([mtp.md](https://github.com/vllm-project/vllm/blob/main/docs/features/speculative_decoding/mtp.md))
confirm the checkpoint ships an MTP path. The maintainer cost is one
re-verification against KAITO's pinned vLLM version, then one entry in
`catalogOverrides`.

| KAITO preset | HF ID | Notes / vLLM evidence |
|---|---|---|
| `deepseek-v3.2` | `deepseek-ai/DeepSeek-V3.2` | DeepSeek-V3 family continuation; same MTP path |
| `gemma-4-E2B-it` | `google/gemma-4-E2B-it` | vLLM MTP doc: *"The E2B, E4B, 12B, 26B-A4B, and 31B Gemma 4 IT assistant checkpoints are supported."* Uses `"method":"mtp"` with a Gemma 4 assistant checkpoint in the `model` field. |
| `gemma-4-E4B-it` | `google/gemma-4-E4B-it` | same |
| `gemma-4-12B-it` | `google/gemma-4-12B-it` | same |
| `gemma-4-26B-A4B-it` | `google/gemma-4-26B-A4B-it` | same |
| `gemma-4-31B-it` | `google/gemma-4-31B-it` | same |

⚠️ Note: the distilled presets
`DeepSeek-R1-Distill-Llama-8B` and `DeepSeek-R1-Distill-Qwen-14B` are
**not** MTP candidates — they are Llama / Qwen architectures with no MTP
head in the checkpoint.

### 8.3. Waiting on preset (`dspark`, DeepSeek-V4 family)

Issue #2286 explicitly parks `dspark` until the DeepSeek-V4 preset lands.
Once it does, the same pattern applies:

| KAITO preset | HF ID | Method |
|---|---|---|
| `deepseek-v4-flash-0731` | `deepseek-ai/DeepSeek-V4-Flash-0731` | `dspark` |
| `deepseek-v4-pro` | `deepseek-ai/DeepSeek-V4-Pro` | `dspark` |

Evidence: DeepSeek DSpark paper (arXiv:2607.05147); vLLM upstream now
documents DSpark as one of the parallel-drafter methods.

### 8.4. Deferred — EAGLE / EAGLE-3 (separate draft checkpoint)

Out of scope for issue #2286 (each target needs a matching, maintained
draft checkpoint plus real extra GPU memory), but the vLLM EAGLE docs
([eagle.md](https://github.com/vllm-project/vllm/blob/main/docs/features/speculative_decoding/eagle.md))
point at two curated draft collections:

- [`RedHatAI/speculator-models`](https://huggingface.co/collections/RedHatAI/speculator-models)
- [`yuhuili/models` (EAGLE)](https://huggingface.co/yuhuili/models?search=eagle)

Mapping to presets already in the KAITO catalog:

| KAITO preset | Candidate EAGLE / EAGLE-3 draft |
|---|---|
| `llama-3.1-8b-instruct` | `RedHatAI/Llama-3.1-8B-Instruct-speculator.eagle3`, `yuhuili/EAGLE-LLaMA3-Instruct-8B` |
| `llama-3.3-70b-instruct` | RedHatAI Llama-3.3-70B EAGLE-3 speculator |
| `qwen3-8b-awq`, `qwen3.5-*`, `qwen3.6-*` | RedHatAI Qwen3-family EAGLE-3 speculators |
| `mistral-7b-instruct-v0.3` | yuhuili EAGLE Mistral series |

### 8.5. Deferred — MLP speculator (IBM accelerators)

Also out of scope for issue #2286 for the same reason (separate draft
checkpoint). vLLM's MLP speculator docs
([mlp.md](https://github.com/vllm-project/vllm/blob/main/docs/features/speculative_decoding/mlp.md))
list IBM's `*-accelerator` checkpoints:

| KAITO preset | Candidate MLP draft |
|---|---|
| `llama-3.1-8b-instruct` | `ibm-ai-platform/llama3-8b-accelerator` |
| `llama-3.3-70b-instruct` | `ibm-ai-platform/llama3-70b-accelerator` — known issue tracked in vLLM [#34106](https://github.com/vllm-project/vllm/issues/34106) / [#34163](https://github.com/vllm-project/vllm/pull/34163) |

⚠️ `granite-4.1-8b` is not directly served by the current IBM accelerator
collection (they cover granite-3b/8b/20b **code** and granite-7b
instruct, not granite-4.1); it would need a fresh accelerator checkpoint
before it can join this row.

### 8.6. `ngram` / `suffix` — universal, but not part of the initial commitment

These methods do not need a draft model at all — they lookup against the
prompt and generation history. In principle any preset in the catalog
could opt in, and typical parameters are
`num_speculative_tokens: 5, prompt_lookup_max: 4`. Issue #2286 does not
define per-preset ngram entries; if the maintainers decide to expose it,
it is a good candidate for a preset-wide default on
code-completion / RAG / agent workloads.

### 8.7. Summary table

| Bucket | Presets | Status |
|---|---|---|
| **Shipping (issue #2286)** | `deepseek-r1-0528`, `deepseek-v3-0324` | `mtp`, `num_speculative_tokens: 3`, in `catalogOverrides` from day one |
| **Free-to-onboard next (same `mtp` path)** | `deepseek-v3.2`, `gemma-4-{E2B,E4B,12B,26B-A4B,31B}-it` | Needs one re-verification + one `catalogOverrides` entry each |
| **Blocked on preset (`dspark`)** | `deepseek-v4-flash-0731`, `deepseek-v4-pro` | Waits until DeepSeek-V4 preset merges |
| **Deferred (EAGLE / MLP draft)** | Llama-3.1/3.3, Qwen3.*, Mistral-7B, etc. | Out of scope for #2286; needs draft-checkpoint sourcing design |
| **Universal opt-in (`ngram` / `suffix`)** | Any preset | Not part of #2286 initial commitment |

---

## 9. TL;DR

- **User**: adds one annotation. Gets ~1.5×–1.7× interactive-latency win on
  supported presets, zero risk on unsupported presets (webhook rejects).
- **Preset maintainer**: adds a few lines to `catalogOverrides` and reruns
  the catalog generator; verification and tuning happen once, in Go review.
- **The per-preset config is not user-tunable by design.** Users who need
  that keep using the existing `inference_config.yaml` ConfigMap
  passthrough.
