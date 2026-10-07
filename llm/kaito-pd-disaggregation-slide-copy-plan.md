# KAITO + P/D Deck Copy Plan

## Source deck
- `llm/kaito-llm-d/From_Model_Serving_to_Distributed_Inference.pptx`

## Page-level decision table

| Source page | Title / theme | Action | Notes |
|---|---|---|---|
| P10 | Challenges of Real Production Inference | Tweak | Use as production-gap setup slide |
| P12 | Production Distributed Inference Architecture | Tweak | Highlight only KAITO + llm-d + vLLM + NIXL |
| P15 | What is LLM-D? | Tweak | Frame llm-d as routing/scheduling substrate |
| P19 | KV Cache Reuses conversation | Tweak | Keep if you want a KV-reuse explainer |
| P20 | Where Standard Load-Balancing Fails | Tweak | Good lead-in to intelligent routing |
| P21 | Intelligent Inference Scheduling | Tweak | Keep core message, refresh numbers if needed |
| P34 | Why P/D? Prefill and Decode Two Phases | Direct copy | Strong foundational P/D slide |
| P35 | Why P/D? Prefill and Decode Scale Differently | Direct copy | Strong foundational P/D slide |
| P37 | Efficient KV Transfer in vLLM via NIXL | Direct copy (optional) | Keep only if there is time for KV transfer details |
| P38 | Aggregated vs Disaggregated Pareto Frontier | Direct copy | Best payoff slide for P/D story |
| P41 | What is KAITO? | Direct copy | Best transition into KAITO story |
| P42 | Workload Lifecycle | Direct copy | Shows model-to-service automation well |
| P43 | How the GPU Node Count Is Computed | Direct copy | Useful proof of model-aware automation |
| P44 | Autoscaling: keda-kaito-scaler | Direct copy | Good base autoscaling slide |
| P45 | Autoscaling: Composite Metrics | Tweak | Rewrite around per-role scaling policy |
| P47 | Production-Stack | Tweak | Keep only if audience cares about production integration |
| P48 | GPU Node Mocker | Tweak | Strong infra/testing slide |
| P49 | Testing=Confidence | Tweak | Compress with P48 if deck is long |

## New slides to write

1. Why KAITO on top of llm-d / Dynamo / manual stack
2. What is MultiRoleInference?
3. What one MRI CR generates
4. Request flow: Gateway → EPP → Decode → Prefill → KV transfer
5. decode-only sidecar / port / label / env contracts
6. benchmark / break-even analysis
7. AKS / production lessons learned

## Suggested final slide order

1. Title *(new)*
2. Production problem *(P10 tweak)*
3. Stack placement *(P12 tweak)*
4. What is KAITO *(P41)*
5. Why KAITO on top of llm-d / Dynamo / manual stack *(new)*
6. Why P/D: two phases *(P34)*
7. Why P/D: scale differently *(P35)*
8. Aggregated vs disaggregated *(P38)*
9. KV reuse + why routing matters *(P19/P20/P21 tweak or merge)*
10. What is llm-d here *(P15 tweak)*
11. MultiRoleInference CRD *(new)*
12. What one MRI CR generates *(new)*
13. Request flow *(new)*
14. Sidecar / port / label / env contracts *(new)*
15. NIXL KV transfer *(P37 optional)*
16. Independent autoscaling *(P44 + P45 tweak)*
17. Production integration + testing *(P47/P48/P49 tweak)*
18. Benchmark / break-even *(new)*
19. AKS lessons learned *(new)*
20. Summary / Q&A *(new)*
