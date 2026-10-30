# KubeCon North America 2026 — Speaker Scripts (Slides 2–39)

## Slide 2 — Agenda

We'll follow four questions. Why separate prefill and decode? What makes that difficult to operate? How do KAITO and llm-d divide the work? And how do we decide whether the extra complexity pays off?

## Slide 3 — Prefill: read the prompt, select the first output token

Let's start with what the model actually does. For this teaching example, we're treating each word and punctuation mark as a token. Prefill processes the five prompt positions with causal attention and builds their per-layer keys and values. The final prompt position predicts the first output token, 'Kubernetes.' Importantly, selecting that token doesn't put its keys and values in the cache yet. Those appear when the next step consumes it.

## Slide 4 — Decode: consume one token, select the next, repeat

Now decode consumes 'Kubernetes,' reads the existing history, adds that consumed token's keys and values, and predicts 'helps.' Then it repeats. We're reusing old keys and values, not avoiding all attention work. On the client timeline, time to first token is the initial wait. Inter-token latency is each subsequent gap. Average time per output token summarizes those later intervals; it isn't the same thing as an individual gap or its percentile.

## Slide 5 — One request. Two different performance targets.

These phases create two different performance targets. Prefill often stresses compute and mainly shapes time to first token. Decode often stresses memory bandwidth and shapes the pace of the stream. Neither relationship is exclusive: queues and delivery matter too. What we ultimately want is goodput: requests that meet both latency targets, not just a large aggregate token counter.

## Slide 6 — One shared pool couples two capacity decisions

In aggregated serving, both phases share a GPU pool and scaling boundary. That's a reasonable starting point. But prompt bursts can compete with ongoing generation, and scaling adds both phases together. Even with good scheduling, capacity remains a coupled decision.

## Slide 7 — Long prefills can interrupt token delivery

Here, A is an ongoing request and B is a new arrival. Each D block means a decode execution step for A; D isn't a token or a request name. On the shared GPU, B's prefill can interrupt A. Chunked prefill can reduce that pause. Separate workers remove that direct execution conflict, although B still needs a KV handoff and other latency sources remain.

## Slide 8 — Prefill and decode batch different work

The batching opportunities are different too. Prefill can process many prompt positions together, while respecting causal attention. Ordinary decode advances one newest input position for each independent request. So decode finds parallelism across active sequences. More concurrency can improve aggregate efficiency, but it can also lengthen each iteration and consume more KV memory. The latency budget still matters.

## Slide 9 — Independent pools remove a forced compromise

This is the real motivation: two capacity decisions instead of one compromise. Prompt-heavy demand may need a different replica count or parallelism setting from generation-heavy demand. Those choices remain runtime-dependent. Separation is worthwhile only when the benefit exceeds KV transfer, duplicated model weights, and the extra work of operating two pools.

## Slide 10 — Split the phases. Tune the pools independently.

Here's the resulting shape: prefill and decode pools with a new boundary between them. Data moves from prefill memory to decode memory, even when decode initiates the read. Transfer and coordination must fit the service's latency and cost budgets.

## Slide 11 — P/D fits when the phases need different shapes

Look for phases that want different shapes. Retrieval-heavy prompts create prefill pressure. Long answers and high concurrency keep decode busy with resident state. These are reasons to investigate, not automatic wins. Can independent capacity address a bottleneck we actually observe?

## Slide 12 — Keep aggregated serving when simplicity wins

Sometimes the right answer is to stay aggregated. Small models, short prompts, and low concurrency often don't justify another transfer path and more failure boundaries. If the existing service meets its targets simply and predictably, splitting it because it's fashionable would be a step backward.

## Slide 13 — The hard part is the Kubernetes wiring

The conceptual split is easy. The Kubernetes wiring is where the work expands. Endpoint selection, the decode proxy, transfer settings, labels, ports, and readiness all have to agree. Individually valid manifests can still form a broken service. That's the orchestration gap we're trying to close, rather than inventing another model execution engine.

## Slide 14 — Open-source P/D: several paths, different abstractions

There are already several credible approaches here. Dynamo offers an integrated stack; llm-d provides reusable routing components; KServe, AIBrix, Ray, and the vLLM Production Stack bring different packaging choices. Declarative APIs are not new. Our question is narrower: what's the cleanest way to bring this capability into KAITO's existing operating model?

## Slide 15 — Why llm-d is the best fit for KAITO’s P/D integration

