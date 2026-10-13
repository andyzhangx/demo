# KAITO CPU Minimal-Change POC

## Goal

Design a **minimal-change POC** for KAITO to support a CPU model path.

Implemented branch reference:

- `https://github.com/andyzhangx/kaito/tree/andyzhangx/kaito-cpu-poc-minimal-cpu-model`

This POC is intentionally narrow:

- prove KAITO can launch a CPU-served model successfully
- do **not** optimize for extensibility
- do **not** try to build a full CPU runtime architecture
- do **not** attempt feature parity with the GPU path

The main question is not "how should long-term CPU support look", but:

> What is the smallest set of code and config changes needed to make a CPU model run successfully in KAITO?

---

## PR-Style Summary for the Implemented Branch

### Title

`feat: add minimal CPU custom model POC`

### What this branch changes

This branch adds the smallest practical set of changes needed to prove KAITO can run a CPU-served custom model:

- adds a new CPU-only base image build path:
  - `docker/presets/models/tfs-cpu/Dockerfile`
  - `presets/workspace/dependencies/requirements-cpu.txt`
  - `make docker-build-kaito-base-cpu`
- adds a CPU custom model example:
  - `examples/custom-model-integration/custom-model-deployment-cpu.yaml`
- updates the workspace controller so template-based inference can use `resource.count` directly instead of the GPU/vLLM node estimator
- adds/updates controller tests for the new template-based target node count behavior
- documents the CPU-only custom-model POC in `website/docs/custom-model.md`

### Why this is minimal

The branch deliberately avoids introducing:

- new CRD fields
- runtime profile redesign
- preset CPU support
- CPU auto provisioning
- llama.cpp support
- benchmark/autoscaling changes

It only proves that a custom Hugging Face model can be launched on a CPU node using the existing custom Workspace path.

## Scope

This POC supports only the following scenario:

- **custom/BYO model only**
- **custom template Workspace only**
- **BYO CPU nodes only**
- **Hugging Face `transformers` runtime only**
- **single-node inference only**

Everything else is out of scope.

---

## Non-Goals

The following are explicitly **not** included in this POC:

- preset CPU support
- node auto provisioning for CPU SKUs
- runtimeProfile or accelerator API redesign
- CPU/GPU unified runtime abstraction
- `llama-cpp-cpu`
- `vllm-cpp-cpu`
- CPU benchmark support
- CPU autoscaling
- MultiRoleInference support on CPU
- speculative decoding on CPU
- advanced scheduler/resource optimization
- performance tuning or quantization strategy

This is intentionally a **temporary narrow solution**, not a clean long-term architecture.

---

## Runtime Choice

For a minimal POC, the runtime should be:

- **`transformers-cpu`**

Reason:

- it matches the dominant native format for mainstream Hugging Face models
- it reuses the existing KAITO custom model serving shape
- it avoids introducing GGUF/`llama.cpp` model format changes
- it minimizes image and controller work

For this POC, the user explicitly sets:

- `kaito.sh/runtime: transformers`
- `--device_map cpu`

This is enough to prove CPU inference can work without adding a new runtime abstraction.

---

## High-Level Design

The POC has only two real design ideas:

1. **Add a CPU-only base image** for custom model serving.
2. **Bypass GPU node estimation logic** for template-based CPU inference and use `resource.count` directly.

Everything else should reuse existing KAITO behavior.

---

## POC Architecture

### 1. Reuse the existing custom model path

Do **not** introduce new API fields.

Do **not** add:

- `runtimeProfile`
- `accelerator: cpu|gpu`
- new CRD fields
- CPU-specific preset logic

Instead, reuse the existing custom Workspace path:

- `Workspace.inference.template`
- `kaito.sh/runtime: transformers`
- existing `inference_api.py`

This keeps the control-plane change as small as possible.

### 2. Introduce a dedicated CPU image

Add one new image only:

- `kaito-base-cpu`

This image is used only for the custom CPU POC.

It should contain:

- Python runtime
- CPU-only torch
- transformers
- accelerate
- fastapi / uvicorn
- current custom-model inference script dependencies

It should **not** contain:

- CUDA toolkit
- CUDA wheels
- vLLM
- GPU-only runtime packages

### 3. Require BYO CPU nodes

Do not touch node auto provisioning for this POC.

The user must bring an existing CPU node and label it, for example:

```bash
kubectl label node <cpu-node-name> kaito.sh/cpu-inference=true
```

