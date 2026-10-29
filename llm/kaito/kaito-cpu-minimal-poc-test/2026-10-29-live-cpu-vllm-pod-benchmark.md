# Gemma 4 E4B CPU vLLM 实测（2026-10-29）

## 结论与边界

- 精确目标：`default/gemma-4-e4b-it-cpu-vllm-lq449-0`；实际加载 **`google/gemma-4-e4b-it`**，不是历史报告中的 Qwen。启动日志、Pod command、CPU 包版本以及全部响应的 served-model alias 相互核对。
- 沿用本目录原始 **20 short + 20 long** prompts，先 short 后 long 串行执行；共 **40 次请求、40 次 HTTP/API 成功、0 次失败、0 次重试**。没有重启测试序列、筛除慢请求或额外生成预热。
- short 平均 **3,539.01 ms**，long 平均 **27,438.26 ms**；端到端输出吞吐分别 **9.04 / 9.33 tokens/s**。
- **HTTP/API 成功不等于回答质量达标。** 本次所有输出均 `finish_reason=length`：short 为 32 tokens，long 为 256 tokens。实际 `content` 出现 planning/thinking 风格文字，并在预算处截断；独立 `reasoning` 字段为 null。短请求并未给出满足“20 words 以内一句话”的最终答案，长请求也不能视为完整解释。此次是当前配置下的生成/延迟测量，不能宣称 40 个有效最终答案。
- 测试前后同一 Pod UID、同一 containerID，Running/Ready，restartCount **0 → 0**；health/models 均 HTTP 200。没有修改 Pod、StatefulSet、InferenceSet 或服务配置。

## 运行环境（从实机读取）

| 项目 | 实测值 |
|---|---|
| Azure VM SKU | `Standard_D16s_v6` |
| CPU | `INTEL(R) XEON(R) PLATINUM 8573C`，16 个逻辑 CPU；affinity/cpuset `0-15` |
| Node CPU capacity / allocatable | `16` / `15740m` |
| Node memory capacity / allocatable | `65837840Ki` / `60564240Ki`（约 62.79 / 57.76 GiB） |
| OS / kernel / kubelet | Ubuntu 22.04.5 LTS / `5.15.0-1123-azure` / `v1.34.1` |
| Container runtime | `containerd 1.7.36-4`，amd64 |
| Image | `andyzhangx/kaito-base-vllm-cpu:0.3.0` |
| Image digest | `sha256:cab425602c6ed581a0240c558ba94f67c5cc0ed9d0933e376a0bb800d34d8962` |
| Python packages | vLLM `0.25.1+cpu`，PyTorch `2.11.0+cpu`，Transformers `5.13.1`，FastAPI `0.136.3`，Uvicorn `0.51.0` |
| Model / architecture | `google/gemma-4-e4b-it` / `Gemma4ForConditionalGeneration` |
| dtype / quantization / device | `bfloat16` / `None` / `cpu`；未发现 `/dev/nvidia*` |
| Context / parallelism | `max_model_len=2048`；TP/PP/DP 都为 1 |
| Pod resources / CPU quota | `resources: {}`（未设 requests/limits）；`cpu.max=max 100000` |
| Thread observation | API Python 进程 93 threads；这不等于 93 个计算核。API env 仅观察到 `VLLM_TARGET_DEVICE=cpu`，未设 OMP/MKL 线程数；启动日志显示 `VLLM_CPU_OMP_THREADS_BIND=auto` |
| Caching | prefix caching 和 chunked prefill 均开启；未清空缓存，既有服务已运行，不是冷启动测试 |
| Model revision | runtime `revision=None`；未记录不可变的模型仓库 commit，不能声称权重版本已钉死 |

当前容器完整启动命令（测试未改动）：

```sh
python3 /workspace/vllm/inference_api.py --max-model-len=2048 --download-dir=/workspace/weights --load_format=auto --dtype=bfloat16 --compilation-config.pass_config.fuse_allreduce_rms=False --model=google/gemma-4-e4b-it --tokenizer_mode=auto --served-model-name=gemma-4-e4b-it-cpu-vllm --config_format=auto --trust-remote-code --enable-auto-tool-choice --kv-events-config='{"enable_kv_cache_events":true}' --kaito-kv-cache-cpu-memory-utilization=0 --tool-call-parser=gemma4 --chat-template=/workspace/chat_templates/tool-chat-gemma4.jinja --reasoning-parser=gemma4 --gpu-memory-utilization=0.8
```

`--gpu-memory-utilization=0.8` 是当前 CPU vLLM 也使用的内存预算配置，并不表示使用 GPU。`--kaito-kv-cache-cpu-memory-utilization=0` 在当前 wrapper 下保留 vLLM CPU KV-cache 自动配置，不代表不分配 KV cache。启动日志记录模型加载约 24.11 GiB；这只是启动时记录，不是本次压测的峰值 RSS。日志中通用标签 “GPU KV cache size: 425,043 tokens” 也不是 GPU 存在的证据。测试未测 CPU 利用率、峰值内存或功耗。

