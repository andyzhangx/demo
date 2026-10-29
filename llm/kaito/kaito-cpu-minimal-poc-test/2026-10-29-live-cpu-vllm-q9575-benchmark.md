# Gemma q9575 CPU vLLM 实测报告（2026-10-29）

- 测试对象：`default/gemma-4-e4b-it-cpu-vllm-q9575-0`，实际模型 **google/gemma-4-e4b-it**。
- 测试时间（UTC）：2026-10-29T14:37:24.142Z 至 2026-10-29T14:48:10.166Z。
- 完成 20 个短请求 + 20 个长请求，串行 concurrency=1，成功 40/40，无自动重试、无额外生成预热。
- 未修改、重启 Pod/StatefulSet/配置；本报告与机器可读统计按用户要求发布；集群访问脚本和凭据不发布。

## 1. 结果

| 请求组 | 成功/尝试 | 平均延迟 s | P50 s | P95 s | 最小–最大 s | 输出 tokens | E2E 输出 tokens/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| short | 20/20 | 4.09988 | 3.60408 | 4.58526 | 3.53210–12.85050 | 640 | 7.80510 |
| long | 20/20 | 27.98786 | 27.94875 | 28.51294 | 27.47205–28.60379 | 5120 | 9.14682 |

延迟从客户端发起 HTTP POST 前计时，到完整响应读取结束；每次新建本地 HTTP 连接，经 kubectl port-forward。E2E 输出吞吐 = Σ completion_tokens / Σ请求延迟；包括输入处理、排队、生成、传输，不是纯 decode TPS，也未测 TTFT。P50/P95 使用排序后 `(n−1)×p` 位置线性插值，保留第一条请求，不剔除异常值。

第一条短请求延迟 **12.85050s**；未单独预热，不能无证据把它归因于某种冷启动或编译过程。

## 2. 与此前 lq449 同方法测试比较

| 组 | 原平均 s → 本次 s | 原 P95 s → 本次 s | 原 E2E tokens/s → 本次 | 平均延迟变化 | E2E 吞吐变化 |
|---|---:|---:|---:|---:|---:|
| short | 3.53901 → 4.09988 | 3.69068 → 4.58526 | 9.04206 → 7.80510 | +15.85% | -13.68% |
| long | 27.43826 → 27.98786 | 28.06481 → 28.51294 | 9.33004 → 9.14682 | +2.00% | -1.96% |

两次模型名相同、提示词文件 SHA256 和每条请求设置完全一致，但不是严格受控 A/B：
- 镜像 `andyzhangx/kaito-base-vllm-cpu:0.3.0` → `:0.3.1`；vLLM `0.25.1+cpu` → `0.30.0+cpu`；PyTorch `2.11.0+cpu` → `2.13.0+cpu`；Transformers `5.13.1` → `5.17.0`。
- 节点 `previous-node (identity omitted)` → `current-node (identity omitted)`，同为 Standard_D16s_v6 / Intel Xeon Platinum 8573C / 16 vCPU。不同节点、既有负载及缓存状态未控制。
- 原命令显式含 `--gpu-memory-utilization=0.8 --kaito-kv-cache-cpu-memory-utilization=0`；本次未显式带这两个参数，也未显式带 `--cpu-offload-gb`。本次容器源码显示 CPU parser 默认 gpu_memory_utilization=0.8、cpu_offload_gb=0；启动日志明确跳过自动 NIXL/LMCache offload/sidecar。CPU 原生 KV cache 仍启用，不能把“不做 GPU→CPU offload”等同于“禁用 CPU KV cache”。
- 本次为 `exec python3` 且新增 `--shutdown-timeout=50`；其他完整命令、资源及镜像摘要见下文；公开 JSON 保留测试参数与统计。
- 两次日志均 model revision=main，未核实下载权重对应的具体不可变 commit；因此不把差异归因于单一 vLLM 版本、offload 或模型权重变化。

## 3. 环境与完整配置

