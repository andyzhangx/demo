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
