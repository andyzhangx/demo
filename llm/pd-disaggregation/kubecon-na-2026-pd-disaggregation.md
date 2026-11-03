# KubeCon North America 2026 — Speaker Scripts (Slides 2–32)

## Slide 2 — Prefill here, decode there Kubernetes-native LLM inference with KAITO and llm-d

OK, let's start now, this session is “Prefill here, decode there<strong>,&#32;</strong>Kubernetes-native LLM inference with KAITO and llm-d”, in this session I will introduce how do we use KAITO and llm-d to implement prefill and decode disaggregation.

## Slide 3 — About us

To begin with, let me introduce myself. I am Andy Zhang, Software Engineer at Microsoft AKS team, and I am the maintainer of KAITO and several CSI drivers.&#32;

Unfortunately, my co-presenter Linbo couldn’t join us because he cannot get his visa in time, so I’ll be presenting alone today.

<p></p>

<p></p>

## Slide 4 — Agenda

Here’s the agenda. We’ll start with inference basics, what are the prefill and decode processes, and why it makes sense to separate them. Then, I will&#32;&#32;introduce llm-d and KAITO and show how they work together to support P/D disaggregation. Finally, I will explore how to scale prefill and decode independently when traffic changes.

## Slide 5 — What is the LLM KV cache?

Before we look at prefill and decode, let’s explain the KV cache. It stores attention keys and values for tokens we’ve already processed—not model weights or finished answers. Prefill builds the cache. Decode uses it, so we don’t recalculate earlier keys and values, though attention still reads them. Longer conversations need more cache memory. When we separate prefill and decode, we pass this cache between them. Let’s see an example.

## Slide 6 — Prefill: process the prompt and select the first token

Let’s use the prompt, ‘What does Kubernetes do?’ We’ll count each word and punctuation mark as a token here, just to keep the example simple. That gives us five tokens.

Prefill processes them together, but each position can only see itself and earlier tokens. It stores their keys and values in the cache at each layer.

Then the last position’s scores give us the first output token: ‘Kubernetes’. Now decode takes that token and continues the answer.

## Slide 7 — Decode: consume a token, select the next, repeat

Now follow the table from top to bottom. Decode takes ‘Kubernetes’, reads the cached keys and values, adds K/V for ‘Kubernetes’, and picks ‘helps’. Then ‘helps’ becomes the next input, and we pick ‘teams’. We repeat this one token at a time.

Notice that we cache the token we process, not the one we’ve just picked.

The timeline below shows what the user sees. The wait for the first token is TTFT. The gaps between later tokens are ITL. So starting quickly and keeping the answer flowing are two different goals. That’s what we’ll look at next.

## Slide 8 — One request. Two latency targets.

For each request, we care about two latency targets.<br>We want a short wait for the first token, and short gaps between the tokens that follow.

Prefill processes the input and is often compute-bound. It is a major contributor to time to first token, or TTFT.

Decode generates tokens one at a time and is often memory-bandwidth-bound. It is a major contributor to inter-token latency, or ITL. Queueing and delivery also affect the latency users experience.

Our goal is to serve more requests while meeting both targets. SLO goodput is the number of requests per second that meet both latency targets.

## Slide 9 — Long prefills can interrupt token delivery

Long prefills can interrupt token delivery.

In this slide, D is ongoing decode. P is prefill for a new request. Where should P run?&#32;

On the shared GPU graph,&#32;<strong>there are one prefill task and 4 ongoing decoding workers, you could see&#32;</strong>that prefill can pause decode.&#32;

On the separate GPUs graph,&#32;**prefill and decode runs on different GPU nodes**, and decode can continue while prefill runs elsewhere. The new request still needs a KV handoff&#32;<strong>between prefill and decode runtimes&#32;</strong>in separate GPUs scenario.

So<strong>&#32;</strong>Separate GPUs remove this execution conflict, but not every source of latency since it requires KV handoff between nodes.

<p></p>

## Slide 10 — P/D improves throughput with llm-d

Here is a benchmark from the llm-d project. Both tests run Llama 4 scout model on the H200 GPUs on two nodes.

<strong>The chart&#32;</strong>compares output speed per user with throughput per GPU.&#32;<strong>With separate prefill and decode workers, llm-d delivers&#32;</strong>higher throughput in the middle of the tested range.

<strong>The key point is simple: we can get more throughput from the same GPUs by separating prefill and decode processes,&#32;</strong>and the benefit depends on the workload.&#32;

Next, let’s see how to set this up on Kubernetes.

## Slide 11 — The hard part is the Kubernetes wiring to support P/D

The hard part is the Kubernetes wiring to support prefill and decode disaggregation.

<p></p>

Two pools still have to work together as one model service. The EPP, or Endpoint Picker, picks workers. KV transfer settings must match. The decode-side proxy coordinates requests. We must keep pods ready as replicas change.

Routing, KV transfer, labels, ports and readiness must stay in sync, even when pods restart or we scale.&#32;