Then the Workspace selects it through `resource.labelSelector`.

This avoids introducing CPU SKU selection, scheduling policy redesign, or estimator changes beyond the minimal one needed below.

### 4. Minimal controller change

Current logic assumes inference workloads may need GPU/vLLM-driven node estimation.

That does not work for a custom CPU template POC.

For this narrow case:

- if the Workspace uses `inference.template`
- and the user explicitly provides `resource.count`
- then the controller should **use `resource.count` directly** instead of invoking the GPU estimator

This is the only controller behavior change needed for the POC.

---

## How to Use This POC

## Prerequisites

Before using this POC, assume all of the following are true:

- you are running KAITO in **BYO mode**
- `disableNodeAutoProvisioning=true`
- you already have at least one Kubernetes node with enough CPU and memory for the model
- that node is intended for CPU inference only
- you are using a Hugging Face model that can run via `transformers` on CPU

## Recommended model for the POC

The example branch uses:

- `microsoft/Phi-3-mini-4k-instruct`

Why this model was chosen:

- it is a recognizable Hugging Face causal LM
- it works with the existing `transformers`-style serving flow
- it demonstrates the CPU custom-model path without introducing a new runtime or model format

However, for an actual CPU-only smoke test, you may want to start with a **smaller** model if your node is resource-constrained. The important point for the POC is not model quality, but verifying that the end-to-end CPU serving path works.

## Step 1: Build the CPU image

From the `kaito` repo branch:

```bash
make docker-build-kaito-base-cpu REGISTRY=<your-registry> OUTPUT_TYPE=type=docker
```

If you want to push the image to a registry, use an output mode appropriate for your environment, for example:

```bash
make docker-build-kaito-base-cpu \
  REGISTRY=<your-registry> \
  OUTPUT_TYPE=type=registry
```

The image name introduced by this POC is:

- `kaito-base-cpu`

The Dockerfile is:

- `docker/presets/models/tfs-cpu/Dockerfile`

The CPU-specific Python dependency file is:

- `presets/workspace/dependencies/requirements-cpu.txt`

## Step 2: Prepare a CPU node

Label a CPU node so the Workspace can select it explicitly:

```bash
kubectl label node <cpu-node-name> kaito.sh/cpu-inference=true
```

This is important because the POC intentionally does **not** implement CPU auto provisioning or CPU-specific scheduler logic beyond label-based selection.

## Step 3: Use the provided config file

The branch adds this example manifest:

- `examples/custom-model-integration/custom-model-deployment-cpu.yaml`

This is the intended starting point for the POC.

### What this config does

The example manifest:

- creates a `Workspace`
- sets `kaito.sh/runtime: transformers`
- requires `resource.count: 1`
- selects a labeled BYO CPU node with:
  - `kaito.sh/cpu-inference: "true"`
- uses the CPU image:
  - `mcr.microsoft.com/aks/kaito/kaito-base-cpu:0.0.1`
- launches the existing inference server script:
  - `/workspace/tfs/inference_api.py`
- forces CPU execution with:
  - `--device_map cpu`

### Example config shape

```yaml
apiVersion: kaito.sh/v1beta1
kind: Workspace
metadata:
  name: workspace-custom-llm-cpu
  annotations:
    kaito.sh/runtime: transformers
resource:
  count: 1
  labelSelector:
    matchLabels:
      kaito.sh/cpu-inference: "true"
inference:
  template:
    metadata:
      labels:
        apps: custom-llm-cpu
    spec:
      containers:
        - name: custom-llm-cpu
          image: mcr.microsoft.com/aks/kaito/kaito-base-cpu:0.0.1
          ports:
            - containerPort: 5000
          resources:
            requests:
              cpu: "8"
              memory: 32Gi
            limits:
              cpu: "8"
              memory: 32Gi
          command:
            - "python3"
          args:
            - "/workspace/tfs/inference_api.py"
            - "--pipeline"
            - "text-generation"
            - "--allow_remote_files"
            - "--pretrained_model_name_or_path"
            - "microsoft/Phi-3-mini-4k-instruct"
            - "--torch_dtype"
            - "float32"
            - "--device_map"
            - "cpu"
```

## Step 4: Update the image reference if needed

If you built and pushed the image to your own registry, change:

```yaml
image: mcr.microsoft.com/aks/kaito/kaito-base-cpu:0.0.1
```

to your actual published image, for example:

