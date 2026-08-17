# vLLM Speculative Decoding Support in KAITO

> Design doc + rollout plan for adding speculative decoding as a first-class
> capability of KAITO's vLLM runtime.

## 1. Background

Speculative decoding runs a cheap "drafter" that proposes N tokens per step,
and lets the target model verify them in a single forward pass. When the
acceptance rate is high enough (typically >50%), end-to-end tokens/sec goes
up 1.5–3× on autoregressive workloads.

vLLM has had speculative decoding built in since 0.7 and it stabilised
significantly through 0.10. KAITO's vLLM runtime already exposes almost
everything vLLM supports, but there is currently no first-class knob for
speculative decoding — users have to reach into
`--kaito-config-file` overrides to enable it, and there is no
preset-level guidance on which speculator to pair with which model.

## 2. vLLM speculative decoding surface

### 2.1 Supported methods (as of vLLM 0.10)

| Method | Drafter | Extra weights | Notes |
| --- | --- | --- | --- |
| **N-gram** | Prompt-lookup n-gram | none | Best for RAG / code completion / long repetitive prompts. Zero GPU cost. |
| **Draft model** | Small target-family LLM | Draft weights (e.g. `Llama-3.2-1B` for `Llama-3.1-70B`) | General purpose. Needs a family match. |
| **EAGLE / EAGLE-3** | Head that consumes target hidden state | EAGLE head weights | SOTA acceptance rate, well-supported on Llama/Qwen. |
| **MLPSpeculator** (IBM) | MLP head | Trained head weights | Niche; used by IBM Granite family. |
| **Medusa** | Multi-head prediction | Medusa heads | Legacy, being displaced by EAGLE. |

### 2.2 CLI shape

vLLM 0.10 collapsed the older `--speculative-model / --num-speculative-tokens / ...`
flags into a single JSON blob:

```bash
vllm serve meta-llama/Llama-3.1-70B-Instruct \
  --speculative-config '{
    "method": "eagle3",
    "model": "yuhuili/EAGLE3-LLaMA3.1-Instruct-70B",
    "num_speculative_tokens": 5,
    "draft_tensor_parallel_size": 1
  }'
```

N-gram (no model download, cheapest to enable):

```bash
--speculative-config '{"method":"ngram","num_speculative_tokens":5,"prompt_lookup_max":4}'
```

### 2.3 Known limitations that shape our design

- `best_of > 1`, `beam_search` incompatible with spec decode.
- Chunked prefill + spec decode only stable in recent vLLM releases; needs
  a compatibility matrix per preset.
- Multi-LoRA + spec decode has open bugs; recommend disabling one of the two.
- `draft_tensor_parallel_size` almost always 1 (draft models are small).
- Memory overhead: draft weights + verify KV cache typically eat 5–15 % of
  available GPU memory. Affects `max_model_len` / `max_num_seqs` autotuning.

## 3. KAITO integration map

The concrete integration points below were confirmed by reading
`kaito-project/kaito` `main` at commit `ff469ac`.

### 3.1 Runtime args pipeline (the good news)

`pkg/model/interface.go` builds the vLLM launch command entirely through a
`map[string]string` in `VLLMParam.ModelRunParams`. That map is fed to
`utils.BuildCmdStr` (`pkg/utils/common.go:88`) which emits `--key=value`
tokens, wrapped by `utils.ShellCmd` into `/bin/sh -c ...`.

```go
// pkg/utils/common.go:88
func BuildCmdStr(baseCommand string, runParams ...map[string]string) string {
    for _, runParam := range runParams {
        for key, value := range runParam {
            if value == "" {
                updatedBaseCommand = fmt.Sprintf("%s --%s", updatedBaseCommand, key)
            } else {
                updatedBaseCommand = fmt.Sprintf("%s --%s=%s", updatedBaseCommand, key, value)
            }
        }
    }
    return updatedBaseCommand
}
```

**Consequence:** adding a new vLLM flag is one map insert. JSON-shaped
values (like `--speculative-config`) survive the shell wrap when
single-quoted — same pattern as the existing `kv-events-config`:

```go
// pkg/model/interface.go:414
if _, ok := p.VLLM.ModelRunParams["kv-events-config"]; !ok {
    p.VLLM.ModelRunParams["kv-events-config"] = `'{"enable_kv_cache_events":true}'`
}
```

We reuse the exact same pattern for speculative decoding.

### 3.2 Where to insert the code

The vLLM branch in `buildVLLMInferenceCommand` lives roughly at
`pkg/model/interface.go:388–502`. The right insertion point is right after
the `fuse_allreduce_rms` block and before parallelism resolution (around
line 425), grouped with the other "operator-injected defaults, user may
override" flags.

Terminal serialisation happens once at the end:

```go
// pkg/model/interface.go:500-501
modelCommand := utils.BuildCmdStr(p.VLLM.BaseCommand, p.VLLM.ModelRunParams)
return utils.ShellCmd(modelCommand)
```

We do not touch the shell command, container spec, or args slice.

### 3.3 Types

Two changes required.

**a) `pkg/model/interface.go` — `RuntimeContextExtraArguments`** (line 328):

```go
type RuntimeContextExtraArguments struct {
    // ... existing fields (StreamingModelPath, LocalModelWeightsPath, ...) ...

    // SpeculativeDecoding, when non-nil, causes buildVLLMInferenceCommand
    // to inject --speculative-config as a JSON blob. Nil means disabled.
    SpeculativeDecoding *SpeculativeConfig
}

// SpeculativeConfig is the runtime-shape of vLLM's --speculative-config.
// Kept in pkg/model (not api/v1alpha1) to avoid the import cycle the file
// header already warns about at line 388.
type SpeculativeConfig struct {
    Method                  string  // "ngram" | "draft" | "eagle" | "eagle3" | "medusa" | "mlp_speculator"
    NumSpeculativeTokens    int
    Model                   string  // draft model repo/path; empty for ngram
    DraftTensorParallelSize *int
    NgramPromptLookupMax    *int
}
```

**b) `pkg/model/interface.go` — `VLLMParam`** (line 249) gets preset-level
capability flags mirroring the existing `DisallowLoRA`:

```go
type VLLMParam struct {
    // ... existing fields ...

    DisallowLoRA        bool
    DisallowSpeculative bool                // preset opts out entirely
    DefaultSpeculators  []DefaultSpeculator // preset's recommended draft configs
}

type DefaultSpeculator struct {
    Method            string
    Model             string
    RecommendedTokens int
}
```

`DefaultSpeculators` lets a preset (e.g. `llama-3.1-70b-instruct`) declare
"when the user turns on `method: eagle3` without specifying `draftModel`,
use this repo by default."

### 3.4 CRD field

`api/v1alpha1/workspace_types.go` — extend `InferenceSpec` (not
`RuntimeSpec` — spec decode is inference-only, not tuning):

```go
type SpeculativeDecodingSpec struct {
    // Method is the speculator backend.
    // +kubebuilder:validation:Enum=ngram;draft;eagle;eagle3;medusa;mlp_speculator
    Method string `json:"method"`

    // NumSpeculativeTokens is the number of tokens drafted per step.
    // Typical sweet spot: 3-7. >10 usually hurts (verify cost > gain).
    // +kubebuilder:default=5
    // +kubebuilder:validation:Minimum=1
    // +kubebuilder:validation:Maximum=10
    NumSpeculativeTokens int32 `json:"numSpeculativeTokens,omitempty"`

    // DraftModel is the HuggingFace repo (or local path) of the draft
    // model. Required for method != ngram. Empty for ngram.
    // If empty and method != ngram, the preset's DefaultSpeculators[0]
    // matching the method is used.
    // +optional
    DraftModel string `json:"draftModel,omitempty"`

    // DraftTensorParallelSize overrides TP for the draft model.
    // Defaults to 1. Only meaningful for method in {draft, eagle, eagle3}.
    // +optional
    DraftTensorParallelSize *int32 `json:"draftTensorParallelSize,omitempty"`

    // NgramPromptLookupMax: max n-gram length looked up in the prompt.
    // Only for method=ngram. Defaults to 4.
    // +optional
    NgramPromptLookupMax *int32 `json:"ngramPromptLookupMax,omitempty"`
}
```

