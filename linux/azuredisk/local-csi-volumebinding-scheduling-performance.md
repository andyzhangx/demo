# Local CSI 大规模集群调度延迟：VolumeBinding 根因、缓解与优化

> 分析日期：2026-11-14。基于 upstream Kubernetes **v1.36.1** 源码、公开 issue／benchmark PR 及匿名化现场反馈。
>
> 本文虽然归档在 `linux/azuredisk`，讨论的是 **node-local NVMe CSI + kube-scheduler VolumeBinding**，不代表 Azure Disk CSI 存在同样故障。未独立访问生产集群、采集 profile、运行 benchmark 或部署修复；ACStor local-csi-driver v0.2.19 的内部实现尚未审阅。所有优化均为建议，不是已交付能力或版本承诺。

## 1. 结论摘要

1. 现有证据强烈支持 **VolumeBinding 容量查找的可扩展性瓶颈**，不能仅按“CSI 容量发布延迟”处理。逐节点发布容量是 node-local storage 的正常用法，不等于 driver 实现错误。
2. 容量检查对每个到达该路径的节点／PVC，重复枚举 `CSIStorageCapacity` 并转换 topology selector，最坏工作量接近 **O(F × P × C)**。这里的 List 是 **本地 informer 缓存读取，不是反复访问 API server**。
3. `percentageOfNodesToScore=5` 值得做受控缓解实验，但它控制的是 **找到多少个 feasible nodes 后可以停止**，不是“最多检查 5% 的节点”。不能承诺端到端延迟降低 50%。
4. 真正的修复主要在 **kube-scheduler**：减少重复 List／selector 转换，再为常见 topology 建索引；只按 StorageClass 分桶不足以解决单一 StorageClass 下的 1,427 个对象。
5. driver 侧可清理无效对象、保证容量准确和更新合理，但不能伪造容量、错误合并独立 NVMe，也不应简单关闭容量感知检查。

## 2. 现象与证据边界

现场反馈涉及 AKS 1.36.1、ACStor 2.2.1、local-csi-driver 0.2.19，以及约 1.7k 节点、其中 1,427 个 NVMe 节点的集群。这里不保留客户名、集群名或 Pod 标识。