```yaml
image: <your-registry>/kaito-base-cpu:v0.0.1
```

## Step 5: Apply the Workspace

```bash
kubectl apply -f examples/custom-model-integration/custom-model-deployment-cpu.yaml
```

Or apply your modified copy if you changed the image or model.

## Step 6: Validate the POC

This POC should be considered successful if all of the following happen:

- the pod lands on the labeled CPU node
- the container starts successfully
- readiness and liveness probes pass
- the model downloads and initializes successfully
- at least one inference request succeeds

## Copy-paste command checklist

The following sequence is intended to be executable with minimal editing. Replace the placeholder values first:

- `<your-registry>`
- `<cpu-node-name>`
- `<your-image>`

### 1. Build and push the CPU image

```bash
cd <path-to-kaito-repo>
git checkout andyzhangx/kaito-cpu-poc-minimal-cpu-model

make docker-build-kaito-base-cpu \
  REGISTRY=<your-registry> \
  OUTPUT_TYPE=type=registry
```

This produces and pushes an image equivalent to:

```text
<your-registry>/kaito-base-cpu:v0.0.1
```

### 2. Label a CPU node

```bash
kubectl label node <cpu-node-name> kaito.sh/cpu-inference=true --overwrite
```

### 3. Copy and patch the example manifest

```bash
cd <path-to-kaito-repo>
cp examples/custom-model-integration/custom-model-deployment-cpu.yaml /tmp/custom-model-deployment-cpu.yaml
sed -i 's#mcr.microsoft.com/aks/kaito/kaito-base-cpu:0.0.1#<your-image>#' /tmp/custom-model-deployment-cpu.yaml
```

Example image value:

```text
<your-registry>/kaito-base-cpu:v0.0.1
```

### 4. Apply the Workspace

```bash
kubectl apply -f /tmp/custom-model-deployment-cpu.yaml
```

### 5. Watch the pod and Workspace

```bash
kubectl get workspace workspace-custom-llm-cpu -o yaml
kubectl get pods -l apps=custom-llm-cpu -w
```

### 6. Inspect logs if startup takes time

```bash
kubectl logs -l apps=custom-llm-cpu --tail=200 -f
```

### 7. Verify the pod landed on the intended CPU node

```bash
kubectl get pod -l apps=custom-llm-cpu -o wide
```

### 8. Port-forward and run a smoke request

```bash
kubectl port-forward pod/$(kubectl get pod -l apps=custom-llm-cpu -o jsonpath='{.items[0].metadata.name}') 5000:5000
```

In another terminal:

```bash
curl -s http://127.0.0.1:5000/health
```

If the server exposes OpenAI-style generation endpoints through the existing script wiring, you can also try a small generation request after the model is ready. The exact request shape depends on the inference script behavior in your branch, so the minimum required smoke check for this POC is the health endpoint plus successful model initialization in logs.

## Common failure modes / troubleshooting

### 1. Pod stays Pending

Typical causes:

- no node has `kaito.sh/cpu-inference=true`
- the labeled node does not have enough CPU or memory
- other node selectors / taints block placement

Checks:

```bash
kubectl get nodes --show-labels | grep kaito.sh/cpu-inference
kubectl describe pod -l apps=custom-llm-cpu
```

### 2. Image pull failure

Typical causes:

- the image was not pushed successfully
- the image reference in the YAML still points at the default MCR placeholder
- the cluster cannot pull from your private registry

Checks:

```bash
kubectl describe pod -l apps=custom-llm-cpu
```

Look for errors such as:

- `ImagePullBackOff`
- `ErrImagePull`
- authentication failures against the registry

### 3. Model download hangs or fails

Typical causes:

- outbound network restrictions to Hugging Face
- gated/private model without token
- model too large for the available node memory or disk

Checks:

```bash
kubectl logs -l apps=custom-llm-cpu --tail=200
```

If a Hugging Face token is required, uncomment and populate the example `HF_TOKEN` env block in the manifest.

### 4. Container starts but health probes fail

Typical causes:

- model initialization is still in progress
- CPU node is too small, so startup is extremely slow
- the model choice is too large for the machine

Actions:

- wait longer and continue watching logs
- try a smaller model first
- increase CPU and memory requests/limits

### 5. The wrong estimator path is still being used

This POC depends on the controller branch containing the minimal target-node-count logic change.

Make sure you are actually running KAITO built from the branch that contains the CPU POC changes:

- `andyzhangx/kaito-cpu-poc-minimal-cpu-model`