Attach it to `InferenceSpec`:

```go
type InferenceSpec struct {
    // ... existing fields ...
    // +optional
    SpeculativeDecoding *SpeculativeDecodingSpec `json:"speculativeDecoding,omitempty"`
}
```

### 3.5 Validation webhook

`api/v1alpha1/workspace_validation.go`:

- `method == "ngram"` → reject non-empty `DraftModel`,
  `DraftTensorParallelSize`.
- `method != "ngram"` → require non-empty `DraftModel` **or** the preset
  advertising a `DefaultSpeculators` entry for that method.
- `NumSpeculativeTokens` in `[1, 10]`.
- Reject if the target preset sets `VLLMParam.DisallowSpeculative = true`.
- Reject combination with `EnableLoRA=true` (until vLLM bug closes).

## 4. Integration code sketch (Phase 1, n-gram only)

Full diff-shape of the insertion point (`pkg/model/interface.go`, right
after the `fuse_allreduce_rms` line):

```go
// Speculative decoding: serialised as a single --speculative-config JSON
// blob. vLLM dispatches to the right speculator backend internally.
// Single-quoted so the JSON survives the shell wrap in ShellCmd, matching
// the pattern used for kv-events-config above. User overrides via
// kaito-config-file win because that flag is applied after argparse.
if rc.SpeculativeDecoding != nil && !p.VLLM.DisallowSpeculative {
    if _, ok := p.VLLM.ModelRunParams["speculative-config"]; !ok {
        cfg := map[string]any{
            "method":                 rc.SpeculativeDecoding.Method,
            "num_speculative_tokens": rc.SpeculativeDecoding.NumSpeculativeTokens,
        }
        if rc.SpeculativeDecoding.Model != "" {
            cfg["model"] = rc.SpeculativeDecoding.Model
        }
        if rc.SpeculativeDecoding.DraftTensorParallelSize != nil {
            cfg["draft_tensor_parallel_size"] = *rc.SpeculativeDecoding.DraftTensorParallelSize
        }
        if rc.SpeculativeDecoding.NgramPromptLookupMax != nil {
            cfg["prompt_lookup_max"] = *rc.SpeculativeDecoding.NgramPromptLookupMax
        }
        if b, err := json.Marshal(cfg); err == nil {
            p.VLLM.ModelRunParams["speculative-config"] =
                fmt.Sprintf("'%s'", string(b))
        }
    }
}
```

Upstream translation lives in
`pkg/workspace/inference/preset_inferences.go`, where the controller
already builds `RuntimeContext`. One `if ws.Inference.SpeculativeDecoding != nil`
block populates `rc.SpeculativeDecoding` from the CRD field, applying
preset defaults for `DraftModel` when the user omitted it.

## 5. Rollout plan

### Phase 1 — N-gram only (target: 2–3 days)

- Zero draft-weight distribution problem.
- Zero resource-calc adjustment.
- Zero preset compatibility problem (any vLLM preset works unless
  explicitly opted out).
- Files touched (~200 LoC + tests):
  - `api/v1alpha1/workspace_types.go` (+ `zz_generated.deepcopy.go`)
  - `api/v1alpha1/workspace_validation.go`
  - `pkg/model/interface.go`
  - `pkg/workspace/inference/preset_inferences.go`
  - `pkg/model/interface_test.go` — new `TestGetInferenceCommandVLLMSpeculativeNgram*`
  - `test/e2e/preset_vllm_test.go` — one e2e case exercising n-gram on Llama-3.1-8B
- Docs: `website/docs/inference/speculative-decoding.md`.

### Phase 2 — Draft model (external HF repo)

- Extend init container to download `spec.speculativeDecoding.draftModel`
  from HuggingFace into `/workspace/draft-model`.