- 运行时：`{'vllm': '0.30.0+cpu', 'torch': '2.13.0+cpu', 'transformers': '5.17.0', 'accelerate': 'No package metadata was found for accelerate', 'fastapi': '0.136.3', 'uvicorn': '0.53.0'}`。
- CPU：['INTEL(R) XEON(R) PLATINUM 8573C']，可见 CPU=16，affinity=0–15；cgroup cpu.max=`max 100000`（无 CPU quota）。
- Pod resources={}，未配置 CPU/内存 requests 或 limits；这不保证独占整个节点。节点 capacity=16 CPU / 约 62.8 GiB，allocatable=15.74 CPU / 约 57.8 GiB。
- CPU 运行：VLLM_TARGET_DEVICE=cpu，无 /dev/nvidia*；启动日志 dtype=bfloat16、device_config=cpu、max_seq_len=2048、tensor_parallel_size=1。
- 日志启用 prefix caching、chunked prefill；模型加载占 23.93 GiB；CPU KV cache 423,969 tokens（容量，不是实测并发吞吐）。源代码只读提取在短组完成后、长组开始附近执行，未导入运行引擎或修改文件；这类观测开销也未从请求延迟中扣除。
- 镜像摘要：`docker.io/andyzhangx/kaito-base-vllm-cpu@sha256:5a22f2daec54902c156ec3ce4bce7da31b50858b9d06c33705e4f46e92810627`。
- 原镜像摘要：`docker.io/andyzhangx/kaito-base-vllm-cpu@sha256:cab425602c6ed581a0240c558ba94f67c5cc0ed9d0933e376a0bb800d34d8962`。

完整容器 command：
```sh
exec python3 /workspace/vllm/inference_api.py --tokenizer_mode=auto --dtype=bfloat16 --enable-auto-tool-choice --chat-template=/workspace/chat_templates/tool-chat-gemma4.jinja --reasoning-parser=gemma4 --served-model-name=gemma-4-e4b-it-cpu-vllm --compilation-config.pass_config.fuse_allreduce_rms=False --load_format=auto --trust-remote-code --download-dir=/workspace/weights --shutdown-timeout=50 --config_format=auto --tool-call-parser=gemma4 --max-model-len=2048 --kv-events-config='{"enable_kv_cache_events":true}' --model=google/gemma-4-e4b-it
```

## 4. 方法、提示词和质量限制

请求 body：model=`gemma-4-e4b-it-cpu-vllm`，一个 user message，temperature=0，stream=false；short max_tokens=32，long max_tokens=256；客户端 timeout=600s，每组顺序编号 1–20，短组先跑。仅移除文本文件 `NN. ` 前缀，保留 `Request N: `。

短请求模板：
> Request 1: In one short sentence, explain what Kubernetes is. Keep it under 20 words.

长请求模板：
> Request 1: Explain how Kubernetes handles pod creation from API submission to container start. Use a concise but detailed structure with sections for API server, scheduler, kubelet, container runtime, and networking/storage considerations.

- short：finish_reason 分布 `{'length': 20}`；length 截断 20/20，非空 content 20，非空独立 reasoning 字段 0。
- long：finish_reason 分布 `{'length': 20}`；length 截断 20/20，非空 content 20，非空独立 reasoning 字段 0。

API 成功不等于完成用户答案。输出可能把计划/思考文字放在 content 内，即使 reasoning=null / reasoning_tokens=0，也不能据此称为没有思考。原始输出均保存；达到上限的响应按截断处理，不能据此评估完整回答质量。

第一条短请求 content：
```text
The user wants a very short, one-sentence explanation of Kubernetes, strictly under 20 words.

Plan: Define Kubernetes simply as a container orchestration system
```

## 5. 运行完整性和清理

- Pod UID 前后相同（不公开具体 ID）；containerID / node / imageID / command / resources 相同。
- 前后 Ready=True，restartCount=[0]；/health、/v1/models 前后均 HTTP 200，model root 一致。
- 自己创建的临时 0600 kubeconfig 与 access-path 已删除；仅停止本次自己的 localhost port-forward。未存储或发布集群凭据。
- 所有请求原始 HTTP 状态、完整 response_text、解析响应、usage、finish_reason、elapsed 和错误保存在逐条 JSON 及 requests.jsonl；独立校验结果已逐条独立复算通过；公开摘要包含全部请求与响应。