For that goal, llm-d is a good fit. KAITO keeps deployment intent and lifecycle. llm-d contributes endpoint selection and request orchestration. vLLM and NIXL execute the phases and move the state. This is an integration choice, not a universal platform ranking. Today's documented MRI scope is alpha, with vLLM, Istio, and suitable GPU connectivity as important constraints.

## Slide 16 — KAITO turns inference topology into Kubernetes APIs

KAITO's API model grows with the serving problem. Workspace runs a workload, InferenceSet manages serving replicas, InferencePool exposes routing-facing backends, and MultiRoleInference describes the composed topology. These are complementary capabilities, not a strict ownership chain. In particular, InferencePool comes from the Gateway API Inference Extension rather than being a KAITO-specific invention.

## Slide 17 — A continuous API model as serving gets harder

The experience should stay recognizable as the system grows: declare intent, inspect status, and let controllers reconcile. Adding replicas or splitting roles shouldn't replace that mental model. Each resource retains a distinct responsibility while the platform handles more integration work.

## Slide 18 — Clear responsibilities across the stack

Keep these responsibilities separate when debugging. KAITO reconciles resources and lifecycle. The llm-d endpoint picker participates in routing decisions, and its decode-side proxy coordinates the request. The runtime performs inference and transfers KV state. Knowing which layer owns a failure is much more useful than calling everything 'the serving stack.'

## Slide 19 — The stack is composable—not a custom monolith

This composition uses familiar ecosystem pieces instead of hiding them inside a monolith. Gateway APIs expose traffic, llm-d routes, vLLM executes, NIXL connects KV transfer, and KEDA can scale an InferenceSet. KAITO reconciles the declared topology. These components still need compatible versions, and they aren't all installed or owned by one controller.

## Slide 20 — Declare roles once with MultiRoleInference

MultiRoleInference, or MRI, is the central declaration. It describes one logical service with separate prefill and decode InferenceSets. Each role can carry its own capacity and runtime settings. The controller supplies the connecting configuration. Independent replica settings are available here; an automatic service-level scaling policy is a separate topic we'll come to shortly.

## Slide 21 — One API endpoint, a role-aware serving path

Follow a request from the left. The Gateway consults the endpoint picker, then forwards to the selected decode proxy. That proxy invokes prefill and passes the returned transfer metadata to decode. KV data moves between the workers, and the token stream returns through the proxy and Gateway. KAITO reconciles this topology rather than sitting in the request path.

## Slide 22 — From one MRI to a reconciled resource graph

Here's the same service as a resource graph. MRI creates role-specific InferenceSets and a routing pool. InferenceSets reconcile Workspaces and their workloads. Routing configuration connects to the Gateway. We reduce hand-maintained glue while keeping generated resources available for inspection and troubleshooting.

## Slide 23 — A request crosses four distinct boundaries

The sequence highlights an important distinction. Prefill returns metadata identifying remote KV state; decode then obtains the tensors and continues generation. Those are separate operations. The payload arrow shows data direction, not necessarily which side initiates transfer, and doesn't imply timing.

## Slide 24 — Metadata is not the KV payload

Think of this as a control path and a data path. The proxy exchanges HTTP requests and transfer metadata. The runtime moves the much larger KV tensors between memories. If requests route successfully but generation stalls, the data path still deserves investigation. A healthy control exchange doesn't prove that the KV transfer succeeded.

## Slide 25 — The decode pod contains two different roles

Inside the decode pod, the sidecar and vLLM have different jobs and different listeners. External inference traffic needs to reach the routing sidecar; local forwarding reaches the runtime. That sounds small, but a mismatched target port or probe can break the whole path. Use the generated manifests for the installed versions, not remembered example ports.

## Slide 26 — The abstraction removes assembly—not visibility

The abstraction removes assembly, not visibility. Instead of pairing deployments, labels, services, and sidecars by hand, we declare roles and inspect generated objects. Operators still own observability and failure testing. The win is reproducibility and fewer opportunities for configuration drift.

## Slide 27 — Autoscale the role that is actually saturated

Once the roles are separate, scaling should reflect their different pressures. A useful starting signal for prefill is waiting requests. For decode, it's running requests. These are native vLLM gauges, but they need role-scoped interpretation. This is a recommended control pattern, not a claim that MRI automatically supplies these policies today.

## Slide 28 — KEDA autoscales a KAITO InferenceSet

