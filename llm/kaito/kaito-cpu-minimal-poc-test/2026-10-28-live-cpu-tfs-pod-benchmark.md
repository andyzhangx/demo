# 2026-10-28 Qwen 0.5B CPU TFS 实测报告（含连接中断后的补测）

## 结论

**已完成 20 个短请求 + 20 个长请求的有效、唯一成功样本。总计 49 次客户端尝试，不是一次无中断的 40/40 测试。**

- 原始 40 次尝试：31 成功、9 次传输失败；短请求 1–20 全部成功，长请求 1–11 成功。
- 原始 localhost port-forward 在长请求 12 期间中断；长请求 13–20 随后连接被拒绝。原始记录完整保留，未覆盖或隐藏失败。
- 恢复连接后，只对长请求 **12–20** 进行 **9 次串行恢复重试，9/9 成功**。没有重跑任何成功样本，也没有额外预热或自动重试。
- 最终性能样本：短请求 20 条均来自原始窗口；长请求由原始 11 条 + 恢复 9 条组成。每个 prompt 编号只选一个成功响应。
- 短/长平均延迟为 **2.504 / 28.672 秒**；端到端输出吞吐为 **8.39 / 8.93 tokens/s**。
- 相对 2026-10-16 历史 TFS 结果，平均延迟降低 **39.3% / 24.1%**；但 D16s_v5 → D16s_v6、镜像与运行时差异等混杂因素使其**不能归因于单一代码优化**。

### 两个实际请求测量窗口（UTC）

| 阶段 | 首次请求开始 | 最后请求结束 | 尝试 / 成功 |
| --- | --- | --- | ---: |
| 原始测试 | `2026-10-28T13:54:47.088Z` | `2026-10-28T14:01:09.687Z` | 40 / 31 |
| 连接恢复后补测 | `2026-10-28T14:12:43.269Z` | `2026-10-28T14:17:00.649Z` | 9 / 9 |

恢复前后确认同一个 Pod UID、同一个 container ID、同一个 image digest，Running / Ready、restartCount=0，`/health` 均 HTTP 200 Healthy。**原始长请求 55% 的完成比例不是模型可靠性指标**，不能将转发链路失败解释为模型推理错误。也不能将经过重试筛选后的 20/20 长请求成功样本描述为原始运行的 100% 成功率。

本次非流式测试**没有测量 TTFT、TPOT 或纯 decode 速度**；未修改 Kubernetes 工作负载或配置，未向其他 Pod 发送推理请求。

## 1. 测试对象与真实运行时

| 项目 | 实际观测 |
| --- | --- |
| Pod | `qwen-2-5-0-5b-instruct-cpu-tfs-pmfmn-0` |
| Pod UID | `8c709b73-2433-4593-ab26-b40b05a8a22f`（前后一致：True） |
| 节点 | `aks-wsf84b4ccba-32699779-vmss000000` |
| 节点规格 | `Standard_D16s_v6`，16 vCPU，allocatable CPU `15740m` |
| CPU | `INTEL(R) XEON(R) PLATINUM 8573C` |
| Pod image | `mcr.microsoft.com/aks/kaito/kaito-base:0.6.3` |
| Image digest | `sha256:48d7501110feb859b247fa84baa6986e11724739a253da20fc793324e23e424f` |
| 实际服务 | `/workspace/tfs/inference_api.py`，transformers serve 的 `ChatCompletionHandler` |
| API 模型 ID | `/v1/models` 返回 `qwen2.5-0.5b-instruct`，owned_by=`kaito` |
| 响应模型 ID | `qwen/qwen2.5-0.5b-instruct@main` |
| 加载模型路径 | `qwen/qwen2.5-0.5b-instruct` |
| dtype 启动参数 | `--torch_dtype=bfloat16` |
| Pod requests / limits | 均未设置，容器 `resources={}` |
| CPU quota / cpuset | `cpu.max=max 100000`，`cpuset.cpus.effective=0-15` |
| 线程环境 | 服务进程 PID 24 的 `OMP_NUM_THREADS=1`；观测 OS threads=26（不等于 PyTorch intra-op 线程数） |
| Python 包 | torch `2.13.0+cu129`；transformers `5.15.0`；accelerate `1.15.0` |
| 节点软件 | Ubuntu 22.04.5 LTS；kernel 5.15.0-1123-azure；containerd 1.7.36-4；Kubernetes v1.34.1 |

启动命令：

