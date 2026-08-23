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

## 7. TL;DR

- **User**: adds one annotation. Gets ~1.5×–1.7× interactive-latency win on
  supported presets, zero risk on unsupported presets (webhook rejects).
- **Preset maintainer**: adds a few lines to `catalogOverrides` and reruns
  the catalog generator; verification and tuning happen once, in Go review.
- **The per-preset config is not user-tunable by design.** Users who need
  that keep using the existing `inference_config.yaml` ConfigMap
  passthrough.