If you are running an older controller image/build, the template-based inference workload may still flow through GPU-oriented logic.

### 6. CPU model works but is too slow

That is expected for this POC.

This design intentionally does **not** optimize for:

- throughput
- latency
- quantization strategy
- autoscaling
- large-model CPU serving efficiency

If the goal changes from “prove it works” to “make it practical,” that is the point where a follow-up design should evaluate `llama-cpp-cpu`, preset support, or broader runtime/profile work.

## Expected output / 成功时你会看到什么

如果这个 POC 按预期工作，通常会看到下面这些现象。

### 1. Workspace 已创建且 target node count 合理

```bash
kubectl get workspace workspace-custom-llm-cpu -o yaml
```

你应该能看到：

- Workspace 对象存在
- `status.targetNodeCount` 被设置为你在 manifest 里指定的 `resource.count`
- 没有因为 GPU estimator 失败而报错

### 2. Pod 被调度到你打了 label 的 CPU 节点

```bash
kubectl get pod -l apps=custom-llm-cpu -o wide
```

你应该看到：

- pod 状态从 `Pending` 进入 `Running`
- `NODE` 列是你打过 `kaito.sh/cpu-inference=true` 的节点

### 3. 容器日志显示模型正在下载和初始化

```bash
kubectl logs -l apps=custom-llm-cpu --tail=200 -f
```

常见的成功信号包括：

- Hugging Face 模型开始下载
- tokenizer / weights 被加载
- 推理服务启动
- 没有持续性的 Python traceback 或 OOM 错误

### 4. Readiness / liveness probe 通过

```bash
kubectl describe pod -l apps=custom-llm-cpu
```

你应该看到：

- 没有反复的 probe failure 事件
- container 没有陷入重启循环
- pod 最终进入 Ready 状态

### 5. health endpoint 返回成功

完成 port-forward 后：

```bash
curl -s http://127.0.0.1:5000/health
```

你应该看到：

- 返回成功响应（例如 `200 OK`，或脚本定义的健康检查内容）
- 不会出现连接拒绝、超时或 5xx

### 6. 至少一次推理请求成功

最小成功标准不是高性能，而是：

- 服务已经起来
- 模型已经完成初始化
- 至少有一次推理请求能成功返回

即使吞吐低、延迟高，只要完成这一步，这个 POC 的核心目标就达成了。

### 7. 这是一个“能跑通”的成功，不是“性能达标”的成功

这个 POC 成功时的意义是：

- KAITO 可以通过最小改动跑通 CPU custom model 路径
- 现有 custom Workspace + transformers serving 路径可以被 CPU image 复用
- controller 只需要很小的逻辑修正就能避开 GPU estimator 问题

它**不**意味着：

- CPU 性能已经足够好
- 大模型在 CPU 上已经 practical
- preset / autoscaling / advanced features 已经支持

## Validation and benchmark results

The following results were captured from a real AKS cluster using the CPU POC branch and example Workspace.

### Test environment

- KAITO branch:
  - `https://github.com/andyzhangx/kaito/tree/andyzhangx/kaito-cpu-poc-minimal-cpu-model`
- Example manifest:
  - `examples/custom-model-integration/custom-model-deployment-cpu.yaml`
- Model:
  - `microsoft/Phi-3-mini-4k-instruct`
- Runtime:
  - `transformers`
- Model launch args:
  - `--pipeline text-generation`
  - `--allow_remote_files`
  - `--torch_dtype float32`
  - `--device_map cpu`
- Pod resources:
  - `requests.cpu=8`
  - `limits.cpu=8`
  - `requests.memory=32Gi`
  - `limits.memory=32Gi`
- Actual worker node used by the test:
  - `Standard_D16s_v5`
- Observed node allocatable:
  - `15740m` CPU
  - `60565128Ki` memory

### Functional validation summary

The CPU POC worked end to end on the AKS cluster.

Observed success signals:

- `Workspace` reached `Ready`
- `InferenceReady=True`
- `WorkspaceSucceeded=True`
- Pod `workspace-custom-llm-cpu-0` reached `Running/Ready`
- `/health` returned success
- `/v1/models` returned the served model successfully
- repeated inference requests returned valid completions

Example `/v1/models` result:

```json
{
  "object": "list",
  "data": [
    {
      "id": "microsoft/Phi-3-mini-4k-instruct",
      "object": "model",
      "owned_by": "kaito"
    }
  ]
}
```

