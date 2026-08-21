# vLLM Speculative Decoding Support in KAITO

> Design notes + rollout plan for adding speculative decoding as a
> preset-driven, opt-in capability of KAITO's vLLM runtime.
>
> Tracking issue: [`kaito-project/kaito#2286`](https://github.com/kaito-project/kaito/issues/2286)

## 1. Background

Speculative decoding runs a cheap "drafter" that proposes N tokens per step
and lets the target model verify them in a single forward pass. When the
acceptance rate is high enough (typically >50 %), per-request tokens/sec
goes up 1.5–3× on autoregressive workloads — with **no change to the output
distribution**, because rejected drafts fall back to a normal target-model
sample. It is a per-request inter-token-latency win under memory-bound,
medium-to-low QPS traffic.

Today KAITO users can only reach this by hand-writing a raw
`--speculative-config` JSON blob via the `vllm:` passthrough key in a
custom `inference_config.yaml` ConfigMap. There is no preset-level
guidance on which speculator to pair with which model, and every user
carries the compatibility risk themselves.

**Design goals for this proposal:**

1. Zero-config for the user — just an annotation. No CRD field, no method
   choice, no numeric tuning.
2. Preset-owned method + parameters, so KAITO owns compatibility.
3. Opt-in only — never on by default, because throughput can regress at
   high QPS.
4. Ship first what is already free: DeepSeek MTP.

vLLM's built-in support:

- [Speculative Decoding — vLLM docs](https://docs.vllm.ai/en/latest/features/speculative_decoding/)
- Source: [`vllm-project/vllm/docs/features/speculative_decoding/`](https://github.com/vllm-project/vllm/tree/main/docs/features/speculative_decoding)
- API reference: [`SpeculativeConfig`](https://docs.vllm.ai/en/latest/api/vllm/config/speculative.html)

## 2. vLLM speculative decoding surface

### 2.1 In-scope methods

| Method   | How it drafts                                                                                                              | Extra GPU memory?                          | Preset relevance |
| -------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | ---------------- |
| **mtp**    | Multi-Token-Prediction head **bundled in the model checkpoint** (DeepSeek-V3 / R1 and others)                              | No — head weights already in the target repo | Ship first: `deepseek-v3-0324`, `deepseek-r1-0528` |
| **dspark** | DeepSeek-V4's semi-autoregressive block drafting, also bundled in the checkpoint                                            | No                                         | Lands when the DeepSeek-V4 preset lands |
| **ngram**  | Pure lookup against prompt / generation history — no model                                                                 | No                                         | Cheap fallback for RAG / code / long repetitive prompts |
| **suffix** | Newer prompt-lookup variant, same class as ngram                                                                            | No                                         | Same slot as ngram |

### 2.2 Explicitly out-of-scope (Phase 1)

- **EAGLE / EAGLE-3** and **Medusa** style separate-draft-model methods.
  These are the mainstream general-purpose approach across
  vLLM / SGLang / TensorRT-LLM, and give the largest speed-ups (2–3×) on
  Llama / Qwen. But they need:
  - a **separate draft checkpoint per target model** — real ongoing
    maintenance cost,
  - a **checkpoint-sourcing / distribution design** for enterprise
    clusters with no HuggingFace egress,
  - real extra GPU memory for the draft weights and its verify KV cache.
- **MLPSpeculator** (IBM Granite family) — same class as EAGLE for
  packaging purposes.

Adding EAGLE-class support is tracked as a follow-up issue after
`#2286` lands.

### 2.3 CLI shape

vLLM 0.10 collapsed the older `--speculative-model` /
`--num-speculative-tokens` / … flags into a single JSON blob:

```bash
# MTP — DeepSeek-R1, no extra download, no extra memory
vllm serve deepseek-ai/DeepSeek-R1 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":3}'
```

```bash
# ngram — zero-cost across any preset that opts in
--speculative-config '{"method":"ngram","num_speculative_tokens":5,"prompt_lookup_max":4}'
```

### 2.4 Known limitations that shape the design

- Throughput can regress above QPS ≈ 6–8. → **opt-in only, never
  default**.
- `best_of > 1`, `beam_search` are incompatible with spec decode.
- Chunked prefill + spec decode compatibility varies by vLLM version.
- Multi-LoRA + spec decode has open upstream bugs.
- Pipeline parallelism, prefix caching, tool-calling and `logprobs`
  stability under spec decode need re-verification against the vLLM
  version KAITO pins, rather than assumed fixed.

Because every one of these is preset-and-version specific, the design
below hides the method choice inside the preset, not in the user's CRD.

## 3. Evidence

- **DeepSeek DSpark paper** ([arXiv:2607.05147](https://arxiv.org/abs/2607.05147)):
  60–85 % faster per-user generation vs DeepSeek's own prior MTP
  baseline, in production traffic.
- **vLLM MTP benchmark** ([`vllm-project/vllm#12755`](https://github.com/vllm-project/vllm/pull/12755))
  on DeepSeek-R1: ~1.6–1.7× speed-up at QPS = 1, decaying toward ~1× above
  QPS ≈ 6–8.
- DeepSeek presets already in KAITO (`deepseek-v3-0324`,
  `deepseek-r1-0528`) support `mtp` today at **zero extra memory /
  download cost** — turning the flag on is pure upside for their
  low-QPS use cases.

## 4. Proposed design

### 4.1 User surface — annotation only

```yaml
apiVersion: kaito.sh/v1alpha1
kind: Workspace
metadata:
  name: workspace-deepseek-r1
  annotations:
    kaito.sh/enable-speculative-decoding: "true"
spec:
  inference:
    preset:
      name: deepseek-r1-0528
```

That is the entire user-facing API. No `method`, no
`numSpeculativeTokens`, no `draftModel`, no `draftTensorParallelSize`.

**Rationale:**

- Method choice is preset-specific and vLLM-version-specific. Only KAITO
  can validate the combination.
- The user usually just wants "faster if it is safe on this preset,
  otherwise leave me alone." An annotation is the smallest expression of
  that intent.
- Absence of the annotation is a strict opt-out — new presets that grow
  spec-decode support never silently change behaviour for existing
  Workspaces.

### 4.2 Preset surface — typed, per-model, in `model_catalog.go`

Configuration lives in
`presets/workspace/generator/model_catalog.go` via `catalogOverrides`,
next to the other per-model tuning flags. Shape:

```go
// SpeculativeDecoding, when non-nil, means: this preset is allowed to run
// with the kaito.sh/enable-speculative-decoding annotation, using the
// method + parameters below.
type SpeculativeDecoding struct {
    // exactly one of the following is set
    MTP    *MTPConfig
    DSpark *DSparkConfig
    Ngram  *NgramConfig
    Suffix *SuffixConfig
}

type MTPConfig struct {
    NumSpeculativeTokens int  // vLLM default range
}

type NgramConfig struct {
    NumSpeculativeTokens int
    PromptLookupMax      int
}
// DSparkConfig, SuffixConfig: similarly small, method-specific.
```

Why typed sub-structs rather than a flat mirror of vLLM's config or an
opaque blob:

- Each method has a **different valid parameter set**. A flat struct lets
  reviewers author `NumSpeculativeTokens=3` on `ngram` and forget
  `PromptLookupMax`, or set `PromptLookupMax` on `mtp` where it is
  meaningless. The typed shape makes both bugs unrepresentable.
- Method choice becomes a compile-time exhaustive switch, not a runtime
  string comparison — reviewers can grep for every place that handles
  spec decode and know they saw all of them.

Example override:

```go
"deepseek-r1-0528": {
    SpeculativeDecoding: &SpeculativeDecoding{
        MTP: &MTPConfig{NumSpeculativeTokens: 3},
    },
},
```

### 4.3 Controller behaviour

In the preset controller path that already builds the vLLM launch
command:

1. Read the annotation on the Workspace.
2. If unset → do nothing (default off).
3. If set:
   - Look up the model in the catalog. If it has no `SpeculativeDecoding`
     entry → the admission webhook has already rejected this Workspace
     (see §4.4). Belt-and-suspenders: log and skip.
   - Serialise the method's config to the vLLM `--speculative-config`
     JSON blob and inject it into `VLLMParam.ModelRunParams`, using the
     same single-quoted pattern the runtime already uses for
     `kv-events-config`:
     ```go
     p.VLLM.ModelRunParams["speculative-config"] =
         fmt.Sprintf("'%s'", string(configJSON))
     ```

No changes to `RuntimeContextExtraArguments`, no changes to
`InferenceSpec`, no changes to `pkg/model/interface.go` type surface.

### 4.4 Admission webhook

`api/v1alpha1/workspace_validation.go`:

- Annotation `kaito.sh/enable-speculative-decoding: "true"` on a preset
  whose catalog entry has no `SpeculativeDecoding` → **reject** with an
  explicit "preset does not support speculative decoding yet" message.
- Any value other than `"true"` for the annotation → **reject**. We
  reserve room to add e.g. `"auto"` later, but until then the field is
  strict.
- Reject `EnableLoRA=true` combined with the annotation, until the
  upstream multi-LoRA + spec decode bug closes.

The webhook explicitly does **not** try to validate method-specific
constraints — that lives in the preset catalog.

## 5. Integration map

Confirmed against `kaito-project/kaito` `main`.

### 5.1 Runtime args pipeline (unchanged, reused)

`pkg/model/interface.go` builds the vLLM launch command via
`VLLMParam.ModelRunParams` (a `map[string]string`), serialised by
`utils.BuildCmdStr` (`pkg/utils/common.go`) and wrapped by
`utils.ShellCmd`. JSON-shaped values survive the shell wrap when
single-quoted — the existing `kv-events-config` uses exactly that
pattern:

```go
if _, ok := p.VLLM.ModelRunParams["kv-events-config"]; !ok {
    p.VLLM.ModelRunParams["kv-events-config"] = `'{"enable_kv_cache_events":true}'`
}
```

Speculative decoding reuses this pattern. No new plumbing needed.

### 5.2 Files touched (Phase 1)

- `presets/workspace/generator/model_catalog.go` — new
  `SpeculativeDecoding` struct + method sub-structs; add
  `catalogOverrides` entries for `deepseek-v3-0324`,
  `deepseek-r1-0528`.
- Preset controller (the file that composes `VLLMParam.ModelRunParams`)
  — read annotation, look up catalog entry, inject
  `--speculative-config`.
- `api/v1alpha1/workspace_validation.go` — annotation-vs-catalog cross
  check + LoRA conflict check.
- Unit tests: catalog lookup + JSON blob composition per method, one
  test per method sub-struct.
- E2E: enable annotation on `deepseek-r1-0528` (smallest DeepSeek preset
  we can run in CI), assert pod starts and vLLM logs the speculative
  config.
- Docs: `website/docs/inference/speculative-decoding.md` (mirrors this
  design doc, minus internal implementation detail).

## 6. Rollout plan

### Phase 1 — MTP for DeepSeek presets (scope of `#2286`)

- Land the annotation + catalog + webhook plumbing.
- Enable `mtp` on `deepseek-v3-0324` and `deepseek-r1-0528`.
- No extra checkpoint downloads, no GPU memory tuning, no init-container
  changes.

### Phase 2 — `ngram` / `suffix` for eligible presets

- Enable prompt-lookup drafters on presets where they are safe (RAG,
  code-completion oriented).
- Same annotation, no user-facing change; only the catalog grows.

### Phase 3 — DSpark for DeepSeek-V4

- Lands together with the DeepSeek-V4 preset onboarding.
- Same code path; new `DSparkConfig` catalog entry.

### Phase 4 (separate issue) — EAGLE / EAGLE-3

- Needs a checkpoint-sourcing design (mirror in ACR / Artifactory /
  offline cache), GPU memory reservation in
  `pkg/utils/resources/`, and per-preset EAGLE checkpoint pairings.
- Explicitly out of scope for `#2286`.

## 7. Observability

vLLM already exports the metrics we need; no code change required:

- `vllm:spec_decode_num_accepted_tokens_total`
- `vllm:spec_decode_num_draft_tokens_total`
- `vllm:spec_decode_num_emitted_tokens_total`

Recommended derived signals for the KAITO Grafana dashboard:

- **Acceptance rate** = accepted / draft. < 40 % over a sustained window
  means the method is wrong for the workload; document dropping to
  `ngram` or turning the annotation off.
- **Effective tokens per verifier step** = emitted / verifier_steps. The
  actual speed-up factor as seen by users.

## 8. Traps for future reviewers

1. **Never make this default-on.** Above QPS ≈ 6–8, throughput regresses.
   The annotation is the entire safety mechanism.
2. **Catalog and vLLM version travel together.** If KAITO bumps vLLM,
   revalidate every catalog entry; a method that was safe on the old
   version may break on the new one.
3. **`logprobs` semantics under spec decode are surprising** in some vLLM
   versions (draft-token logprob is not always identical to a non-spec
   run). Call this out on the user-facing docs page.
4. **Chunked prefill + spec decode compatibility varies by vLLM version.**
   If KAITO turns chunked prefill on by default for a preset, revalidate
   before adding that preset to the catalog.
5. **MRI (MultiRoleInference) topology.** Prefill / decode pods run
   separately; spec decode only makes sense on decode pods. The
   annotation should be scoped to decode by default; document how to
   override this in MRI setups.
6. **DeepSeek MTP requires the `mtp`-capable checkpoint variant.** If a
   user overrides `spec.inference.preset.presetOptions.image` to point at
   a checkpoint without the MTP head, the config injection will still
   succeed but vLLM will fail to start. Log an actionable error at
   Workspace-status level from the preset controller when it detects a
   pinned image override + MTP enabled.

## 9. Open questions

- **Do we expose method choice at any tier?** Design says no. Power
  users who want e.g. `ngram` on a preset where the catalog picked
  `mtp` still fall back to the raw `vllm:` passthrough in a custom
  `inference_config.yaml`. Confirm this is acceptable with maintainers.
- **Auto mode?** Should we later accept
  `kaito.sh/enable-speculative-decoding: "auto"` to mean "enable on
  low-QPS, disable on high-QPS by acceptance-rate feedback"? Out of scope
  now, but the strict-`"true"` webhook keeps room for it.
- **Where does an EAGLE draft image live?** Deferred to the follow-up
  issue.

## 10. Next actions

1. This design is upstream as
   [`kaito-project/kaito#2286`](https://github.com/kaito-project/kaito/issues/2286).
   Track review comments there, not here.
2. Once shape is agreed, open the Phase 1 PR: catalog struct + DeepSeek
   MTP entries + webhook + e2e case.
3. Land Phase 2 (`ngram` / `suffix`) as a follow-up PR touching only the
   catalog + tests.
4. File the follow-up EAGLE issue with the checkpoint-sourcing question
   listed as its primary blocker.

## 11. References

### vLLM upstream

- [vLLM — Speculative Decoding (latest)](https://docs.vllm.ai/en/latest/features/speculative_decoding/)
- [vLLM — Speculative Decoding (v0.10.2 snapshot)](https://docs.vllm.ai/en/v0.10.2/features/spec_decode.html)
- [vLLM — `SpeculativeConfig` API](https://docs.vllm.ai/en/latest/api/vllm/config/speculative.html)
- [`vllm-project/vllm` — `docs/features/speculative_decoding/`](https://github.com/vllm-project/vllm/tree/main/docs/features/speculative_decoding)
- [`vllm-project/vllm#12755` — DeepSeek-R1 MTP benchmark](https://github.com/vllm-project/vllm/pull/12755)
- [vLLM blog — How Speculative Decoding Boosts vLLM Performance by up to 2.8×](https://blog.vllm.ai/2024/10/17/spec-decode.html)

### Drafter techniques

- **DeepSeek DSpark** — [paper (arXiv:2607.05147)](https://arxiv.org/abs/2607.05147)
- **EAGLE / EAGLE-3** (deferred) — [paper](https://arxiv.org/abs/2401.15077), [EAGLE-3 paper](https://arxiv.org/abs/2503.01840), [`SafeAILab/EAGLE`](https://github.com/SafeAILab/EAGLE)
- **Medusa** (deferred) — [paper](https://arxiv.org/abs/2401.10774), [`FasterDecoding/Medusa`](https://github.com/FasterDecoding/Medusa)
- **MLPSpeculator** (deferred) — [`foundation-model-stack/fms-extras`](https://github.com/foundation-model-stack/fms-extras)
- **N-gram / prompt lookup** — [`apoorvumang/prompt-lookup-decoding`](https://github.com/apoorvumang/prompt-lookup-decoding)
- Original speculative decoding paper — Leviathan et al., ["Fast Inference from Transformers via Speculative Decoding"](https://arxiv.org/abs/2211.17192) (2022)

### KAITO context

- Tracking issue: [`kaito-project/kaito#2286`](https://github.com/kaito-project/kaito/issues/2286)
- KAITO vLLM runtime entrypoint: [`pkg/model/interface.go` — `buildVLLMInferenceCommand`](https://github.com/kaito-project/kaito/blob/main/pkg/model/interface.go)
- Existing single-quoted JSON blob pattern reused here: `kv-events-config` in the same file.

---

_Author: andyzhang · Last updated: 2026-08-21_
_Aligned with `kaito-project/kaito#2286`._