## 6. 逐条结果

| 组 | 序号 | HTTP | 延迟 s | prompt tokens | output tokens | finish_reason |
|---|---:|---:|---:|---:|---:|---|
| short | 1 | 200 | 12.85050 | 35 | 32 | ['length'] |
| short | 2 | 200 | 3.60850 | 35 | 32 | ['length'] |
| short | 3 | 200 | 3.62819 | 35 | 32 | ['length'] |
| short | 4 | 200 | 3.60921 | 35 | 32 | ['length'] |
| short | 5 | 200 | 3.54901 | 35 | 32 | ['length'] |
| short | 6 | 200 | 3.59138 | 35 | 32 | ['length'] |
| short | 7 | 200 | 3.57043 | 35 | 32 | ['length'] |
| short | 8 | 200 | 3.54778 | 35 | 32 | ['length'] |
| short | 9 | 200 | 3.60471 | 35 | 32 | ['length'] |
| short | 10 | 200 | 3.57049 | 36 | 32 | ['length'] |
| short | 11 | 200 | 3.61358 | 36 | 32 | ['length'] |
| short | 12 | 200 | 3.60346 | 36 | 32 | ['length'] |
| short | 13 | 200 | 3.53210 | 36 | 32 | ['length'] |
| short | 14 | 200 | 3.58479 | 36 | 32 | ['length'] |
| short | 15 | 200 | 4.15024 | 36 | 32 | ['length'] |
| short | 16 | 200 | 3.91823 | 36 | 32 | ['length'] |
| short | 17 | 200 | 3.58229 | 36 | 32 | ['length'] |
| short | 18 | 200 | 3.65143 | 36 | 32 | ['length'] |
| short | 19 | 200 | 3.63645 | 36 | 32 | ['length'] |
| short | 20 | 200 | 3.59484 | 36 | 32 | ['length'] |
| long | 1 | 200 | 27.98439 | 56 | 256 | ['length'] |
| long | 2 | 200 | 27.87111 | 56 | 256 | ['length'] |
| long | 3 | 200 | 28.25362 | 56 | 256 | ['length'] |
| long | 4 | 200 | 27.85056 | 56 | 256 | ['length'] |
| long | 5 | 200 | 27.87232 | 56 | 256 | ['length'] |
| long | 6 | 200 | 27.87549 | 56 | 256 | ['length'] |
| long | 7 | 200 | 27.91650 | 56 | 256 | ['length'] |
| long | 8 | 200 | 27.47205 | 56 | 256 | ['length'] |
| long | 9 | 200 | 27.64788 | 56 | 256 | ['length'] |
| long | 10 | 200 | 28.20410 | 57 | 256 | ['length'] |
| long | 11 | 200 | 28.08542 | 57 | 256 | ['length'] |
| long | 12 | 200 | 27.98515 | 57 | 256 | ['length'] |
| long | 13 | 200 | 28.60379 | 57 | 256 | ['length'] |
| long | 14 | 200 | 28.50816 | 57 | 256 | ['length'] |
| long | 15 | 200 | 27.85372 | 57 | 256 | ['length'] |
| long | 16 | 200 | 27.78662 | 57 | 256 | ['length'] |
| long | 17 | 200 | 28.06476 | 57 | 256 | ['length'] |
| long | 18 | 200 | 27.98101 | 57 | 256 | ['length'] |
| long | 19 | 200 | 28.18912 | 57 | 256 | ['length'] |
| long | 20 | 200 | 27.75137 | 57 | 256 | ['length'] |

## 7. 已发布证据

- [2026-10-29-live-cpu-vllm-q9575-benchmark-summary.json](2026-10-29-live-cpu-vllm-q9575-benchmark-summary.json)：统计、比较、全部40条原始请求和响应、延迟及token用量。
- [short-requests.txt](short-requests.txt) / [long-requests.txt](long-requests.txt)：与先前测试相同的提示词；SHA256见JSON。
- 集群检查原始文件和测试脚本仅保留本地，未上传。Pod身份、健康、清理与全部统计已独立复核通过。