<strong>There are lots of things to combine, that is why the hard part is the Kubernetes wiring.&#32;</strong>

## Slide 12 — Production Distributed Inference Architecture

**So, this slide shows the big picture.**

**Running an inference workload takes more than just a model and a GPU. We also need to route requests, manage workloads, and scale when traffic changes.**

**That’s where KAITO and llm-d come in—the orchestration layer in the middle.**

**Below that, vLLM runs the model, and the KV cache helps us reuse work instead of doing it again. Kubernetes provides the infrastructure underneath.**

**We also need things like security and monitoring around the whole system.**

**The main takeaway is simple: all these pieces need to work together.**

**Today, we’ll focus on how KAITO and llm-d help with that. Let’s look at some of the open-source options.**

## Slide 13 — Several open-source projects support P/D disaggregation

There are already several open-source projects to support P/D disaggregation.

This table shows a few examples and this is not a ranking, and some of these projects can work together.

There are Dynamo, llm-d, and AIBrix, kubeRay, and so on.

**They take different approaches to route requests and managing workloads on Kubernetes.**

For KAITO, the goal is simple: make these options easier to deploy and manage, with less manual configuration.

**Today, we’ll focus on llm-d. Let’s take a closer look.**

## Slide 14 — llm-d: framework for running distributed inference on k8s

So, what is llm-d?

It’s a framework for running distributed inference on Kubernetes.&#32;**It doesn’t replace vLLM—it brings all the pieces together.**&#32;It Brings inference runtimes, routing, and KV cache transport together on Kubernetes.

<p></p>

**There are three ideas here.**

First, a modular design. It connects inference routing to Kubernetes through Gateway API.

Second, flexible components. You can combine different runtimes, routing plugins, and KV transport options.

Third, tested deployment patterns. You don’t have to figure out every piece from scratch.

## Slide 15 — llm-d: capabilities for running distributed inference

And llm-d brings reusable capabilities running distributed inference on Kubernetes.

llm-d builds on the serving runtime, not replace it. And we combine reusable llm-d components, Deployment paths explain the trade-offs.

<p></p>

There are mainly four areas of capability for llm-d projects:

State-of-the-art MoE serving, here MoE means Mixture of Experts, which is supported on all mainstream models now.

prefill/decode disaggregation

State-aware scheduling

autoscaling architecture

## Slide 16 — llm-d “well-lit paths”

llm-d calls these “well-lit paths”—these are tested ways to deploy, with clear guidance on what works well and what the limitations are.

**There are 4 well-lit paths:**

Intelligent scheduling determines where this request should run

KV cache management determines where should reusable state live?

Wide expert parallelism determines how should a large MoE model run across GPUs?

P/D disaggregation determines how should prompt and generation capacity differ?

These paths can work together, but we don’t need all of them at once. Results depend on the hardware.&#32;

**Today, we’ll focus on P/D disaggregation.**

## Slide 17 — What is KAITO (Kubernetes AI Toolchain Operator)?

Next, what is KAITO, KAITO stands for Kubernetes AI Toolchain Operator, which automates LLM inference, fine-tuning and RAG with Kubernetes operators. It is also a CNCF Sandbox project.

<strong>With KAITO, you only need to&#32;</strong>specify a model name and GPU VM SKU. KAITO sizes the nodes to fit the model’s memory requirements, handles model setup and caching, manages inference workloads and rolling updates on Kubernetes, and uses KEDA to automatically scale inference workloads.

## Slide 18 — KAITO inference workload example

Here is a KAITO inference workload example, user only needs to specify the model name, GPU instance type and replica count.

In this example, user specifies a qwen3 model name which is a huggingface model id and specifies A100 GPU instance type with 3 replicas,&#32;<strong>three replicas does not necessarily mean three GPUs; each replica’s GPU and node needs depend on the model and runtime settings.&#32;</strong>

**KAITO does all the rest of work, like provisioning the required GPU nodes to fit the model’s memory requirements, handles model setup and caching, manages inference workloads and rolling updates on Kubernetes.**

## Slide 19 — KAITO works out the initial GPU node count

**This slide shows how KAITO does the math.**

User specifies a model name and GPU SKU. KAITO estimates how many nodes the model needs.

KAITO reserves memory for overhead and KV cache, then fits the weights into the remaining GPU memory.

KAITO saves the result as status.targetNodeCount. This path uses tensor parallelism within nodes and pipeline parallelism across nodes. It sizes memory, not how much traffic it can handle.&#32;

## Slide 20 — Why bring llm-d into KAITO?

So why do we bring llm-d into KAITO?&#32;

We want P/D routing without replacing KAITO’s Kubernetes operating model. KAITO manages deployment and lifecycle. llm-d adds endpoint selection and request routing.&#32;**vLLM runs the prefill and decode phases, and NIXL moves KV.**

## Slide 21 — One endpoint, separate request and KV paths

The client only uses one endpoint.&#32;<strong>Behind it,&#32;</strong>KAITO manages the workloads. Requests go through routing; KV cache moves directly between runtimes via NIXL.