## 请求与统计方法

- 输入：[short-requests.txt](short-requests.txt)、[long-requests.txt](long-requests.txt)，来源 commit `6d9aa6bcff9c382d8128b06d79a7c191ca2f3c3e`。文件 SHA-256 分别为 `c4d1b7e8d51ec6b6130b24212a9848692cf06d7a9cf52d930875d44d2ace2731`、`188306b17eff6a237f6ab754bb9aa4db6f055565948f90d2954e812ff1c8f29b`。
- 只剥离文件行首 `NN. `，保留 `Request N: ` 及全部剩余文字；各文件 20 行，逐项与实际 payload 校验。
- short 模板：`Request N: In one short sentence, explain what Kubernetes is. Keep it under 20 words.`
- long 模板：`Request N: Explain how Kubernetes handles pod creation from API submission to container start. Use a concise but detailed structure with sections for API server, scheduler, kubelet, container runtime, and networking/storage considerations.`
- Pod 定向 port-forward 后调用 `/v1/chat/completions`；不通过可能负载均衡到其他 Pod 的 Service。每次新建 HTTP 连接，concurrency=1；单个 user message，无 system message；`model=gemma-4-e4b-it-cpu-vllm`，`temperature=0`，`stream=false`，short `max_tokens=32` / long `max_tokens=256`。其余采样参数保持服务默认；未传 thinking-disable 或 chat-template override。
- 单请求 timeout 600 秒；无自动重试、无恢复重试、无生成预热（只做 health/models 探测）。每个返回立即落盘，记录所有尝试，包括错误字段。
- 时间范围（UTC）：**2026-10-29T05:37:30.189Z → 2026-10-29T05:48:00.278Z**。记录落盘/复制存在请求间间隙，整个批次墙钟时间不是请求延迟之和。
- latency 用 monotonic `perf_counter` 从 HTTP send 到非流式响应正文全部读完计时；包含客户端/port-forward 传输、服务排队、prefill、生成，不含后续 JSON parse 与证据落盘。
- mean 为算术平均；P50/P95 使用 Hyndman–Fan type 7：排序后 `h=(n-1)*p`，相邻样本线性插值。每组只有 20 次，P95 不代表稳定长尾 SLA。
- **端到端输出 tokens/s = 成功响应 completion_tokens 总和 / 成功请求 elapsed_seconds 总和**，不是各请求吞吐的简单平均，也不是整个批次墙钟吞吐，更不是纯 decode tokens/s。非流式测试未测 TTFT、逐 token 间隔或独立 prefill/decode 耗时。

## 聚合结果

| 组 | 成功/尝试 | mean ms | P50 ms | P95 ms | min ms | max ms | prompt tokens 总数/均值 | output tokens 总数/均值 | 端到端 output tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| short | 20/20 | 3539.01 | 3519.80 | 3690.68 | 3410.41 | 3942.14 | 711/35.55 | 640/32.00 | 9.0421 |
| long | 20/20 | 27438.26 | 27288.47 | 28064.81 | 27108.95 | 28327.63 | 1131/56.55 | 5120/256.00 | 9.3300 |

## 每请求结果

全部尝试均保留；更高精度耗时、UTC 起止时间、完整 prompt/响应 content、response ID、模型标识、tokens、error 与原始记录 SHA-256 见 [summary JSON](2026-10-29-live-cpu-vllm-pod-benchmark-summary.json)。