- Wire `pkg/utils/resources/` GPU memory calc to reserve draft-model
  headroom (5–15 % depending on draft size / verify KV cache).
- E2E: pair `Llama-3.1-70B` (target) with `Llama-3.2-1B-Instruct` (draft).

### Phase 3 — EAGLE / EAGLE-3 + preset registry

- Each `presets/workspace/models/*/model.go` declares `DefaultSpeculators`
  with tested EAGLE / draft pairings.
- Preset docs list "recommended speculator" alongside "recommended
  performance mode".
- Grafana dashboard: expose vLLM `spec_decode_num_accepted_tokens_total /
  num_draft_tokens_total` as an "acceptance rate" panel. Warn <40 %.

### Phase 4 — Advanced

- MoE + spec decode compatibility validation (Mixtral 8x22B family).
- Chunked prefill + spec decode compatibility matrix per preset.
- Autotune `num_speculative_tokens` using vLLM 0.10+ dynamic mode when
  it stabilises.
- Multi-LoRA + spec decode once the upstream vLLM bug is fixed.

## 6. Observability

vLLM already exports Prometheus metrics; no code change required:

- `vllm:spec_decode_num_accepted_tokens_total`
- `vllm:spec_decode_num_draft_tokens_total`
- `vllm:spec_decode_num_emitted_tokens_total`

Recommended derived signals:

- **Acceptance rate** = accepted / draft. <40 % usually means the method
  is wrong for the workload; consider dropping to `ngram` or turning off.
- **Effective tokens per verifier step** = emitted / verifier_steps. This
  is the actual speed-up factor.

## 7. Traps for future PR reviewers

1. **Not every model has an EAGLE checkpoint.** KAITO's Phi, Falcon,
   Mistral presets vary. Presets must set `DisallowSpeculative=true` or
   omit `DefaultSpeculators` where unsupported.
2. **`num_speculative_tokens` too high hurts.** After ~7 tokens, acceptance
   drops fast and verify cost dominates. Docs should call this out.
3. **Vocab / version drift** between target and draft crashes on startup.
   Validation should reject known-bad pairings when possible; otherwise
   emit a controller event on first reconcile failure.
4. **`logprobs` semantics under spec decode** are surprising in some vLLM
   versions (draft-token logprob is not always identical to a non-spec
   run). Document this in the user-facing page.
5. **Chunked prefill compatibility** varies by vLLM version. If KAITO
   turns chunked prefill on by default for a preset, ensure the preset's
   `DisallowSpeculative` reflects reality on that version.
6. **MRI (MultiRoleInference) topology.** Prefill / decode pods run
   separately; spec decode only makes sense on decode pods. The CRD field
   applies to decode by default; document how to scope it in MRI.

## 8. Open questions

- **Where does the field live?** `InferenceSpec.SpeculativeDecoding`
  (this doc's choice) versus `RuntimeSpec.Speculative`. Ask maintainers.
- **Default `NumSpeculativeTokens`.** vLLM has no strong default; empirical
  ~5 works across most Llama-family models. Confirm with benchmarks.
- **Preset default speculators** — do we ship a curated list per preset,
  or leave selection entirely to the user? Curated is friendlier but
  ties KAITO releases to third-party EAGLE checkpoint availability.
- **Draft model image packaging.** For enterprise clusters with no
  outbound to HuggingFace, do we ship a `-with-eagle3` image tag per
  preset, or rely on ACR/Artifactory mirror configured via
  `#2218`-style overrides?

## 9. Next actions

1. File an upstream issue on `kaito-project/kaito` proposing this design,
   linking this doc.
2. Once field-name / placement is agreed, open Phase 1 PR (n-gram only)
   with the code sketch in §4.
3. Follow up with Phase 2 (draft model) once init-container + resource
   calc changes are scoped.

---

_Author: andyzhang · Last updated: 2026-08-17_
_Source of truth for KAITO code references: `kaito-project/kaito@ff469ac` (main branch, 2026-07-01)._