### Resource observations during the test

- `kubectl top pod` showed memory around `15786Mi`
- the server `/metrics` endpoint reported host memory usage around `17.3GB`-`17.5GB` during the long-request test
- the server `/metrics` endpoint reported CPU load around `51%`-`56%` during the long-request test

This is enough to show the CPU path is viable for a POC, though not optimized.

### Benchmark request shapes

#### Short request

Prompt:

```text
Give me a one-sentence summary of Azure Kubernetes Service.
```

Parameters:

- `max_tokens=64`
- `temperature=0`

Observed token pattern:

- prompt tokens: `17`
- completion tokens: `39`
- total tokens: `56`

#### Long request

Prompt:

```text
Explain what Azure Kubernetes Service is, then list five practical use cases and one caveat for each. Keep it concise but complete.
```

Parameters:

- `max_tokens=256`
- `temperature=0`

Observed token pattern:

- prompt tokens: `32`
- completion tokens: `256`
- total tokens: `288`
- finish reason: `length`

### Benchmark summary table

| Request type | Samples | Success rate | Avg latency | P50 | P90 | P95 | P99 | Max | Avg output tokens | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Short request | 83 | 100% | 7188.48 ms | 7184.88 ms | 7250.36 ms | 7284.21 ms | 7385.80 ms | 7478.96 ms | 39 | 5.425 tok/s |
| Short request rerun | 20 | 100% | 7188.04 ms | 7185.40 ms | 7260.79 ms | 7281.07 ms | 7294.51 ms | 7297.87 ms | 39 | 5.426 tok/s |
| Long request | 20 | 100% | 46244.53 ms | 46233.62 ms | 46496.71 ms | 46647.01 ms | 46702.87 ms | 46716.83 ms | 256 | 5.536 tok/s |

### Direct takeaways

- The CPU POC is **functionally stable** for repeated single-request inference.
- Short requests are consistently about **7.2s** end to end.
- A 256-token long response is consistently about **46.2s** end to end.
- Output throughput stays very stable at roughly **5.4-5.5 tokens/sec**.
- This is good enough for:
  - smoke tests
  - functional validation
  - demos
  - low-frequency internal experiments
- This is **not** a low-latency production serving result.

## Additional experimental vLLM CPU workspace benchmark

The earlier benchmark in this document validates the **minimal transformers-based CPU POC**.

Separately, I also validated an **experimental vLLM CPU custom Workspace** after fixing the LMCache CPU-runtime startup issue on branch:

- `https://github.com/andyzhangx/kaito/tree/andyzhangx/kaito-cpu-poc-minimal-cpu-model`

This is a different setup from the original transformers CPU POC, so the numbers below should be treated as a **separate experiment**, not a direct apples-to-apples comparison.

### Experimental vLLM CPU test environment

- Workspace: `workspace-custom-vllm-cpu`
- Pod: `workspace-custom-vllm-cpu-0`
- Image:
  - `andyzhangx/kaito-vllm-cpu:v0.0.1`
- Model:
  - `Qwen/Qwen2.5-0.5B-Instruct`
- Served model name:
  - `qwen2.5-0.5b-instruct-cpu`
- Runtime family:
  - `vLLM CPU`
- Pod resources:
  - `requests.cpu=8`
  - `limits.cpu=8`
  - `requests.memory=32Gi`
  - `limits.memory=32Gi`
- Worker node:
  - `Standard_D16s_v5`
- Readiness during benchmark:
  - pod `Running`
  - pod `Ready=true`
  - `restartCount=0`

### Experimental vLLM CPU test method

- The benchmark was executed from **inside the serving pod** via `kubectl exec` and called `http://127.0.0.1:5000/v1/chat/completions` directly.
- This avoids `kubectl port-forward` instability and keeps the measurements focused on model-serving latency rather than tunnel behavior.
- Requests were sent **serially**, one at a time.
- Temperature was fixed at `0`.
- Sample count:
  - short requests: `20`
  - long requests: `20`

### Experimental vLLM CPU request shapes

#### Short request

Prompt shape:

```text
In one short sentence, explain what Kubernetes is.
```

Parameters:

- `max_tokens=32`
- `temperature=0`

Observed averages:

- prompt tokens: `51.55`
- completion tokens: `21`

#### Long request

Prompt shape:

```text
Explain how Kubernetes handles pod creation from API submission to container start, with sections for API server, scheduler, kubelet, container runtime, and networking/storage considerations.
```