| 组 | 编号 | HTTP | 成功 | latency ms | prompt tokens | completion tokens | finish | error |
|---|---:|---:|---|---:|---:|---:|---|---|
| short | 01 | 200 | True | 3529.149 | 35 | 32 | length | — |
| short | 02 | 200 | True | 3539.129 | 35 | 32 | length | — |
| short | 03 | 200 | True | 3456.299 | 35 | 32 | length | — |
| short | 04 | 200 | True | 3455.513 | 35 | 32 | length | — |
| short | 05 | 200 | True | 3556.538 | 35 | 32 | length | — |
| short | 06 | 200 | True | 3489.523 | 35 | 32 | length | — |
| short | 07 | 200 | True | 3515.365 | 35 | 32 | length | — |
| short | 08 | 200 | True | 3485.540 | 35 | 32 | length | — |
| short | 09 | 200 | True | 3524.243 | 35 | 32 | length | — |
| short | 10 | 200 | True | 3942.144 | 36 | 32 | length | — |
| short | 11 | 200 | True | 3677.449 | 36 | 32 | length | — |
| short | 12 | 200 | True | 3498.827 | 36 | 32 | length | — |
| short | 13 | 200 | True | 3591.133 | 36 | 32 | length | — |
| short | 14 | 200 | True | 3483.467 | 36 | 32 | length | — |
| short | 15 | 200 | True | 3455.375 | 36 | 32 | length | — |
| short | 16 | 200 | True | 3410.411 | 36 | 32 | length | — |
| short | 17 | 200 | True | 3527.530 | 36 | 32 | length | — |
| short | 18 | 200 | True | 3597.592 | 36 | 32 | length | — |
| short | 19 | 200 | True | 3502.990 | 36 | 32 | length | — |
| short | 20 | 200 | True | 3542.077 | 36 | 32 | length | — |
| long | 01 | 200 | True | 27274.184 | 56 | 256 | length | — |
| long | 02 | 200 | True | 27226.720 | 56 | 256 | length | — |
| long | 03 | 200 | True | 28327.633 | 56 | 256 | length | — |
| long | 04 | 200 | True | 27108.952 | 56 | 256 | length | — |
| long | 05 | 200 | True | 27435.156 | 56 | 256 | length | — |
| long | 06 | 200 | True | 27236.436 | 56 | 256 | length | — |
| long | 07 | 200 | True | 27178.109 | 56 | 256 | length | — |
| long | 08 | 200 | True | 27600.323 | 56 | 256 | length | — |
| long | 09 | 200 | True | 27284.663 | 56 | 256 | length | — |
| long | 10 | 200 | True | 28050.972 | 57 | 256 | length | — |
| long | 11 | 200 | True | 27287.022 | 57 | 256 | length | — |
| long | 12 | 200 | True | 27592.850 | 57 | 256 | length | — |
| long | 13 | 200 | True | 27475.140 | 57 | 256 | length | — |
| long | 14 | 200 | True | 27942.749 | 57 | 256 | length | — |
| long | 15 | 200 | True | 27283.807 | 57 | 256 | length | — |
| long | 16 | 200 | True | 27207.761 | 57 | 256 | length | — |
| long | 17 | 200 | True | 27289.922 | 57 | 256 | length | — |
| long | 18 | 200 | True | 27328.303 | 57 | 256 | length | — |
| long | 19 | 200 | True | 27372.486 | 57 | 256 | length | — |
| long | 20 | 200 | True | 27262.055 | 57 | 256 | length | — |

## 前后健康核验

| 项目 | 测试前 | 测试后 |
|---|---|---|
| 观察时间 UTC | 2026-10-29T05:35:57.961690+00:00 | 2026-10-29T05:48:01.339945+00:00 |
| Pod UID | `ffc36263-24e3-4601-a50a-ba1269ef446f` | `ffc36263-24e3-4601-a50a-ba1269ef446f` |
| Phase / Ready | Running / True | Running / True |
| restartCount | 0 | 0 |
| Container start UTC | 2026-10-28T14:22:47Z | 2026-10-28T14:22:47Z |
| `/health` HTTP | 200 | 200 |
| `/v1/models` HTTP | 200 | 200 |

同一 containerID、node 和容器配置；无 deletionTimestamp。零重启与前后探测成功说明这段测试期间未观察到容器重启，不等于长期可用性承诺，也不是全程资源监控。

## 与历史 Qwen/TFS 报告的关系

保留 [2026-10-28 Qwen CPU TFS 报告](2026-10-28-live-cpu-tfs-pod-benchmark.md) 及其原始失败/恢复说明不变。该测试 short 平均 2,504.37 ms、输出 21 tokens，long 平均 28,671.93 ms、输出 256 tokens，端到端输出吞吐 8.39 / 8.93 tokens/s；49 次尝试含 9 次传输失败与显式恢复，不能当作连续 40/40。

本次 Gemma 与历史 Qwen **模型、tokenizer、runtime/image、chat template、输出内容及短输出长度都不同**。同为 D16s_v6 也不代表相同节点负载/缓存状态。历史 10 月 15–16 日的 D16s_v5 比较还有硬件代际差异。长组同为 256 output tokens 只能减少长度差异，不能消除模型/推理行为的混杂因素。因此这里只并列数据，不将差异归因于 vLLM 对 TFS 的提升、代码优化或宣称同等回答质量。

## 可审计性与未覆盖范围

JSON 包含每次请求的原始响应 content；可直接看到计划式文字与截断，而不是只信 HTTP 200。完整 40 个 raw request/response、JSONL、请求脚本、前后健康快照、运行时版本、启动日志摘录和独立统计核验保存在本次本地 artifacts；JSON 提供原始记录和输入哈希。发布内容不含 kubeconfig、认证信息或私有集群端点。

本次仅覆盖单 Pod、串行、固定 40 次请求；不覆盖并发容量、冷启动、长期稳定性、回答质量评分、TTFT、纯 decode 速率、峰值内存或成本结论。未为了修复 thinking/截断而改变配置或追加请求。