```text
accelerate launch --gpu_ids=all --num_processes=1 --num_machines=1 --machine_rank=0 /workspace/tfs/inference_api.py --pipeline=text-generation --served_model_name=qwen2.5-0.5b-instruct --pretrained_model_name_or_path=qwen/qwen2.5-0.5b-instruct --allow_remote_files --torch_dtype=bfloat16
```

这里不能只看 Pod 名称：本次的确是 TFS/transformers 路径，而非 vLLM。模型由启动路径、API 列表及全部响应中的模型 ID 共同验证。该节点为 CPU SKU，未分配 GPU 资源且容器无 `/dev/nvidia*`；虽然 torch 安装包带 `+cu129` 后缀，这不意味着本次使用 GPU。dtype 仅核验启动配置，未侵入服务进程检查每个 tensor 的 dtype。未在被测容器中加载第二份模型。

`/health` 测试前后均 Healthy（测试后 localhost 转发已失效，改用只读 `kubectl exec` 在同一 Pod 内请求 `127.0.0.1:5000/health`，14:04:55 UTC 返回 HTTP 200）。OpenAPI 暴露 `/v1/chat/completions`、`/v1/responses`、`/v1/models`、`/health` 和 `/metrics`；本次没有为探测 `/v1/completions` 而发送额外生成请求。


## 2. 可复现方法及恢复策略

