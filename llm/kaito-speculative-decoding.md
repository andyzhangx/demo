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

| KAITO preset | HF ID | In KAITO catalog? | Method | `num_speculative_tokens` | Extra memory / download |
|---|---|---|---|---|---|
| `deepseek-r1-0528` | `deepseek-ai/DeepSeek-R1-0528` | ✅ Yes | `mtp` | 3 | none — MTP head is in the checkpoint |
| `deepseek-v3-0324` | `deepseek-ai/DeepSeek-V3-0324` | ✅ Yes | `mtp` | 3 | none — same |

Source: issue #2286 —

> *"deepseek-v3-0324 and deepseek-r1-0528 (existing KAITO presets) already
> support mtp at zero extra memory/download cost."*

Explicitly out of scope for this issue:

- EAGLE / Medusa separate-draft-model methods (need checkpoint sourcing).
- Typed override field on `InferenceSpec` for power users.

### 8.2. Free-to-onboard next (same `mtp` path, still no extra memory / download)

These presets already exist in the KAITO catalog and the vLLM upstream MTP
docs
([mtp.md](https://github.com/vllm-project/vllm/blob/main/docs/features/speculative_decoding/mtp.md))
confirm the checkpoint ships an MTP path. The maintainer cost is one
re-verification against KAITO's pinned vLLM version, then one entry in
`catalogOverrides`.

| KAITO preset | HF ID | In KAITO catalog? | Notes / vLLM evidence |
|---|---|---|---|
| `deepseek-v3.2` | `deepseek-ai/DeepSeek-V3.2` | ✅ Yes | DeepSeek-V3 family continuation; same MTP path |
| `gemma-4-E2B-it` | `google/gemma-4-E2B-it` | ✅ Yes | vLLM MTP doc: *"The E2B, E4B, 12B, 26B-A4B, and 31B Gemma 4 IT assistant checkpoints are supported."* Uses `"method":"mtp"` with a Gemma 4 assistant checkpoint in the `model` field. |
| `gemma-4-E4B-it` | `google/gemma-4-E4B-it` | ✅ Yes | same |
| `gemma-4-12B-it` | `google/gemma-4-12B-it` | ✅ Yes | same |
| `gemma-4-26B-A4B-it` | `google/gemma-4-26B-A4B-it` | ✅ Yes | same |
| `gemma-4-31B-it` | `google/gemma-4-31B-it` | ✅ Yes | same |

⚠️ Note: the distilled presets
`DeepSeek-R1-Distill-Llama-8B` and `DeepSeek-R1-Distill-Qwen-14B` are
**not** MTP candidates — they are Llama / Qwen architectures with no MTP
head in the checkpoint.

### 8.3. Ready to onboard (`dspark`, DeepSeek-V4 family) — presets now in catalog

Issue #2286 originally parked `dspark` until the DeepSeek-V4 preset landed.
**As of August 2026, both DeepSeek-V4 presets are now in the KAITO model
catalog** (architecture `DeepseekV4ForCausalLM`), so `dspark` onboarding is
no longer blocked on preset availability — it just needs the same
re-verification + `catalogOverrides` entry as section 8.2.

| KAITO preset | HF ID | In KAITO catalog? | Method |
|---|---|---|---|
| `deepseek-v4-flash-0731` | `deepseek-ai/DeepSeek-V4-Flash-0731` | ✅ Yes | `dspark` |
| `deepseek-v4-pro` | `deepseek-ai/DeepSeek-V4-Pro` | ✅ Yes | `dspark` |

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
| **Ready to onboard (`dspark`)** | `deepseek-v4-flash-0731`, `deepseek-v4-pro` | Presets now in KAITO catalog; needs re-verification + `catalogOverrides` entry |
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

---

## 10. Runtime finding — `MiMo-7B-Base` can crash with `mtp` + `runai_streamer`

On 2026-09-15 I checked a live KAITO Workspace (`default/xiaomi`) whose pod
`xiaomi-0` was stuck in `CrashLoopBackOff`. This turned out to be a useful
real-world correction to the mostly code-level discussion above:

> **The flags do not conflict syntactically, but `MiMo-7B-Base` running with
> both speculative decoding (`mtp`) and model streaming (`runai_streamer`)
> crashed at runtime during engine initialization.**

### Workspace / pod configuration observed

The Workspace had speculative decoding explicitly enabled:

```yaml
metadata:
  annotations:
    kaito.sh/enable-speculative-decoding: "true"
```

And the pod command confirmed that KAITO enabled both features at once:

```bash
python3 /workspace/vllm/inference_api.py \
  --load-format=runai_streamer \
  --model=az://.../XiaomiMiMo/MiMo-7B-Base \
  --speculative-config='{"method":"mtp","num_speculative_tokens":1}'
```

So this was not a theory exercise — the failing pod really was launched with
**streaming + MTP together**.

### What succeeded

The main model weights were streamed successfully by Run:ai Model Streamer:

```text
Loading safetensors using Runai Model Streamer: 100% Completed | 451/451
[RunAI Streamer] Overall time to stream 14.6 GiB of all files to cpu: 8.26s
```

That rules out the most obvious classes of failure:

- not a blob download/auth problem for the main model,
- not a generic `runai_streamer` startup failure,
- not a simple "weights never arrived" issue.

### Where it failed

vLLM then resolved both the base model and the MTP model path:

```text
Resolved architecture: MiMoForCausalLM
Resolved architecture: MiMoMTPModel
```

The engine config in logs also showed that speculative decoding was wired to
use the streamed local cache path:

```text
speculative_config=SpeculativeConfig(
  method='mtp',
  model='/root/.cache/vllm/assets/model_streamer/bc8a14aa',
  num_spec_tokens=1)
load_format=runai_streamer
```

The actual crash happened while vLLM was loading the MTP speculator:

```text
self.speculator.load_model(self.model)
...
runai_streamer_loader.py
RuntimeError: Cannot find any safetensors model weights with '/root/.cache/vllm/assets/model_streamer/bc8a14aa'
```

For reference, here is the most useful error sequence from the live pod logs:

```text
INFO 09-15 06:51:20 inference_api.py:557] Starting server on port 5000
INFO 09-15 06:51:40 [model.py:619] Resolved architecture: MiMoForCausalLM
INFO 09-15 06:51:52 [model.py:619] Resolved architecture: MiMoMTPModel
(EngineCore pid=301) INFO 09-15 06:52:05 [core.py:114] Initializing a V1 LLM engine (v0.25.1) with config: model='/root/.cache/vllm/assets/model_streamer/bc8a14aa', speculative_config=SpeculativeConfig(method='mtp', model='/root/.cache/vllm/assets/model_streamer/bc8a14aa', num_spec_tokens=1), load_format=runai_streamer
(EngineCore pid=301) Loading safetensors using Runai Model Streamer: 100% Completed | 451/451
(EngineCore pid=301) INFO 09-15 06:52:18 file_streamer.py:69] [RunAI Streamer] Overall time to stream 14.6 GiB of all files to cpu: 8.26s, 1.8 GiB/s
(EngineCore pid=301) RuntimeError: Cannot find any safetensors model weights with '/root/.cache/vllm/assets/model_streamer/bc8a14aa'
(APIServer pid=45) RuntimeError: Engine core initialization failed. See root cause above. Failed core proc(s): {}
```

The outer API server then died with the usual wrapper error:

```text
RuntimeError: Engine core initialization failed. See root cause above.
```

### Conclusion

For this concrete runtime combination:

- model: `XiaomiMiMo/MiMo-7B-Base`
- speculative decoding: `mtp`
- model loading: `runai_streamer`

**there is a real runtime incompatibility today.**

More precisely:

- **code/config layer**: KAITO successfully injects both flags and they do not
  overwrite each other;
- **runtime layer**: vLLM's MTP/speculator loading path fails when pointed at
  the streamed local cache directory produced by `runai_streamer` for this
  model.

### Best current mitigation

If the immediate goal is to get the Workspace healthy, the safest workaround is:

1. **Disable speculative decoding** for this Workspace
   (`kaito.sh/enable-speculative-decoding: "false"` or remove the annotation)
2. Keep model streaming enabled

Why this is the best first move:

- the streamer clearly succeeded,
- the crash happened later in the MTP/speculator path,
- disabling MTP isolates the failure without giving up the streaming benefit.

### Recommended follow-up experiments

To tighten the RCA, run these two A/B checks:

1. **Streaming on, MTP off**
   - expected: pod should start successfully
2. **Streaming off, MTP on**
   - determines whether the problem is specific to the `runai_streamer + mtp`
     combination, versus a broader MiMo MTP issue

### Practical takeaway for KAITO docs / rollout

The earlier statement "`mtp` and `runai_streamer` do not conflict" is only true
at the **flag wiring** level. It is **not** sufficient as an operational claim.
For at least `MiMo-7B-Base`, KAITO should document that:

- `runai_streamer` can successfully load the base model,
- but enabling `mtp` on top may still fail during vLLM engine startup,
- so model-by-model runtime validation is required before claiming the
  combination is supported.

### Follow-up benchmark on the same cluster: MTP still helps once `runai_streamer` is removed

After confirming the crash was specific to the `mtp + runai_streamer`
combination, I ran an A/B benchmark on the **same live cluster** after
patching the `xiaomi` StatefulSet to:

- **disable `runai_streamer`**
- keep the model as `XiaomiMiMo/MiMo-7B-Base`
- keep **speculative decoding MTP enabled** via:

```bash
--speculative-config='{"method":"mtp","num_speculative_tokens":1}'
```

This matters because it separates two questions:

1. does `runai_streamer` conflict with MiMo MTP? (**yes, in this case**)
2. does MiMo MTP itself still help when loaded normally from Hugging Face?
   (**also yes, based on the measurements below**)

### Benchmark setup

#### Test environment

- Cluster: `andy-aks135`
- Namespace / workload: `default/xiaomi`
- Workload shape: **1 StatefulSet replica** (`xiaomi-0`)
- Model: `XiaomiMiMo/MiMo-7B-Base`
- Runtime: vLLM `0.25.1`
- GPU SKU from the Workspace: `Standard_NC24ads_A100_v4`
- Parallelism: single-pod / single-rank path (`tensor-parallel-size=1`)
- Model loading path during the benchmark: **direct HF model path**
  (`--model=XiaomiMiMo/MiMo-7B-Base`), **not** `runai_streamer`

#### Test procedure

1. Start from the patched `xiaomi` StatefulSet with:
   - `runai_streamer` removed
   - `--speculative-config='{"method":"mtp","num_speculative_tokens":1}'`
2. Port-forward the serving endpoint locally.
3. Run a warmup request.
4. Run **6 fixed prompts** sequentially against the OpenAI-compatible
   `/v1/chat/completions` endpoint with:
   - `temperature=0`
   - `max_tokens=256`
5. Record per-request latency and token usage returned by the API.
6. Patch the same StatefulSet again to **remove** `--speculative-config`.
7. Wait for the replacement pod to become `Ready`.
8. Run the **same warmup + same 6 prompts** again.
9. Restore `--speculative-config` and confirm the pod becomes `Ready` again.
10. Run one more confirmation pass after restore.

#### Test scale / workload size

The benchmark was intentionally **small-scale and latency-oriented**, not a
full throughput sweep:

- **1 pod**
- **1 GPU-backed serving replica**
- **6 measured requests** per condition
- **256 completion tokens per request** (all six requests hit the length cap)
- roughly **48 prompt tokens on average** per request
- one warmup request before each measured run

This is a reasonable shape for validating **interactive request latency** and
steady per-request completion speed, but it is **not** enough to claim a full
cluster-wide QPS curve.

### Measured results

#### Speculative decoding ON (steady state, before turning it off)

- average latency: **1.71s**
- p50 latency: **1.74s**
- max latency: **1.77s**
- aggregate completion throughput: **150.0 tokens/s**

#### Speculative decoding OFF

- average latency: **2.78s**
- p50 latency: **2.78s**
- max latency: **2.80s**
- aggregate completion throughput: **92.0 tokens/s**

#### Speculative decoding ON again (after restore)

The first post-restore warmup path was cold and noticeably slower, so the
cleanest comparison is the restored **steady-state** run excluding the first
measured request after the pod restart:

- average latency: **1.75s**
- p50 latency: **1.76s**
- max latency: **1.77s**
- aggregate completion throughput: **146.4 tokens/s**

### Performance delta

Using the initial steady-state `speculative on` run versus the `speculative
off` run:

- **average latency improved by ~38.7%**
- **aggregate completion throughput improved by ~63.1%**

Using the restored steady-state `speculative on` run versus the `speculative
off` run:

- **average latency improved by ~37.2%**
- **aggregate completion throughput improved by ~59.2%**

So the practical result on this cluster is:

> **MiMo MTP is beneficial once `runai_streamer` is removed.**
> The failure was not "MTP is bad"; the failure was the specific
> `runai_streamer + mtp` runtime combination.

### Operational takeaway from the A/B test

For `XiaomiMiMo/MiMo-7B-Base`, the evidence now supports a more precise claim:

- `mtp + runai_streamer` can fail at startup
- `mtp` **without** `runai_streamer` can start successfully
- and in this single-replica interactive benchmark, `mtp` delivered roughly
  **37–39% lower latency** and **59–63% higher completion throughput**

That is strong enough to justify a model-specific workaround such as:

- disable `runai_streamer` for MiMo MTP workloads, or
- block the unsupported `runai_streamer + mtp` combination until the runtime
  issue is fixed upstream or in KAITO

while still keeping speculative decoding enabled where it demonstrably helps.
