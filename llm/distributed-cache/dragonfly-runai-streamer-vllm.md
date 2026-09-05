# Dragonfly + runai_streamer + vLLM 推荐链路

## 背景

随着 LLM 模型文件快速变大（几十 GB 到上百 GB，甚至 TB 级），在 Kubernetes 集群中把同一份模型分发到大量 GPU 节点，已经变成 AI 推理/训练平台里的一个核心瓶颈。

典型问题包括：

- 每个节点都直接从 Hugging Face / ModelScope / 对象存储拉模型
- 源站或对象存储被瞬时 fan-out 打爆
- 公网 / 跨 AZ / 跨 region 流量成本高
- GPU 节点冷启动慢
- 模型更新时 rollout 很慢

## 结论

这三个组件分别解决不同层的问题：

- **Dragonfly**：解决**集群级模型分发**问题
- **runai_streamer**：解决**单节点模型加载到 GPU** 的效率问题
- **vLLM**：负责模型推理服务

推荐组合：

- **Dragonfly 负责把模型高效分发到每个节点本地**
- **runai_streamer 负责从本地模型文件高并发加载到 GPU memory**
- **vLLM 负责 serving**

---

## 推荐链路图

```text
                    ┌──────────────────────────────┐
                    │   Hugging Face / ModelScope  │
                    │   or S3 / GCS / Azure Blob   │
                    └──────────────┬───────────────┘
                                   │
                                   │  首次回源 / 少量回源
                                   ▼
                        ┌──────────────────────┐
                        │  Dragonfly Seed Peer │
                        │   (or first peer)    │
                        └─────────┬────────────┘
                                  │
                    piece-based   │   P2P micro-task distribution
                    streaming     │   边下边分享
                                  ▼
         ┌──────────────────────────────────────────────────────────┐
         │              Dragonfly P2P Mesh in K8s Cluster          │
         │                                                          │
         │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
         │   │ GPU Node A   │   │ GPU Node B   │   │ GPU Node N   │ │
         │   │ dfdaemon     │◄─►│ dfdaemon     │◄─►│ dfdaemon     │ │
         │   │ peer cache   │   │ peer cache   │   │ peer cache   │ │
         │   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘ │
         └──────────┼──────────────────┼──────────────────┼──────────┘
                    │                  │                  │
                    │ 落本地模型目录     │ 落本地模型目录     │ 落本地模型目录
                    ▼                  ▼                  ▼
         ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
         │ local NVMe /   │ │ local NVMe /   │ │ local NVMe /   │
         │ hostPath / PVC │ │ hostPath / PVC │ │ hostPath / PVC │
         └──────┬─────────┘ └──────┬─────────┘ └──────┬─────────┘
                │                  │                  │
                │ 本地 safetensors │ 本地 safetensors │
                ▼                  ▼                  ▼
       ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
       │ runai_streamer  │ │ runai_streamer  │ │ runai_streamer  │
       │ concurrent read │ │ concurrent read │ │ concurrent read │
       │ CPU buf -> GPU  │ │ CPU buf -> GPU  │ │ CPU buf -> GPU  │
       └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
                │                   │                   │
                ▼                   ▼                   ▼
          ┌───────────┐       ┌───────────┐       ┌───────────┐
          │   vLLM    │       │   vLLM    │       │   vLLM    │
          │ API Pod   │       │ Worker    │       │ Worker    │
          └─────┬─────┘       └─────┬─────┘       └─────┬─────┘
                │                   │                   │
                └───────────────────┴───────────────────┘
                            Model Ready / Serving
```

---

## 组件分工

### 1. Dragonfly 做什么

Dragonfly 是一个 P2P 分发系统，适合把大文件、镜像、OCI Artifact、AI 模型、数据集分发到大量节点。

它的核心能力：

- 把大文件切成多个 piece / micro-task
- 第一个节点或 seed peer 从源站回源
- **还没下完整个文件就开始把已下载 piece 分发给其他 peer**
- 后续节点从多个 peer 并发拉取 piece
- 在集群内形成 P2P mesh，显著减少回源流量

对于 LLM 模型，这意味着：

- 不需要每个 GPU 节点都直接打 Hugging Face / ModelScope
- 大部分流量会变成集群内部流量
- 节点越多，P2P 的收益越大

### 2. runai_streamer 做什么

runai_streamer 是一个高性能权重加载器，目标是把 safetensors 文件更高效地从：

- 本地文件
- S3
- GCS
- Azure Blob

加载到 CPU buffer，再并发转移到 GPU memory。

它优化的是：

- tensor 读取并发度
- CPU buffer 使用
- 数据进入 GPU 的 pipeline
- 大模型冷启动时间

### 3. vLLM 做什么

vLLM 负责：

- 模型初始化
- tokenizer / engine setup
- serving API
- request scheduling
- KV cache / inference execution

---

## 为什么推荐 Dragonfly + runai_streamer 组合

因为两者优化的是**不同层**。

### Dragonfly 优化的是“分发”

关注的问题：

- 同一个模型如何快速出现在 10 / 100 / 200 个节点上
- 如何降低回源、带宽和对象存储压力
- 如何降低 rollout 的长尾

### runai_streamer 优化的是“加载”

关注的问题：

- 模型已经在本地或对象存储了，怎么更快把 safetensors 读进 GPU
- 如何降低单节点 cold start
- 如何提升多文件、多 tensor 并发读取效率

所以最合理的链路是：

```text
Model Hub / Object Store
        ↓
    Dragonfly
  (cluster-wide P2P)
        ↓
   node-local cache
        ↓
  runai_streamer
 (fast local load)
        ↓
      vLLM
```