Parameters:

- `max_tokens=256`
- `temperature=0`

Observed averages:

- prompt tokens: `71.55`
- completion tokens: `256`
- finish reason: `length`

### Experimental vLLM CPU benchmark summary table

| Request type | Samples | Success rate | Avg latency | P50 | P95 | Min | Max | Avg output tokens | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Short request | 20 | 100% | 759.10 ms | 760.55 ms | 779.63 ms | 730.56 ms | 783.69 ms | 21 | 27.67 tok/s |
| Long request | 20 | 100% | 6838.10 ms | 6828.32 ms | 6943.23 ms | 6749.47 ms | 6958.07 ms | 256 | 37.44 tok/s |

### Experimental vLLM CPU direct takeaways

- The experimental vLLM CPU workspace was **stable** across all 40 measured requests.
- Short requests completed in about **0.76s** on average.
- Long requests that generated **256 output tokens** completed in about **6.84s** on average.
- Output throughput stayed very stable at about:
  - **27.7 tok/s** for the short-request shape
  - **37.4 tok/s** for the long-request shape
- These numbers are materially better than the earlier transformers CPU POC numbers in this document, but the setup is also different:
  - different runtime family
  - much smaller model
  - different prompt/output shapes
- So the correct conclusion is **not** “CPU is now fast in general”, but rather:
  - this specific experimental vLLM CPU workspace shape is viable for small-model single-request serving

## Additional transformers CPU rerun on the same Qwen request set

After the experimental vLLM CPU benchmark above, the same live workspace name was reconfigured from the vLLM CPU path to the **transformers CPU** path, still using:

- `Qwen/Qwen2.5-0.5B-Instruct`

The point of this rerun was simple:

- first record the earlier **20 short + 20 long** vLLM CPU results as a baseline
- then run the **same request shapes** again on the transformers CPU path
- compare the two results directly

### Transformers CPU rerun environment

- Workspace:
  - `workspace-custom-vllm-cpu`
- Runtime annotation:
  - `transformers`
- Image:
  - `andyzhangx/kaito-base-cpu:v0.0.1`
- Model:
  - `Qwen/Qwen2.5-0.5B-Instruct`
- Worker node:
  - `Standard_D16s_v5`
- Pod resources:
  - `requests.cpu=8`
  - `limits.cpu=8`
  - `requests.memory=32Gi`
  - `limits.memory=32Gi`
- Pod state during benchmark:
  - `Running`
  - `Ready=true`
  - `restartCount=0`

### Transformers CPU rerun method

- The benchmark was executed from **inside the serving pod** via `kubectl exec`.
- The endpoint was:
  - `http://127.0.0.1:5000/v1/chat/completions`
- Requests were sent **serially**, one at a time.
- Temperature was fixed at `0`.
- Sample count:
  - short requests: `20`
  - long requests: `20`

### Stored request content

The exact 40 test request texts used for the Qwen rerun are stored under:

- `llm/kaito/kaito-cpu-minimal-poc-test/`

Files:

- `llm/kaito/kaito-cpu-minimal-poc-test/short-requests.txt`
- `llm/kaito/kaito-cpu-minimal-poc-test/long-requests.txt`

### Request shapes reused for the rerun

#### Short request

Prompt shape:

```text
Request N: In one short sentence, explain what Kubernetes is. Keep it under 20 words.
```

Parameters:

- `max_tokens=32`
- `temperature=0`

Observed averages:

- prompt tokens: `51.55`
- completion tokens: `21`

#### Long request

Prompt shape:

```text
Request N: Explain how Kubernetes handles pod creation from API submission to container start. Use a concise but detailed structure with sections for API server, scheduler, kubelet, container runtime, and networking/storage considerations.
```

Parameters:

- `max_tokens=256`
- `temperature=0`

Observed averages:

- prompt tokens: `71.55`
- completion tokens: `256`
- finish reason: `length`

### Transformers CPU rerun summary table

| Request type | Samples | Success rate | Avg latency | P50 | P95 | Min | Max | Avg output tokens | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Short request | 20 | 100% | 840.24 ms | 826.64 ms | 899.56 ms | 805.56 ms | 953.81 ms | 21 | 25.03 tok/s |
| Long request | 20 | 100% | 9354.59 ms | 9352.76 ms | 9482.73 ms | 9164.59 ms | 9533.48 ms | 256 | 27.37 tok/s |