Let’s look at how KAITO integrates with KEDA today. For metric-based scaling, we enable autoscaling on an InferenceSet through annotations. The dedicated KEDA KAITO external scaler uses those annotations to create a ScaledObject automatically.

The scaler reads vLLM metrics directly from the inference pods, so this path does not require a separate Prometheus deployment. KEDA manages an HPA, which updates the InferenceSet’s desired replica count through its scale API. KAITO then reconciles the inference replicas.

The guide’s example uses the average number of waiting requests as the scaling signal, with a target of ten and a maximum of five replicas. That is a queue-pressure signal, not GPU utilization and not request rate.

For predictable traffic, KEDA’s built-in cron trigger is another option. That uses a manually configured ScaledObject and does not need the dedicated KAITO scaler.

The important boundary is that this scales one InferenceSet as a unit. It does not yet give us independent prefill and decode scaling. That is the next step we will look at.

## Slide 29 — Two independent control loops, one logical service

The proposed pattern has two independent loops: prefill load drives prefill capacity, and decode load drives decode capacity. One ScaledObject per target is one implementation. Each loop needs stabilization, warm-up awareness, safe scale-down, and one authoritative replica-count writer.

## Slide 30 — One service, independently managed role capacity

At the service level, we care about both the initial wait and the delivery pace. At the capacity level, we make separate decisions for each role. And we scale a complete serving replica, not an arbitrary tensor-parallel worker. This diagram describes the policy boundary; automatic projection of service intent is still design work.

## Slide 31 — Observe each role. Act on its own capacity.

Routing and scaling solve different problems. Routing chooses among the capacity we have; scaling changes how much model-ready capacity exists. Each role needs correctly scoped metrics and its own decision loop. Count a new replica only when it can serve, and avoid counting the same engine multiple times through different worker series.

## Slide 32 — Two native gauges, two scaling decisions

Here are illustrative thresholds, not production recommendations. Prefill scales up above eight waiting requests and down below one. Decode uses running requests, above twenty-four or below four. Values between or equal to those thresholds hold. Validate per-replica aggregation first: engine queues don't include requests still waiting upstream, and missing data must never quietly become zero load.

## Slide 33 — Different roles need different scaling policies

The policies differ, but their safety contract should match: fresh data, readiness, bounds, stabilization, and protection for in-flight work. The replica ranges are examples. Tune each role against its own workload and objective rather than copying these numbers into production.

## Slide 34 — Safe autoscaling starts with ownership and valid data

The most important safeguards aren't clever formulas. Choose one replica-count writer, make ownership handoff explicit, and verify the real metrics. When data is missing or invalid, the intended behavior is to hold and report the problem. Test that behavior end to end, especially during partial scrape failures, model loading, and scale-down.

## Slide 35 — Derived signals add context to scaling decisions

Derived signals add useful context. Maximum KV occupancy can inform a downscale guard, but it isn't demand or available request capacity. Histogram rates can describe latency tails, and token-counter rates show throughput. Start by observing these signals. Promoting them into control inputs requires tested semantics, correct aggregation, and a reliable query or adapter path.

## Slide 36 — KAITO annotations wire each role to its own scaler

Here's a concrete integration proposal, not a feature enabled by adding annotations today. A new MRI adapter would validate role policies and project allowed annotations onto each child InferenceSet's metadata. The scaler could then create the corresponding ScaledObject. That needs explicit child opt-in and ownership handling; putting annotations in workload templates isn't sufficient.

## Slide 37 — Example: one MRI policy, independent P/D decisions

In this proposed example, prefill and decode carry separate policies. If waiting requests reach twelve while running requests are twelve, prefill requests more capacity and decode holds. Later, decode can scale independently. Null replicas releases MRI's fixed-replica enforcement; it doesn't create an autoscaler. Readiness, cooldown, bounds, and full metric coverage still govern the actual changes.

## Slide 38 — Benchmark the operating point—not only the peak

Now we need to prove that the topology helps. Compare aggregated and disaggregated serving with the same model, traffic, SLO, and stated GPU or cost budget. Record versions, placement, fabric, warm-up, and duration. This is our local evaluation plan, not a results slide. Without those controls, a bigger deployment can masquerade as a better architecture.

## Slide 39 — TTFT: measure the tail under prompt pressure

For first-token latency, look beyond the median. Under matched prompt-heavy load, do the tails improve once transfer overhead is included? These cells are intentionally unmeasured. An honest scorecard is more useful than a percentage borrowed from a different model or system.