原始方法与输入：[andyzhangx/demo / kaito-cpu-minimal-poc-test](https://github.com/andyzhangx/demo/tree/master/llm/kaito/kaito-cpu-minimal-poc-test)。请求文件 SHA-256：

- `short-requests.txt`: `c4d1b7e8d51ec6b6130b24212a9848692cf06d7a9cf52d930875d44d2ace2731`
- `long-requests.txt`: `188306b17eff6a237f6ab754bb9aa4db6f055565948f90d2954e812ff1c8f29b`

1. 通过绑定 `127.0.0.1` 的 kubectl port-forward，直接连接指定 Pod 的端口 5000；非 Service，不做负载均衡。
2. 原始窗口串行执行 20 短 + 20 长。恢复窗口在核验同一个健康容器后，**仅串行执行 long 12–20**，每条恢复 payload 与对应原始失败请求逐字段相等。
3. 只去掉行首 `NN. ` 编号，完整保留 `Request N:` 及后续内容。无 system message。
4. `POST /v1/chat/completions`；`model=qwen2.5-0.5b-instruct`；`temperature=0`；`stream=false`；短 `max_tokens=32`、长 `max_tokens=256`。temperature 是请求参数，未修改服务内部采样行为。
5. 并发 1，每条新建 HTTPConnection，超时 600 秒，完整接收后关闭；无生成预热、无自动重试、不排除首个请求。恢复阶段与原始阶段之间存在明显时间间隔，缓存/负载状态未控制。
6. 使用 `time.perf_counter()` 从发送 HTTP 请求前计时至完整非流式响应体接收完；不包含后续 JSON 解析和落盘。记录 UTC 起止、usage、状态和 finish reason；失败记录原样保留。

短 prompt：

```text
Request N: In one short sentence, explain what Kubernetes is. Keep it under 20 words.
```

长 prompt：

```text
Request N: Explain how Kubernetes handles pod creation from API submission to container start. Use a concise but detailed structure with sections for API server, scheduler, kubelet, container runtime, and networking/storage considerations.
```

## 3. 最终有效样本统计

每组 n=20，延迟单位 ms；只统计每个编号选定的成功响应。9 次原始失败没有混入延迟均值，也没有从尝试数中删除。

| 类型 | 成功唯一样本 / 总尝试 | 平均延迟 | P50 | P95 | 最小 | 最大 | 平均输入 tokens | 平均输出 tokens | 平均总 tokens | 端到端输出 tok/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 短请求 | 20 / 20 | 2504.37 | 2513.43 | 2544.46 | 2432.83 | 2586.79 | 51.55 | 21.00 | 72.55 | 8.39 |
| 长请求 | 20 / 29 | 28671.93 | 28673.75 | 29382.41 | 27923.00 | 29771.80 | 71.55 | 256.00 | 327.55 | 8.93 |

- 短请求总计：输入 1031、输出 420、总 tokens 1451；成功请求耗时和 **50.087473 秒**。20 条均 `finish_reason=stop`，每条输出 21 tokens。
- 长请求总计：输入 1431、输出 5120、总 tokens 6551；成功请求耗时和 **573.438591 秒**。20 条均 `finish_reason=length`，每条输出 256 tokens，达到上限不代表自然结束。
- 吞吐公式：`sum(completion_tokens) / sum(successful_request_elapsed_seconds)`，包含连接/转发、服务排队、prefill、生成及响应传输；**不是纯 decode tokens/s**。分母不是跨两个窗口及中间等待的墙钟时间。
- P50/P95 使用 Hyndman–Fan type 7：排序后 `h=(n−1)×p`，在零起始下标 floor(h) 与 ceil(h) 之间线性插值。每组 n=20 时 P95 是第 19/20 个有序样本之间 5% 的插值。
- 完整 20 条长样本平均输入 71.55 tokens，与历史 20 条一致；不是原始仅 11 条成功时的 71.18182。

### 原始传输中断的完整说明

原始长请求 12 在约 14.276 秒后 `RemoteDisconnected`，无 HTTP 状态和响应体；13–20 为 `ConnectionRefusedError`，未到达推理服务。断开的第 12 条是否最终在服务端完成未知，其未观测 token/耗时不计入成功统计。恢复在其结束/断开很久之后启动，没有与之重叠地立即发送第二条长请求。

转发日志为 `error: lost connection to pod`。Pod 后续复查健康、没有重启，这支持传输链路中断的观测，但不足以确定 API server、网络或客户端的具体根因，也不证明中断瞬间服务内部完全无异常。49 次客户端尝试、40 个完整成功响应、9 次原始传输失败均公开保留；这不是持续无故障性能或长期模型可靠性测试。

### 逐条成功样本（共享原始 prompt 编号）

| 类型 | 编号 | 来源 | 延迟 ms | 输入 tokens | 输出 tokens | finish reason |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| short | 01 | 原始 | 2529.58 | 51 | 21 | stop |
| short | 02 | 原始 | 2478.84 | 51 | 21 | stop |
| short | 03 | 原始 | 2490.21 | 51 | 21 | stop |
| short | 04 | 原始 | 2475.49 | 51 | 21 | stop |
| short | 05 | 原始 | 2512.97 | 51 | 21 | stop |
| short | 06 | 原始 | 2516.17 | 51 | 21 | stop |
| short | 07 | 原始 | 2505.00 | 51 | 21 | stop |
| short | 08 | 原始 | 2451.64 | 51 | 21 | stop |
| short | 09 | 原始 | 2432.83 | 51 | 21 | stop |
| short | 10 | 原始 | 2494.02 | 52 | 21 | stop |
| short | 11 | 原始 | 2541.61 | 52 | 21 | stop |
| short | 12 | 原始 | 2542.24 | 52 | 21 | stop |
| short | 13 | 原始 | 2456.58 | 52 | 21 | stop |
| short | 14 | 原始 | 2464.83 | 52 | 21 | stop |
| short | 15 | 原始 | 2517.92 | 52 | 21 | stop |
| short | 16 | 原始 | 2521.21 | 52 | 21 | stop |
| short | 17 | 原始 | 2520.88 | 52 | 21 | stop |
| short | 18 | 原始 | 2586.79 | 52 | 21 | stop |
| short | 19 | 原始 | 2513.90 | 52 | 21 | stop |
| short | 20 | 原始 | 2534.77 | 52 | 21 | stop |
| long | 01 | 原始 | 29771.80 | 71 | 256 | length |
| long | 02 | 原始 | 28867.48 | 71 | 256 | length |
| long | 03 | 原始 | 28983.60 | 71 | 256 | length |
| long | 04 | 原始 | 28691.25 | 71 | 256 | length |
| long | 05 | 原始 | 28520.85 | 71 | 256 | length |
| long | 06 | 原始 | 29361.91 | 71 | 256 | length |
| long | 07 | 原始 | 28325.53 | 71 | 256 | length |
| long | 08 | 原始 | 28668.23 | 71 | 256 | length |
| long | 09 | 原始 | 28488.79 | 71 | 256 | length |
| long | 10 | 原始 | 28679.27 | 72 | 256 | length |
| long | 11 | 原始 | 28120.18 | 72 | 256 | length |
| long | 12 | 恢复重试 1 | 29201.51 | 72 | 256 | length |
| long | 13 | 恢复重试 1 | 28997.78 | 72 | 256 | length |
| long | 14 | 恢复重试 1 | 29179.44 | 72 | 256 | length |
| long | 15 | 恢复重试 1 | 28437.14 | 72 | 256 | length |
| long | 16 | 恢复重试 1 | 28238.36 | 72 | 256 | length |
| long | 17 | 恢复重试 1 | 28267.89 | 72 | 256 | length |
| long | 18 | 恢复重试 1 | 27923.00 | 72 | 256 | length |
| long | 19 | 恢复重试 1 | 28009.39 | 72 | 256 | length |
| long | 20 | 恢复重试 1 | 28705.19 | 72 | 256 | length |

## 4. 与 2026-10-16 TFS 历史实测比较

历史文件名为 `2026-10-15-live-cpu-tfs-pod-benchmark.md`，但标题及测量窗口实际是 2026-10-16。以下对比使用其真实 TFS 结果，不使用更早误标为 TFS 的 vLLM 数值。

| 类型 | 历史平均 ms | 本次平均 ms | 延迟降低 | 历史 / 本次延迟 | 端到端输出 tok/s（历史 → 本次） |
| --- | ---: | ---: | ---: | ---: | ---: |
| 短请求 | 4123.78 | 2504.37 | 39.3% | 1.65× | 5.09 → 8.39 |
| 长请求 | 37772.32 | 28671.93 | 24.1% | 1.32× | 6.78 → 8.93 |

相同点：同一个 20+20 prompt 集、串行 chat endpoint、temperature=0、32/256 token 上限；平均输入 51.55/71.55、输出 21/256 tokens。最终没有缺失 prompt 编号，但长请求是跨两个窗口恢复组成的样本集，不是一个无中断原始轮次。

归因限制：

- 历史 `Standard_D16s_v5`，本次 **`Standard_D16s_v6`**，CPU 代际不同。
- 历史镜像 `andyzhangx/kaito-base-tfs-cpu:0.3.0`，本次 `mcr.microsoft.com/aks/kaito/kaito-base:0.6.3`；本次为 transformers serve `ModelManager` + `ChatCompletionHandler`。历史缺少精确包版本、线程配置、CPU quota 和模型 revision，变量未固定。
- 当前响应模型为 `qwen/qwen2.5-0.5b-instruct@main`，未锁定模型权重 commit，不声称跨日期权重逐字节一致。
- 未控制节点其他负载、共享 CPU 争用、NUMA/线程绑定、缓存冷暖或网络波动，未采集连续 CPU 利用率；没有 CPU requests/limits 不等于独占 16 核。
- 每组只有 20 个成功样本，单 Pod、串行、跨两个时间窗口；不能外推并发吞吐、饱和能力、长期稳定性或统计显著性。历史吞吐只保留两位小数，历史百分位算法未明确，故不直接比较 P95。

## 5. 健康证据、清理与记录完整性

| 阶段 | Pod 核验 UTC | 状态 | Ready | restartCount | /health |
| --- | --- | --- | --- | ---: | --- |
| 恢复前 | `2026-10-28T14:12:41.870Z` | Running | true | 0 | HTTP 200 Healthy，`2026-10-28T14:12:43.178Z` |
| 恢复后 | `2026-10-28T14:17:01.810Z` | Running | true | 0 | HTTP 200 Healthy，`2026-10-28T14:17:00.863Z` |

- 原始测试与恢复前后 Pod UID、container ID、image digest 完全一致，无删除时间；没有重新部署或重启服务。
- 恢复的临时凭据已删除，本任务自己的 port-forward 已停止；没有删除源凭据或其他人的转发。
- 原始 `summary.json`、`requests.jsonl`、`results.json`、40 个逐条结果及原始元数据的 SHA-256 全部保持不变。原始部分完成报告另存为 `report-initial.md`，本报告是恢复后的最终版本。
- 没有修改 Kubernetes 资源。公开报告和统计文件不包含凭据、私有 API 地址或临时凭据文件路径。

## 6. 报告与统计文件

- [2026-10-28-live-cpu-tfs-pod-benchmark.md](2026-10-28-live-cpu-tfs-pod-benchmark.md)：本报告。
- [2026-10-28-live-cpu-tfs-pod-benchmark-summary.json](2026-10-28-live-cpu-tfs-pod-benchmark-summary.json)：完整精度统计、40 个成功样本的逐条指标及来源、9 次原始失败记录、两个测量窗口和环境核验信息。
- [short-requests.txt](short-requests.txt)、[long-requests.txt](long-requests.txt)：原始请求集，未修改。

原始完整请求/响应、恢复记录、环境采集和校验记录保留在本地测试 artifacts 中；未将凭据、临时访问文件或完整集群对象上传到仓库。