### Baseline vs rerun comparison

Using the earlier experimental vLLM CPU benchmark in this document as the baseline:

#### Short request

- avg latency:
  - baseline vLLM CPU: `759.10 ms`
  - rerun transformers CPU: `840.24 ms`
  - delta: `+10.69%`
- avg throughput:
  - baseline vLLM CPU: `27.67 tok/s`
  - rerun transformers CPU: `25.03 tok/s`
  - delta: `-9.54%`

#### Long request

- avg latency:
  - baseline vLLM CPU: `6838.10 ms`
  - rerun transformers CPU: `9354.59 ms`
  - delta: `+36.80%`
- avg throughput:
  - baseline vLLM CPU: `37.44 tok/s`
  - rerun transformers CPU: `27.37 tok/s`
  - delta: `-26.90%`

### Transformers CPU rerun direct takeaways

- The rerun was **stable**: all **40/40** requests succeeded.
- The transformers CPU path for Qwen is now not only functional but also directly benchmarked.
- On this request set, the transformers CPU path is slower than the earlier experimental vLLM CPU path for the same workspace/model family.
- The difference is especially visible on the long-request case, where the average latency increased by about **36.8%** and throughput dropped by about **26.9%**.
- So for this exact CPU-only Qwen experiment, the main takeaway is:
  - **both paths work**, but the experimental vLLM CPU path was faster than the transformers CPU rerun for the same prompt shapes.

### Same-model CPU runtime comparison summary (Qwen2.5-0.5B-Instruct)

For the same `Qwen/Qwen2.5-0.5B-Instruct` model, on the same request set and the same general node shape, the current measured result is:

- **vLLM CPU is faster than transformers CPU**

#### Side-by-side summary

| Request type | Runtime | Success rate | Avg latency | P95 latency | Throughput |
| --- | --- | ---: | ---: | ---: | ---: |
| Short request | vLLM CPU | 100% | 759.10 ms | 779.63 ms | 27.67 tok/s |
| Short request | transformers CPU | 100% | 840.24 ms | 899.56 ms | 25.03 tok/s |
| Long request | vLLM CPU | 100% | 6838.10 ms | 6943.23 ms | 37.44 tok/s |
| Long request | transformers CPU | 100% | 9354.59 ms | 9482.73 ms | 27.37 tok/s |

#### Comparison takeaway

- For this exact CPU-only Qwen experiment:
  - both runtimes worked
  - both were stable
  - **vLLM CPU delivered lower latency and higher token throughput**
- The gap was modest on the short-request case, but much more visible on the long-request case.
- So if the question is simply:
  - “for the same Qwen CPU model, which runtime performed better in this test?”
- the answer is:
  - **vLLM CPU performed better than transformers CPU in this benchmark.**

### What the original transformers benchmark numbers mean

For `microsoft/Phi-3-mini-4k-instruct` on the original transformers-based CPU POC shape:

- the path definitely works
- latency is predictable
- performance is far below a GPU-backed path
- the main value of this POC is proof of correctness and integration simplicity, not production-grade CPU serving efficiency

## How to estimate CPU and memory requirements for a CPU model

There is usually no single official source that tells you the exact CPU and memory requirements for an arbitrary Hugging Face model on CPU. In practice, you estimate the requirements from a combination of model size, dtype, runtime choice, and benchmark results.

### Memory is usually easier to estimate than CPU

Memory sizing starts from the model parameter count.

For example, `microsoft/Phi-3-mini-4k-instruct` is a roughly **3.8B parameter** model.

If the model is loaded with:

- `float32`

then a rough lower-bound estimate for model weights alone is:

- `3.8B * 4 bytes ~= 15.2 GB`

However, that is only the weight footprint. Real runtime memory also includes:

- tokenizer/runtime overhead
- Python / FastAPI / torch / transformers process overhead
- temporary buffers
- KV cache
- memory fragmentation and safety margin

That is why a practical POC allocation is larger than the raw weight size. In this POC, `32Gi` memory was chosen as a conservative working value rather than a theoretical minimum.

### CPU is usually a performance-sizing question

CPU core requirements are harder to derive from static model metadata.

Unlike memory, CPU sizing depends heavily on:

- runtime choice (`transformers-cpu` vs `llama-cpp-cpu` vs other stacks)
- dtype / quantization
- latency target
- throughput target
- prompt length and output length
- thread efficiency, NUMA topology, and memory bandwidth