---

## Dragonfly 是否原生支持 runai_streamer

**目前看并不是原生一体化支持。**

当前更像是：

- Dragonfly 原生支持 `hf://`、`modelscope://` 以及多种对象存储后端
- runai_streamer / vLLM 文档里主要支持：
  - 本地路径
  - `s3://`
  - `gs://`
  - `az://`

所以更现实的用法是：

1. 用 Dragonfly 把模型分发到节点本地目录
2. 再让 vLLM 使用 `--load-format runai_streamer` 从本地目录加载

而不是指望 runai_streamer 直接读 Dragonfly 的 `hf://` / `modelscope://`。

---

## 推荐落地方式

### 方案 A：最推荐

```text
HF / ModelScope / Blob / S3
          ↓
       Dragonfly
          ↓
  Node local NVMe / hostPath
          ↓
  vLLM --load-format runai_streamer
          ↓
        Serving
```

适合：

- GPU 节点较多
- 模型体积很大
- 同一模型会在很多节点重复部署
- 希望降低源站 / 对象存储压力

### 方案 B：先只接 Dragonfly

```text
HF / ModelScope / Blob / S3
          ↓
       Dragonfly
          ↓
  Node local model dir
          ↓
      vLLM default loader
```

适合：

- 当前瓶颈明确在“分发”而不在“加载”
- 想先降低复杂度
- 想先验证 Dragonfly 在 rollout 上的收益

### 方案 C：只用 runai_streamer

```text
Object Storage
      ↓
runai_streamer
      ↓
    vLLM
```

适合：

- 节点数量不多
- 模型已经稳定放在对象存储
- 主要问题是单节点冷启动，而不是大规模 fan-out

---

## 在 Kubernetes / AI inference 平台中的推荐时序

```text
1. 调度 GPU 节点
2. Dragonfly 从源站回源一次
3. Dragonfly P2P 把模型分发到各节点本地目录
4. 推理 Pod 启动
5. runai_streamer 从本地 safetensors 并发加载到 GPU
6. vLLM ready
```

---

## 和共享存储方案的对比

### 相比 NFS / BlobFuse / 共享文件系统

优势：

- 不把所有推理读流量集中到单个共享存储
- 本地盘更适合大模型高吞吐读取
- 避免 shared storage 热点问题

代价：

- 每个节点需要有足够本地容量
- 首次分发仍然需要一次回源

### 相比预烘焙超大镜像

优势：

- 模型更新不需要重建超大镜像
- 模型与 serving runtime 解耦
- rollout 更灵活

代价：

- 启动链路更复杂
- 需要额外模型缓存管理

---

## 什么时候收益最大

Dragonfly 的收益在这些场景最明显：

- 同一模型在很多 GPU 节点上并发部署
- 模型来自 Hugging Face / ModelScope / 公有对象存储
- 模型大于几十 GB
- 模型更新频繁，或者自动扩容频繁
- 节点本地盘性能不错（尤其是 NVMe）

runai_streamer 的收益在这些场景最明显：

- safetensors 文件很多 / 很大
- 模型加载时间已经接近启动瓶颈
- 本地文件系统很快，但单机加载还想继续压缩

---

## 对 KAITO / workspace 类场景的建议

如果是 workspace / inference CRD 驱动的模型启动链路，推荐这样接：

```text
Workspace Created
   ↓
Model download/init job
   ↓
Dragonfly dfget 拉到 node-local model dir
   ↓
Inference pod starts
   ↓
vLLM --load-format runai_streamer --model /models/xxx
```

也就是说：

- **download/init 阶段** 插 Dragonfly
- **serving/load 阶段** 继续用 runai_streamer

这种分层最清晰，也最容易排查问题。

---

## 需要注意的限制

Dragonfly 解决的是**模型分发问题**，不是全部冷启动问题。

它不能直接解决：

- vLLM 本身初始化时间
- 权重格式不兼容
- tokenizer / engine 构建时间
- GPU kernel / backend 问题
- 显存分配问题

runai_streamer 也不能解决：

- 100 个节点同时回源 Hugging Face 的 fan-out 问题
- 源站限流
- 大规模 rollout 的公网带宽问题

所以这两者最好结合看，不要混为一谈。

---

## 参考资料

### Dragonfly

- Docs: https://d7y.io/docs/
- Architecture: https://d7y.io/docs/operations/architecture/architecture/
- AI model distribution blog: https://d7y.io/blog/2026/03/11/p2p-accelerated-ai-model-downloads-native-hugging-face-and-modelscope-protocols-in-dragonfly/
- CNCF article: https://www.cncf.io/blog/2026/04/06/peer-to-peer-acceleration-for-ai-model-distribution-with-dragonfly/
- Hugging Face integration: https://d7y.io/docs/next/operations/integrations/hugging-face/

### runai_streamer / vLLM

- vLLM docs: https://docs.vllm.ai/en/latest/models/extensions/runai_model_streamer/
- Run:ai Model Streamer repo: https://github.com/run-ai/runai-model-streamer
- vLLM runai streamer doc source: https://github.com/vllm-project/vllm/blob/main/docs/models/extensions/runai_model_streamer.md

---

## TL;DR

推荐把职责拆成两层：

- **Dragonfly**：解决“模型怎么高效到达每个节点本地”
- **runai_streamer**：解决“本地模型怎么更快加载到 GPU”
- **vLLM**：负责最终推理服务

最推荐链路：

```text
HF/ModelScope/Object Storage
          ↓
       Dragonfly
          ↓
  Node-local NVMe / hostPath
          ↓
     runai_streamer
          ↓
         vLLM
```