公开 [Issue #144144](https://github.com/kubernetes/kubernetes/issues/144144) 描述了同类场景：

- 正常占用时，大量节点先被资源过滤排除，带 local ephemeral volume 的 Pod 调度较快。
- 一批约 300 个 NVMe 节点释放、带本地临时卷的 Pod 同时进入队列后，单次调度周期达到约 1.3–2.2 秒。
- 一个 5 分钟样本中，305 个此类 Pod 消耗约 192 秒调度时间；其他 Pod 的首次调度尝试也被延后。
- 空闲节点减少后，周期重新降到约 65 ms；不带 PVC 的对照 Pod 明显更快。
- trace 指向 `Computing predicates` 阶段，但它覆盖多种 Filter 工作，**单靠这条 trace 不能证明 CPU 时间全部消耗在 VolumeBinding**。

以上生产数字和 issue 中的 benchmark 结果属于报告者提供的数据，不是本文独立复测结果。生产节点数也可能随时间变化；后文阈值计算分别列出 1,716 和 trace 中的 1,751 节点示例。

“local ephemeral volume”需要进一步确认其具体 API 形态。本文热点路径针对 **generic ephemeral volume 生成的 PVC** 或其他未绑定、需要容量检查的 PVC；不能据此推断 CSI inline ephemeral volume 也走相同路径。

## 3. 源码如何产生这一成本

主要路径：

- [`binder.go`：`checkVolumeProvisions()`、`hasEnoughCapacity()`、`nodeHasAccess()`](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/scheduler/framework/plugins/volumebinding/binder.go)
- [`volume_binding.go`：插件 PreFilter／Filter 与 CycleState](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/scheduler/framework/plugins/volumebinding/volume_binding.go)

简化逻辑，不是完整源码：

```text
Pod 的一个调度周期
  对到达 VolumeBinding 的候选节点执行 Filter
    对需要动态 provisioning／容量检查的 PVC
      hasEnoughCapacity()
        从 informer lister 获取全部 CSIStorageCapacity
        遍历对象，检查：
          StorageClass 是否相符
          volume limit 是否足以容纳请求
          node topology 是否匹配
            nodeHasAccess()
              LabelSelectorAsSelector(capacity.NodeTopology)
              selector.Matches(node.Labels)
        找到合适对象后提前返回
```

定义：

- **F**：实际到达容量检查的节点数，不是简单的总节点数或 GPU 空闲节点数。
- **P**：每个 Pod 中需要检查的动态 provisioning PVC 数量。
- **C**：lister 获取的容量对象总量，可能包含其他 StorageClass／驱动发布的对象。

最坏工作量为 `O(F × P × C)`。已有卷匹配、StorageClass／容量不符、提前命中和其他插件的失败都会改变实际执行量，不能把该公式当作每次都完整执行 F×P×C 次 topology 匹配。

### 3.1 三种不同的开销

1. **List 与结果分配**：反复构造容量对象列表，即使最终较早匹配，也已有 List 成本。
2. **遍历与 selector 编译**：同一容量对象的 topology 在不同节点／Pod 检查中反复转换。
3. **GC／并发成本**：大量短命分配和并行 Filter 可能放大 CPU、GC 和锁竞争。

因此“降低 driver API 请求量”不等价于解决这里的 List 热点；scheduler 的 informer 已经把 API 读取缓存到了本地。

### 3.2 为什么普通 Pod 也受影响

一个活跃 scheduler 中，调度周期串行推进；周期内部的节点 Filter 可并行，binding 周期则可以异步进行。一个昂贵的 scheduling cycle 会延迟下一个 Pod 开始尝试。

所以需要分别测量：

- queue wait：入队到第一次尝试；
- scheduling attempt duration：单次尝试耗时；
- binding／provisioning／Pod Ready：后续阶段。

提高普通 Pod 优先级不修复单周期成本，也不能中断当前正在运行的慢周期。

## 4. `percentageOfNodesToScore=5`：有用，但不是节点检查上限

[v1.36.1 `numFeasibleNodesToFind()`](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/scheduler/schedule_one.go) 的自适应公式大致为：

```text
percentage == 0:
    percentage = max(5, 50 - floor(N / 125))

target = max(100, floor(N * percentage / 100))
```

小集群等情形有额外边界处理。下面假设参与该阈值计算的候选列表包含所列全部节点；实际还要检查 PreFilter 结果、有效 scheduler profile 和 AKS 自身配置。

| 候选节点数 N | `0` 的自适应百分比 | 默认 feasible target | 显式 `5` 的 target |
|---|---:|---:|---:|
| 1,716 | 37% | 634 | 100 |
| 1,751 | 36% | 630 | 100 |

如果只有约 300 个可行节点，默认值找不到 630+ 个，通常会遍历完整候选列表；显式 5 则可能找到 100 个可行节点就提前停止。

但是：

- 必须先通过 Filter 才知道节点是否 feasible；为了找到 100 个，可能检查远多于 100 个节点。
- 不足 100 个节点可行时，通常仍需遍历完整候选列表。
- 取消信号发出时，已经运行的并行检查仍可能继续产生开销。
- 遍历顺序、资源碎片、缓存、GC 和其他插件决定实际收益。
- 更少节点参与后续打分，可能影响装箱、亲和性、拓扑偏好和资源利用率。

**推荐定位：可回滚的止血实验，而非修复。**由 AKS 控制平面团队确认支持的调整方式与实际生效配置；本文没有确认客户可自行修改此托管组件参数。实验必须同时比较 batch 完成时间、普通 Pod 的 p95／p99 首次尝试等待、节点利用率和放置质量。

参考：[Kubernetes Scheduler Performance Tuning](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduler-perf-tuning/)。

## 5. 第一阶段优化在哪里做：kube-scheduler，而非 local-csi-driver

这里的“低风险”仅表示比完整 topology 索引改动小，不是可以不经测试直接上线。

| 建议 | 主要位置／思路 | 预期收益与边界 |
|---|---|---|
| 缓存编译后的 selector | `binder.go` 的 `nodeHasAccess()` 周边，或 informer 派生对象 | 去掉重复 `LabelSelectorAsSelector()`；仍有线性遍历。 |
| 一次调度周期共享容量快照 | `volume_binding.go` 的 PreFilter／CycleState／Filter，将数据传给 binder | 减少重复 List 与列表分配；不会自动消除 topology 匹配的 F×C。 |
| 按 StorageClass 分桶 | 周期快照或长期派生索引 | 排除无关 StorageClass；同一 StorageClass 下的 1,427 对象仍要进一步优化。 |

### 5.1 selector 缓存与容量快照不是一回事

`nodeTopology` 在对象生命周期内不可修改，因此可以复用已编译 selector。但缓存必须正确处理 UID、删除／重建及并发访问；不能只按名称永久保存。

**容量数值会变。**不能因为 selector 可缓存，就把 `Capacity`／`MaximumVolumeSize` 也当作永久不变。每周期快照与跨周期 informer 索引需要各自明确一致性语义和更新路径。

采用 CycleState 方案时：

- 尽量仅在相关 Pod 需要容量检查时准备数据。
- 并行 Filter 共享的数据应只读，注意 Clone／preemption 模拟路径。
- 为 PreFilter 新增的串行成本单独计时。
- 不要把“遍历所有节点×所有容量”简单搬到 PreFilter，否则可能只是移动瓶颈。

### 5.2 如何交付给 AKS

```text
upstream Kubernetes 修改与验证
  → upstream review／合入，或 AKS 评估受控 backport
  → 控制平面集成与回归
  → 发布包含优化的 kube-scheduler
```

仅升级 ACStor／local-csi-driver 不会自动更新托管控制面的这段代码。是否 backport、适用版本和时间表，必须由相应维护团队确认。

## 6. 第二阶段：StorageClass + topology 的定向查找

对常见逐节点 topology，可以考虑索引：

```text
(StorageClass, topology label key, topology label value)
    → 可能匹配的 CSIStorageCapacity 对象集合
```

节点检查先取得少量候选对象，再验证完整 selector，而不是遍历整个集群的容量对象。

这不是把 CSIStorageCapacity 简化成固定的 `nodeName → capacity`：其 `NodeTopology` 是通用 LabelSelector，可能匹配多个节点，也可能包含复杂表达式。

### 6.1 正确性要求

- `matchLabels` 有多个条件时，索引命中只是候选，仍需验证整个 AND 条件。
- 复杂 `matchExpressions` 必须完整支持，或走安全的线性回退路径。
- 空 selector 匹配所有节点；未设置 topology 不匹配节点，不能混淆。
- 保留缺失 label、`Exists`／`DoesNotExist`／`NotIn` 等语义。
- 同节点、同 StorageClass 可能有多个匹配容量池，不应压缩成任意一个数值。
- 保留 `MaximumVolumeSize` 和 `Capacity` 的既有 volume-limit 语义及评分需要；不能自行改成另一套判断。
- 容量更新、对象删除／重建、节点 label 改变都要正确反映。
- 检查并行 Filter、索引更新锁竞争和缓存内存；不能以全局大锁换掉原有扫描。

长期 informer 派生索引可以跨 Pod 摊销构建成本，但维护复杂度高于 per-cycle 快照。应通过 benchmark 决定阶段划分，而不是预先保证某种实现一定最快。

## 7. local-csi-driver 侧能做什么

**原则：检查发布质量，降低无效工作；不要为了绕过 scheduler 缺陷破坏存储容量语义。**以下建议基于 CSI 接口，尚未证明该版本 driver 存在相应缺陷。

### 7.1 审计容量对象是否膨胀

检查：

- 旧节点、旧安装实例或旧 StorageClass 遗留的容量对象。
- 同一 StorageClass／topology／存储池的重复对象；不要把合法的独立池误判成重复。
- 不需要的 StorageClass 容量发布，以及合理的 owner reference／垃圾回收。
- 若使用 external-provisioner，是否意外打开 `--capacity-for-immediate-binding`。官方默认关闭，普通 scheduler 不需要为 Immediate-binding StorageClass 使用这一容量信息；修改前也要确认是否有其他消费者。

**1,427 个容量对象对应 1,427 个 NVMe 节点本身合理。**若已是最小有效集合，清理并不能保证大幅减少 C。

### 7.2 容量准确与合理更新

- 检查卷创建／删除后容量反映的延迟。
- 检查 `Capacity`／`MaximumVolumeSize` 是否符合真实可分配行为，包括碎片和存储池约束。
- 抑制无实质变化的重复写入；关注 watch、informer 和可能的重试事件负担。
- 不要把每次对象更新都等同于 scheduler 一定重排所有 Pod；v1.36.1 VolumeBinding 有容量事件 queueing hint，需要按实际字段变化核查。
- 降低 poll 频率只能减少部分更新压力，不能消除 Filter 的全量扫描，并可能让容量更陈旧。
- topology 只表达必要、正确的条件；不应为了让 selector 更简单而扩大可访问范围。

源码会先检查 volume limit，再检查 topology。准确地报告“请求无法容纳”可以跳过后续 selector 转换，但仍然保留列表／遍历成本。

**GPU 被占满不等于磁盘容量不足。**不能按 GPU 忙闲伪造容量、隐藏有效对象或谎报 topology。

### 7.3 不要简单合并独立节点的容量

例如：

```text
Node A 本地盘剩余 100 GiB
Node B 本地盘剩余 900 GiB
```

不能发布一个同时匹配 A、B、容量为 1,000 GiB 或 900 GiB 的对象。这会把 B 的独立磁盘容量错误地当成 A 也能访问。

按保守下界汇总虽然可能避免高估，却会隐藏 B 的可用容量，并带来拓扑分组和更新一致性问题。不是本次故障推荐的简单缓解措施。

对于零／未知容量对象，也不要仅为减少 C 随意删除；必须明确恢复发布的可靠性、可调度性语义与消费者行为，避免节点恢复容量后长期不再被发现。

### 7.4 真正的 scratch workload：可评估另一种卷模型，但不是快速替换

如果应用仅需 Pod 生命周期内的本地 scratch，可评估：

| 卷模型 | 与当前热点的关系 | 主要代价 |
|---|---|---|
| Generic ephemeral volume → PVC → 动态 provisioning | 相关未绑定 PVC 会进入 VolumeBinding 容量检查 | 保留现有容量／拓扑调度语义，但受当前热点影响。 |
| CSI inline ephemeral volume | 没有对应 PVC，不经过这里的 PVC 容量绑定路径 | 不通过该 CSIStorageCapacity 机制进行调度前容量检查；需要 driver 支持及其他保障。 |

CSI inline ephemeral 的评估必须覆盖磁盘隔离、容量耗尽、可用节点约束、节点侧失败／重试、清理和应用容错。不能直接认定当前 driver 支持，也不能声称迁移后解决所有调度问题。

参考：[Ephemeral Volumes](https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/)。

## 8. 其他缓解措施与不推荐的捷径

### 可评估

- **Kueue 准入节流**：按完整 Workload 分批、平滑突发；不要任意拆分要求 gang／all-or-nothing 的任务。释放间隔按吞吐与反馈校准，不给固定万能参数。
- **scheduler 资源检查**：如果存在 CPU throttling、内存压力或 GC 热点，评估控制平面资源；加资源不能修复交叉扫描算法。
- **独立 scheduler 进程**：必要时隔离 batch 与普通 Pod 的调度吞吐。需要明确 Pod 归属、插件与 leader-election 配置、AKS 支持范围以及跨 scheduler 资源竞争。它隔离影响，不修复算法。

### 不推荐直接采用

- 关闭 `CSIDriver.spec.storageCapacity`：移除容量保护，可能把等待变成选错节点后的 provisioning 失败。
- 禁用 VolumeBinding 或随意改掉 `WaitForFirstConsumer`：可能破坏本地存储的节点／卷选择协调。
- 同一个 scheduler 增加 profiles，或增加共享 leader-election 的副本：不等于获得独立调度吞吐。
- 仅提高普通 Pod priority：可能影响排队顺序，但不修复慢周期成本，也可能造成其他负载饥饿。
- 把已有有效的 node-local 容量对象当成“过多”强行删除。

## 9. 验证计划：先证明热点，再衡量修复

### 9.1 生产／复现环境证据

由有权限的工程团队在可控窗口采集，避免把包含敏感信息的 profile／对象直接公开：

1. scheduler CPU 与 allocation profile，寻找 `hasEnoughCapacity`、lister List、`LabelSelectorAsSelector`、GC 和锁竞争。
2. VolumeBinding Filter 与其他插件的耗时、evaluated／feasible nodes、CPU throttling。
3. queue 首次尝试等待、每次 scheduling attempt、重试、binding／provisioning／Ready 的分段时间。
4. 匿名化 Pod／PVC／StorageClass／CSIDriver／CSIStorageCapacity 样本与实际 topology，核对 generic versus inline ephemeral。
5. 无 PVC 或不触发容量检查的对照 workload；类似节点释放规模下比较。
6. 容量对象更新率、有效变化率、更新延迟和失败 provisioning 事件。

### 9.2 benchmark 与 correctness 测试矩阵

- 节点／容量对象规模：1k、1.5k、5k 等；同时变化 F 与 C，而非只测 F=C。
- 可行节点数：约 300、100、低于 100，以及节点持续被占用的整个 batch。
- 单／多 PVC、同／不同 StorageClass、复杂 topology、无匹配及提前匹配。
- 容量充足／不足、缺失值、MaximumVolumeSize、多个匹配池。
- 节点 label 更新、容量更新、对象删除／重建、并行访问及 race tests。
- cache 冷启动／稳态、selector 分配量、B/op、allocs/op、GC 和 index 更新成本。
- 保持 Filter／Score 语义以及卷实际可创建性。

关联 PR 提供的运行入口（**需要先在含该 benchmark 的 Kubernetes checkout 中执行；本文未运行**）：

```sh
go test ./pkg/scheduler/framework/plugins/volumebinding/ -run '^$' -bench BenchmarkFilter -benchmem
```

不能只依赖 microbenchmark。端到端回归应覆盖 PreFilter + 并行 Filter + Score、队列压力、Kueue batch 完成时间、普通 Pod p95／p99 首次尝试等待以及最终 provisioning 成功率。降低单 Pod Filter 时间却恶化放置质量或失败重试，不算成功。

## 10. 优先级、责任与当前 upstream 状态

| 优先级 | 动作 | 主要协作方 | 交付证据 |
|---|---|---|---|
| P0 | 容量对象审计 + 峰值 profile + 最小复现 | local-csi／ACStor、AKS 控制平面 | 确认热点和数据发布是否正确；不是先认定 driver 有 bug。 |
| P1 | 支持范围内 canary 5% + Kueue 准入平滑 | AKS、工作负载团队 | 可回滚结果、queue p99、batch 完成时间及放置质量。 |
| P2 | selector 缓存／每周期快照原型 | SIG Scheduling、SIG Storage | microbenchmark、race／correctness tests、全调度周期结果。 |
| P2 | topology 索引与安全回退 | 同上，driver 团队协助真实 topology 验证 | 高 C、高 F 场景减少扫描，更新和容量判断保持正确。 |
| 发布 | 合入／backport 评估、AKS 集成与回归 | upstream 维护者、AKS 控制平面 | 明确修复 SHA、适用版本和实际发布安排。 |

截至 **2026-11-14** 本次检查：

- [Issue #144144 — VolumeBinding Filter cost grows with nodes × CSIStorageCapacity objects](https://github.com/kubernetes/kubernetes/issues/144144)：Open，`needs-triage`，标注 SIG Scheduling／SIG Storage。
- [PR #144143 — volumebinding: add BenchmarkFilter](https://github.com/kubernetes/kubernetes/pull/144143)：Open、未合并；**仅增加 benchmark，不是性能修复**。
- 以上是时间点快照，不代表读者查看时的最新状态。目前不能据此承诺修复版本或 ETA。

如果容量对象已最小、字段准确、更新正常，应明确把算法优化交给 scheduler，而不是要求 driver 牺牲容量语义来隐藏有效对象。

## 11. 可用于跨团队沟通的英文摘要

> The evidence strongly points to a scalability bottleneck in VolumeBinding's capacity lookup, rather than simply delayed CSI capacity reporting. Lowering `percentageOfNodesToScore` to 5 is worth a controlled trial, but it targets 100 feasible nodes at this scale—not 100 evaluated nodes—and a 50% latency reduction is not guaranteed. The durable fix is to avoid repeated capacity-list/selector processing and introduce topology-aware lookup while preserving CSI capacity semantics. The driver team can help audit published objects, validate update behavior, and provide realistic topology samples and a reproducer. The current upstream PR adds a benchmark only; it does not yet contain a fix.

## 参考资料

- [Kubernetes v1.36.1 — VolumeBinding binder](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/scheduler/framework/plugins/volumebinding/binder.go)
- [Kubernetes v1.36.1 — VolumeBinding plugin／queueing hints](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/scheduler/framework/plugins/volumebinding/volume_binding.go)
- [Kubernetes v1.36.1 — scheduler candidate-node threshold](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/scheduler/schedule_one.go)
- [Kubernetes v1.36.1 — CSIStorageCapacity API 字段语义](https://github.com/kubernetes/kubernetes/blob/v1.36.1/staging/src/k8s.io/api/storage/v1/types.go)
- [Storage Capacity](https://kubernetes.io/docs/concepts/storage/storage-capacity/)
- [Scheduler Performance Tuning](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduler-perf-tuning/)
- [CSI external-provisioner 参数与容量发布说明](https://github.com/kubernetes-csi/external-provisioner/blob/master/README.md)（master 文档可变化，不代表已核实部署中的 sidecar 版本／参数）
- [Ephemeral Volumes](https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/)
