# Speaker Scripts — Slides 2–33

## Slide 2 — Prefill here, decode there Kubernetes-native LLM inference with KAITO and llm-d

OK, let's start now, this session is “Prefill here, decode there<strong>,</strong> Kubernetes-native LLM inference with KAITO and llm-d”, I will explain what’s the prefill and decode processes in LLM inference, and how we implement this p/d disaggregation using KAITO and llm-d projects and how we perform autoscaling for these two processes independently when the traffic changes.

## Slide 3 — About us

To begin with, let me introduce myself. I am Andy Zhang, Software Engineer at Microsoft AKS team, and I am the maintainer of KAITO and several CSI drivers.

Unfortunately, my co-presenter Linbo couldn’t join us because he cannot get his visa in time, so I’ll be presenting alone today.

## Slide 4 — Agenda

Here’s the agenda. We’ll start with inference basics, what are the prefill and decode processes, and why it makes sense to separate them. Then, I will  introduce llm-d and KAITO and show how they work together to support P/D disaggregation. Finally, I will explore how to scale prefill and decode independently when traffic changes.

## Slide 5 — Prefill: process the prompt and select the first token

**Here is an example for prefill process**. Our prompt is “What does Kubernetes do?” Assume one token per word, plus punctuation: five prompt positions. These word-level tokens are illustrative, not a real tokenizer’s output.

We process prompt positions together; each sees only itself and earlier positions. We cache attention keys and values for all five prompt positions at every layer.

Prefill process will use the final position’s scores to select “Kubernetes”. And then Decode will consume it and cache its K/V.

**So next let’s go to decode process.**

## Slide 6 — Decode: consume a token, select the next, repeat

**Decode consumes “Kubernetes”, reads past KV, appends K/V for “Kubernetes” to each layer, and selects “helps”.** Next, it consumes “helps” and selects “teams”. We cache the token we consume, not the one we just select. We reuse past KV.

Each selected token becomes the next input. Repeat until the answer is complete. Below, TTFT is the wait from the request to the first token. ITL is the time between token arrivals.

**The timeline below switches to the client’s view. The wait from sending the request to receiving ‘Kubernetes’ is time to first token, which is TTFT. Once the first token arrives, how long do we wait for the next one? That’s inter-token latency, or ITL.**

**You could see that these two metrics are different, it shows why starting an answer quickly and keeping it flowing smoothly are two different goals.**

## Slide 7 — One request. Two latency targets.

Apparently for one request, there two latency targets.

We want answers to start quickly—and keep going smoothly, **that’s our goal.**

Prefill determines how soon the answer starts, so it determines time to first token, TTFT, and Prefill processes the input and is often compute-bound.

Decode determines whether the answer keeps flowing, so it determines inter-token, ITL, and decode is often memory bandwidth bound. Queueing and delivery matter too.

Our goal is to serve more requests while meeting both latency targets. SLO goodput means the number of requests per second that meet both targets.

## Slide 8 — Long prefills can interrupt token delivery

Long prefills can interrupt token delivery.

In this slide, D is ongoing decode. P is prefill for a new request. Where should P run?

On the shared GPU graph, **there are one prefill task and 4 ongoing decoding workers, you could see** that prefill can pause decode.

On the separate GPUs graph, **prefill and decode runs on different GPU nodes**, and decode can continue while prefill runs elsewhere. The new request still needs a KV handoff **between prefill and decode runtimes** in separate GPUs scenario.

So Separate GPUs remove this execution conflict, but not every source of latency since it requires KV handoff between nodes.

## Slide 9 — Prefill and decode batch different work

Prefill and decode batch different work, Prefill batches prompt positions; decode batches independent requests.

On the left graph, prefill processes the prompt’s tokens in parallel. It can also batch multiple prompts together for efficiency. **But within each prompt, every token can only attend to itself and the tokens before it, that’s called causal attention.**

On the right graph, decode consumes one new token per active request, **read its past KV cache**, then select its next output token.