**KAITO sets up the prefill and decode workloads and connects the components.**

**When a request arrives, the gateway asks the llm-d Router EPP where to send it. The selected routing sidecar then coordinates prefill and decode.**

## Slide 22 — one KAITO MultiRoleInference declares both roles

One KAITO MultiRoleInference declares both roles. This KAITO yaml example sets one prefill replica on A100 and two decode replicas on H100

On the right, we still have one logical service and InferencePool. Both roles serve the same model. Each has its own InferenceSet and capacity settings.&#32;

<p></p>

## Slide 23 — KAITO creates resources and keeps them aligned

KAITO creates resources and keeps them aligned

KAITO turns the declared topology into workers, routing resources and runtime wiring. For prefill, KAITO set lm-d role labels and the NIXL host or Pod IP. For decode, KAITO injects the llm-d sidecar. Align NIXL and vLLM ports.

For routing, llm-d connect Services, ports and endpoint selection.&#32;**So with KAITO and llm-d**, we keep ownership, roles, labels, ports and lifecycle consistent.&#32;

KAITO keeps the resources working together; it&#32;**continuously**&#32;reconciles them to keep the inference deployment in the desired state.

## Slide 24 — The decode sidecar coordinates the P/D request

The decode sidecar coordinates the P/D request

**So here is the graph which shows the whole process.**

<p></p>

**Starting with step one, the gateway sends the request to the decode sidecar.**

<strong>The sidecar calls the remote prefill worker to process the prompt.&#32;</strong>

**Prefill returns the KV cache metadata instead of the actual KV data to the decode sidear.**

**The sidecar passes that KV metadata to the local decode worker, which uses NIXL to fetch the KV cache directly from prefill runtime and generate the response.**

**The response then goes back through the sidecar and gateway to the client.**

So, the sidecar passes calls and KV metadata. The runtimes transfer the actual KV data.

<p></p>

## Slide 25 — KAITO autoscaling: keda-kaito-scaler

**Now, let’s talk about autoscaling.**

**KAITO uses a component called keda-kaito-scaler, which is built on KEDA. There are three things to highlight.**

First, no Prometheus is needed. The scaler reads metrics directly from vLLM pods, does not depend on Prometheus.

Second, it scales gradually. It adds or removes one replica at a time, with a pause between changes.

Third, it can combine multiple signals. It can combine queue length and queue wait time; both must cross their thresholds before scaling up.

## Slide 26 — Let prefill and decode scale independently

**And for p/d disaggregation mode, there is a new problem.**

We want to let prefill and decode scale independently. each role gets its own signal, threshold and replica target.

Prefill watches waiting requests and scales replicas of prefill InferenceSet. Decode watches running requests and scales replicas of decode InferenceSet.

Use one autoscaler for each role. Give new pods time to warm up, and scale down gradually.

**KEDA and HPA let us scale prefill and decode separately, based on what each one needs.**

## Slide 27 — KAITO autoscaling example: scale prefill and decode separately

Here is the KAITO autoscaling example which could scale prefill and decode separately.

In the yaml config, we have set different scaling strategies for prefill and decode roles. Prefill would monitor on number of waiting requests metrics and decode would monitor on number of running requests metrics.&#32;

On the right side, if waiting requests is 12, running is 12, then prefill replicas scale up, decode holds. And later on if running requests exceeds 24, decode replicas can scale up on it’s own.

## Slide 28 — Use derived signals to explain the load

Besides the former vLLM number of waiting requests, number of running requests metrics, we have other vLLM metrics, like kv\_cache\_usage\_percentage,, and time to first token seconds which shows engine-side TTFT tails, and generation token total which shows the output rate.&#32;**We could monitor on those metrics to write different autoscaling strategy for prefill and decode roles.**

## Slide 29 — Where KAITO + llm-d goes next

What’s the next plan for KAITO and llm-d integration.

There are mainly three parts on the road map.

First, we should enable precise cache aware severing,&#32;<strong>make KAITO&#32;</strong>route using KV cache events, and&#32;**supports**&#32;tier cache across HBM, CPU RAM

and optional filesystems.

Second, extend P/D disaggregation to include encoding&#32;<strong>for multimodal inputs, such as images and audio. </strong>

Third, support explore wide expert parallelism, improve cross-node transport and communication.

## Slide 30 — Resources

Explore the projects, then try the KAITO + llm-d P/D guide.&#32;**Here are all the resource links.**

<p></p>

llm-d and KAITO are both CNCF Sandbox projects. Start with their repositories for the code, check keda-kaito-scaler for scaling details, and use the P/D guide for prerequisites and configuration.

## Slide 31 — Where can you find us

All of these components are open. On the left, you can find the llm-d website, GitHub organization, and community Slack. On the right are the KAITO documentation and GitHub organization. We welcome you to try the well-lit paths, reproduce the experiments, and bring your real workloads and feedback back to the communities.<br>

## Slide 32 — Thank you

Thank you. We’re happy to take questions.