So CPU is less about “can the model load at all?” and more about “how fast do we want it to respond?”

### What to check when estimating requirements

A practical estimation flow looks like this:

1. Check the model card / README for:
   - parameter count
   - model family
   - dtype hints
   - special loading requirements
2. Check the model config and weight format for clues such as:
   - `torch_dtype`
   - safetensors size
   - GGUF vs standard Hugging Face format
3. Estimate the lower-bound weight memory footprint.
4. Add runtime overhead and a safety margin.
5. Pick a conservative starting point for CPU and memory.
6. Validate with a real benchmark.

### Where this information usually comes from

Useful sources include:

- Hugging Face model card / README
- `config.json`
- total weight file size (for example, safetensors size)
- runtime documentation (`transformers`, `llama.cpp`, vLLM CPU backend, etc.)
- real cluster or local benchmark results

### How that applied to this POC

For this POC, the starting point was not derived from a single published “required CPU” value. Instead, it came from:

- model scale: approximately `3.8B`
- dtype: `float32`
- runtime: Hugging Face `transformers` on CPU
- a conservative practical sizing choice for initial success

That led to the initial example values of:

- `cpu: 8`
- `memory: 32Gi`

The benchmark then validated that this shape was workable on a real AKS cluster.

### Practical interpretation

For CPU models, the best sizing guidance usually comes from combining:

- model metadata for the initial estimate
- runtime-specific knowledge for expected overhead
- benchmark measurements for the final answer

In other words:

- **memory** is often estimated first from parameter count and dtype
- **CPU** is usually finalized through performance testing rather than a single static lookup

## Why this usage flow matters

This usage pattern matches the exact intent of the branch:

- **no preset path**
- **no GPU estimator for template-based CPU inference**
- **no CPU auto provisioning**
- **no new runtime abstraction**

It is the narrowest possible path that still proves KAITO can run a CPU model.

---

## Required Code Changes

## 1. CPU image build artifacts

Add:

- `docker/presets/models/tfs-cpu/Dockerfile`
- `presets/workspace/dependencies/requirements-cpu.txt`
- a Makefile target such as `docker-build-kaito-base-cpu`

These changes are data-plane only.

## 2. Minimal controller update

Update workspace target node count logic so template-based inference can use `resource.count` directly instead of the GPU estimator.

The logic should be effectively:

- if `Inference.Template != nil`, use `resource.count`
- if runtime is non-vLLM, use `resource.count`
- only use estimator for the current preset/vLLM GPU path

## 3. Docs and example

Add:

- one CPU custom-model example manifest
- one doc section explaining the POC

The doc must clearly say:

- this is CPU-only
- this is BYO node only
- this is custom model only
- this is a POC, not full CPU support

---

## Deliberate Constraints

This POC is intentionally limited in order to keep change size small.

### Constraint 1: No preset support

Preset support would require:

- compatibility declaration per preset
- image selection branching
- CPU sizing heuristics
- model-specific validation

That is too much for the POC.

### Constraint 2: No llama.cpp in phase 1

Although `llama-cpp-cpu` is valuable for quantized CPU LLM serving, adding it now would introduce:

- a second runtime path
- a second image/runtime contract
- a different model format expectation

That is not minimal.

### Constraint 3: No node auto provisioning

Supporting CPU auto provisioning would require:

- CPU SKU selection logic
- provisioning heuristics
- capacity handling
- possibly scheduler/estimator changes beyond this narrow case

That is also out of scope.

---

## Why this is the right POC shape

This design is intentionally **not elegant**.

It is the right POC because it optimizes for:

- smallest blast radius
- fastest implementation
- easiest validation
- lowest risk to the existing GPU path

The POC reuses as much existing KAITO machinery as possible and only changes what is absolutely necessary.

---

## Acceptance Criteria

This POC is successful if all of the following are true:

1. `kaito-base-cpu` can be built successfully.
2. A custom Workspace can target a labeled CPU node.
3. The Workspace does not go through the GPU estimator path.
4. The CPU model server starts successfully.
5. At least one inference request succeeds.

Anything beyond that should be considered a later enhancement, not part of the POC.

---

## Recommended Next Step After the POC

If this POC works, the next real design discussion can evaluate whether KAITO should later add:

- first-class `runtimeProfile`
- `llama-cpp-cpu`
- selected CPU presets
- CPU-aware validation and provisioning

But those should happen **after** the minimal POC proves the basic CPU path is viable.