Prefill gets parallel work from prompt length; decode gets it from active requests. More decode concurrency can raise ITL. Stay within latency and KV-memory budgets.

## Slide 10 — Separate GPU pools let us tune each phase independently

Separate GPU pools let us tune each phase independently. The real benefit is scaling prefill and decode independently to match demand—not simply splitting them into two deployments.

Prefill is often compute-bound. Tune its capacity and parallelism to get better TTFT. On the other hand, decode is often memory-bandwidth-bound. Tune its capacity and batching to get better ITL. **Different latency targets and resource needs can call for different replicas, tensor parallelism and batching policies**. Split only if the gains outweigh KV transfer, extra weight copies and operating costs.

## Slide 11 — The hard part is the Kubernetes wiring to support P/D

The hard part is the Kubernetes wiring to support prefill and decode disaggregation.

Two pools still have to work together as one model service. The EPP, or Endpoint Picker, picks workers. KV transfer settings must match. The decode-side proxy coordinates requests. We must keep pods ready as replicas change.

Routing, KV transfer, labels, ports and readiness must stay in sync, even when pods restart or we scale.

**There are lots of things to combine, that is why the hard part is the Kubernetes wiring.**

## Slide 12 — Production Distributed Inference Architecture

So, this slide shows the big picture.

Running an inference workload takes more than just a model and a GPU. We also need to route requests, manage workloads, and scale when traffic changes.

That’s where **KAITO and llm-d** come in—the orchestration layer in the middle.

Below that, **vLLM** runs the model, and the **KV cache** helps us reuse work instead of doing it again. Kubernetes provides the infrastructure underneath.

We also need things like security and monitoring around the whole system.

The main takeaway is simple: all these pieces need to work together.

Today, we’ll focus on how KAITO and llm-d help with that. Let’s look at some of the open-source options.

## Slide 13 — Open-source P/D has several paths, not one winner

Open-source P/D has several paths, not one winner. The following table presents examples, not a ranking. Some approaches can be used together.

**The middle column** shows the serving and routing path; **the right column** shows what users configure in Kubernetes. Dynamo, llm-d, AIBrix, KServe, Ray Serve and vLLM Production Stack offer different combinations. P/D deployment options already exist. KAITO aims to make them easier to use. **For KAITO users, they want less manual configuration to maintain. Let’s start with llm-d.**

## Slide 14 — llm-d: a distributed inference stack

llm-d is a Kubernetes-native framework for high-performance distributed inference. It joined the CNCF Sandbox in March 2026. **It does not replace vLLM, gateways, or storage systems; it composes them**. **Its value is organized into three ideas**: first modular architecture: Gateway API connects inference routing to Kubernetes, second, Extensible components: combine runtimes, routing plugins and KV transport, third, Well-lit paths, there are tested deployment patterns make trade-offs clear.

## Slide 15 — llm-d: capabilities for distributed inference

These are reusable capabilities, not a performance guarantee. llm-d builds on the serving runtime, not replace it. And we combine reusable llm-d components, Deployment paths explain the trade-offs.

There are mainly four areas of capability for llm-d projects:

first: State-of-the-art MoE serving, Expert parallelism spreads expert computation across GPUs, second, prefill/decode disaggregation, we separate the phases and transfer KV between roles. Third, State-aware scheduling: Routing plugins use cache and load signals to pick workers. Last is autoscaling architecture: workload signals and SLOs guide capacity; each integration chooses its policy.

## Slide 16 — What is KAITO (Kubernetes AI Toolchain Operator)?

Next, what is KAITO, KAITO stands for Kubernetes AI Toolchain Operator, which automates LLM inference, fine-tuning and RAG with Kubernetes operators. It is also a CNCF Sandbox project.

**With KAITO, you only need to** specify a model name and GPU VM SKU. KAITO sizes the nodes to fit the model’s memory requirements, handles model setup and caching, manages inference workloads and rolling updates on Kubernetes, and uses KEDA to automatically scale inference workloads.

## Slide 17 — KAITO workload example

Here is a KAITO inference workload example, user only needs to specify the model name, GPU instance type and replica count.

In this example, user specifies a qwen3 model name which is a huggingface model id and specifies A100 GPU instance type with 3 replicas, **three replicas does not necessarily mean three GPUs; each replica’s GPU and node needs depend on the model and runtime settings.**

**KAITO does all the rest of work, like provisioning the required GPU nodes to fit the model’s memory requirements, handles model setup and caching, manages inference workloads and rolling updates on Kubernetes.**

## Slide 18 — KAITO works out the initial GPU node count

**This slide shows how KAITO does the math.**

User specifies a model name and GPU SKU. KAITO estimates how many nodes the model needs.

KAITO reserves memory for overhead and KV cache, then fits the weights into the remaining GPU memory.

KAITO saves the result as status.targetNodeCount. This path uses tensor parallelism within nodes and pipeline parallelism across nodes. It sizes memory, not how much traffic it can handle.

## Slide 19 — One shared pool ties two capacity decisions together

One shared pool ties two capacity decisions together

A shared pool is simple, but prefill bursts compete with active decoding. **Every worker handles both phases**. One deployment scales both phases together.

Where is the trade-off? Prompt bursts can disrupt token delivery. We scale the whole replica, even when only prefill or decode needs more capacity.We must decide how to run each phase and how much shared capacity to add.

## Slide 20 — Why bring llm-d into KAITO?

So why do we bring llm-d into KAITO?

We want P/D routing without replacing KAITO’s Kubernetes operating model. KAITO manages deployment and lifecycle. llm-d adds endpoint selection and request routing. **vLLM runs the prefill and decode phases, and NIXL moves KV.**

## Slide 21 — Where KAITO and llm-d fit

So where KAITO and llm-d fit.

This is a map of responsibilities, not a required installation checklist. Applications call the inference API. The gateway handles ingress, auth and traffic policy. KAITO manages lifecycle; llm-d selects endpoints.

vLLM runs prefill, decode and batching. NIXL moves KV; cache systems reuse or offload it. **And we depend on Kubernetes to provide** the whole infrastructure to support the stack. We will follow the roles, request routing, KV transfer and capacity control.

## Slide 22 — One endpoint, three separate paths

KAITO manages resources. HTTP carries requests. NIXL moves KV between runtimes.

**Start at the top**: KAITO maintains the role InferenceSets, InferencePool and runtime wiring.

**For a request, the gateway consults the EPP, then forwards to the selected decode sidecar. The sidecar calls remote prefill when needed and local decode.** The client uses one endpoint. KV data bypasses the gateway, EPP and routing sidecar. **NIXL would move KV data between prefill and decode vLLM runtime directly.**

## Slide 23 — One MultiRoleInference declares both roles

One MultiRoleInference declares both roles. This KAITO yaml example sets one prefill replica on A100 and two decode replicas on H100

On the right, we still have one logical service and InferencePool. **Both roles serve the same model.** Each has its own InferenceSet and capacity settings.

## Slide 24 — KAITO creates resources and keeps them aligned

KAITO creates resources and keeps them aligned

KAITO turns the declared topology into workers, routing resources and runtime wiring. For prefill, KAITO set lm-d role labels and the NIXL host or Pod IP. For decode, KAITO injects the llm-d sidecar. Align NIXL and vLLM ports.

For routing, llm-d connect Services, ports and endpoint selection. **So with KAITO and llm-d**, we keep ownership, roles, labels, ports and lifecycle consistent.

KAITO keeps the resources working together; it does not just generate YAML.

## Slide 25 — The decode sidecar coordinates the P/D request

The decode sidecar coordinates the P/D request

The sidecar calls remote prefill when needed, then invokes local decode.

**So here is the graph which shows the whole process.**

**Starting with step one, the gateway sends the request to the decode sidecar.**

**The sidecar calls the remote prefill worker to process the prompt. Prefill returns the KV cache metadata—not the actual KV data.**

**The sidecar passes that metadata to the local decode worker, which uses NIXL to fetch the KV cache directly from prefill and generate the response.**

**The response then goes back through the sidecar and gateway to the client.**

**So, the sidecar coordinates the request, while the runtimes transfer the KV data directly.**

## Slide 26 — KAITO Autoscaling: keda-kaito-scaler

Now, autoscaling. This is how KAITO changes the number of replicas as load moves. The component is keda-kaito-scaler.

It builds on KEDA, but adds three things that matter for GPUs.

First, no extra dependencies - it does not need Prometheus. It reads metrics directly from vLLM, on each pod. Less to install, less to break.

Second, it is GPU-safe. GPU nodes are expensive and slow to start, so it moves gently - only one copy up or down at a time. That keeps things smooth and avoids waste.

Third, it can watch more than one signal at once - like queue length and latency together - and it only scales up when both agree there is real pressure.

So it is autoscaling made for GPU inference: simple, safe on cost, driven by what the server really sees. Next, how does KAITO configures these signals.

## Slide 27 — Let prefill and decode scale independently

**And for p/d disaggregation mode, there is new problem.**

We want to let prefill and decode scale independently.

Prefill watches waiting requests and scales prefill InferenceSet. Decode watches running requests and scales decode InferenceSet.

Give each target one owner. Allow warm-up time, stabilize changes and scale down safely.

**Independent capacity decisions are the goal; KEDA and HPA are the way to implement them.**

## Slide 28 — KAITO autoscaling example: scale prefill and decode separately

Here is the KAITO autoscaling example which could scale prefill and decode separately.

In the yaml config, we have set minimum replicas as 1, maximum replicas as 8 for prefill role, prefill would watch on vLLM number of waiting requests metrics. And we have set minimum replicas as 2, maximum replicas as 16 for decode role, decode would watch on vLLM number of running requests metrics.

On the right side, if waiting requests is 12, running is 12, then prefill requests scale up, decode holds. And later on if running requests exceeds 24, decode can scale up on it’s own.

## Slide 29 — Use derived signals to explain the load

Besides the former vLLM number of waiting requests, number of running requests metrics, we have other vLLM metrics, like kv\_cache\_usage\_percentage,, and time to first token seconds which shows engine-side TTFT tails, and generation token total which shows the output rate. We could monitor on those metrics to write different autoscaling strategy for prefill and decode roles.

## Slide 30 — Where KAITO + llm-d goes next

What’s the next plan for KAITO and llm-d integration.

There are mainly three parts on the road map.

First, we should enable precise cache aware severing, make KAITO route using KV cache events, and supports tier cache across HBM, CPU RAM

and optional filesystems.

Second, Support Encode to Prefill / Decode, support more inference roles.

Third, support explore wide expert parallelism, improve cross-node transport and communication.

## Slide 31 — Resources

Explore the projects, then try the KAITO + llm-d P/D guide. llm-d and KAITO are both CNCF Sandbox projects. Start with their repositories for the code, check keda-kaito-scaler for scaling details, and use the P/D guide for prerequisites and configuration.

References

https://github.com/llm-d

https://github.com/kaito-project/kaito

https://kaito-project.github.io/kaito/docs/prefill-decode-disaggregation/

https://www.cncf.io/projects/llm-d/

https://www.cncf.io/projects/kaito/

https://github.com/kaito-project/keda-kaito-scaler

## Slide 32 — Where can you find us

All of these components are open. On the left, you can find the llm-d website, GitHub organization, and community Slack. On the right are the KAITO documentation and GitHub organization. We welcome you to try the well-lit paths, reproduce the experiments, and bring your real workloads and feedback back to the communities.

## Slide 33 — Thank you

Thank you. We’re happy to take questions.
