# SMB CSI PR #1221：遍历挂载表引入的跨卷阻塞风险

## 结论与审查范围

- **审查对象**：[kubernetes-csi/csi-driver-smb#1221](https://github.com/kubernetes-csi/csi-driver-smb/pull/1221)。
- **分析版本**：`ce6f3a07772dac333b1f8c06de9bf4f46a99bf86`；代码和 CI 状态最后核对于 **2026-11-06 09:44 UTC 左右**。以下代码链接固定到该版本，不代表后续提交仍有相同行为。
- **建议优先级**：P2，条件性的 Linux 可用性风险；不是已经复现的故障或确定发生的永久死锁。
- **核心问题**：新增 stale-bind 检查为了查找当前卷的挂载条目，对挂载表中所有路径执行 `filepath.EvalSymlinks`。该操作会访问文件系统，可能把无关网络挂载的元数据访问延迟引入健康卷的 `NodePublishVolume`，并延长当前卷的操作锁占用。
- **验证边界**：已核对代码调用链、Go 路径解析行为和 Windows 分支；未做故障挂载复现，未运行本地编译、测试或 E2E。独立复核未完成，本文不应作为已验证的生产事故根因报告。
- **CI 与代码风险必须分开**：没有证据证明当时两项 E2E 失败由此风险引起，特别是 Windows 不走这里讨论的全挂载表遍历路径。

## 1. PR 要解决的原始问题

Linux 上的正常挂载关系是：

```text
SMB share
    ↓ CIFS mount
staging/globalmount
    ↓ bind mount
Pod target
```

如果 staging 挂载丢失，仅剩空目录，Pod target 可能曾经 bind 到这个目录。随后在 staging 路径恢复 CIFS 挂载，不保证之前创建的 target bind 自动切换到恢复后的共享。

PR 因此在 `NodePublishVolume` 发现 target 已挂载时，对比 staging 和 target 的挂载设备，识别并重建 stale bind。这个目标合理；本文讨论的是查找挂载条目的实现方式，而不是建议移除恢复逻辑。

代码：[已挂载 target 的检查及重建入口](https://github.com/kubernetes-csi/csi-driver-smb/blob/ce6f3a07772dac333b1f8c06de9bf4f46a99bf86/pkg/smb/nodeserver.go#L151-L175)。

## 2. 风险调用链

```text
NodePublishVolume
  → targetBindIsStale(source, target)
    → mounter.List()
    → findMountPoint(mounts, source)
    → findMountPoint(mounts, target)
      → mountPathKey(每个挂载点路径)
        → filepath.EvalSymlinks(...)
          → 对路径组件执行 os.Lstat
```

`targetBindIsStale` 分别查找 source 和 target：

```go
src, srcOK := findMountPoint(mounts, source)
dst, dstOK := findMountPoint(mounts, target)
```

`findMountPoint` 遍历完整列表，而且找到匹配项后仍继续扫描：

```go
for _, mp := range mounts {
    if mountPathKey(mp.Path) == key {
        found = mp
        ok = true
    }
}
```

`mountPathKey` 先解析符号链接，再规范化路径：

```go
if eval, err := filepath.EvalSymlinks(path); err == nil {
    path = eval
}
```

代码：[targetBindIsStale](https://github.com/kubernetes-csi/csi-driver-smb/blob/ce6f3a07772dac333b1f8c06de9bf4f46a99bf86/pkg/smb/nodeserver.go#L632-L650)、[findMountPoint / mountPathKey](https://github.com/kubernetes-csi/csi-driver-smb/blob/ce6f3a07772dac333b1f8c06de9bf4f46a99bf86/pkg/smb/nodeserver.go#L653-L675)。

### 为什么 EvalSymlinks 不只是字符串处理

`filepath.EvalSymlinks` 必须检查路径组件是否为符号链接；Go 的 `walkSymlinks` 实现逐级调用 `os.Lstat`，包括最终路径组件。路径没有符号链接，也不意味着完全不访问文件系统。

参考：[Go filepath.EvalSymlinks 文档](https://pkg.go.dev/path/filepath#EvalSymlinks)、[Go 路径解析实现](https://github.com/golang/go/blob/master/src/path/filepath/symlink.go)（后者为动态源码链接）。

对网络文件系统执行元数据访问，可能需要与远端交互或等待内核重试。因此，查找 A 的挂载条目时，遍历过程会额外访问同一挂载表中 B、C 等无关挂载点。source 与 target 各查找一次，正常完成时会对完整列表扫描两次。

## 3. 一个健康卷被拖慢的条件性场景

假设同一节点、driver 可见的挂载命名空间中存在：

```text
A：健康的 SMB 共享
B：另一个网络共享，服务端或网络异常
```

对已有 target 的 A 再次调用 `NodePublishVolume`：

1. A 的 staging 与 target 检查正常，进入 stale-bind 检查。
2. 查找 A 的挂载条目时，遍历到 B。
3. 调用 `EvalSymlinks(B 的挂载点路径)`，触发 B 的路径元数据访问。
4. 如果该访问等待远端响应或内核重试，A 的 Publish 也必须等待。

关键变化是 **A 新增了对无关 B 的文件系统访问依赖**，并不是“B 一断网，A 必定永久卡死”。

实际影响取决于：

- B 是否出现在当前 driver 看到的挂载表中；
- 文件系统类型、内核版本和挂载选项；
- 元数据缓存是否可用以及是否需要重新验证；
- 网络错误类型和内核超时、重试行为。

缓存命中或错误立即返回时，影响可能很小；等待重连或重试时可能显著延迟。本文未测量延迟上限，不宣称永久阻塞或固定频率。

## 4. 当前卷锁为什么会放大影响

该 PR 在 staging 检查、恢复、stale-bind 检查和最终 bind 之前取得锁：

```go
lockKey := fmt.Sprintf("%s-%s", volumeID, source)
if acquired := d.volumeLocks.TryAcquire(lockKey); !acquired {
    return nil, status.Errorf(codes.Aborted, volumeOperationAlreadyExistsFmt, volumeID)
}
```

正常路径通过 `defer` 在函数返回时释放锁。

代码：[锁键、获取及释放范围](https://github.com/kubernetes-csi/csi-driver-smb/blob/ce6f3a07772dac333b1f8c06de9bf4f46a99bf86/pkg/smb/nodeserver.go#L87-L103)。

如果 A 的 Publish 正在等待 B 的路径访问：

- A 当前请求可能超过 RPC deadline；
- `EvalSymlinks` 不接收 `context`，RPC 取消并不保证其同步文件系统调用立即返回；
- 在 handler 返回并释放锁前，同一锁键的 Stage、Unstage 或 Publish 可能因竞争锁返回 `Aborted`。

这里不是一个全局锁直接锁住所有卷，也不意味着所有 CSI RPC 都使用该锁。准确说法是：**B 的异常可能间接延长 A 的操作锁占用**；其他健康卷如果也执行相同的全表遍历，则可能各自受到 B 的影响。

## 5. 为什么是新增风险，而非仅有原来的网络挂载风险

原有 `ensureMountPoint` 也可能读取挂载表，但查找条目时比较的是路径字符串；随后进行的目录访问针对当前请求的 target。

新增 `findMountPoint` 则为比较路径，对所有条目执行 `EvalSymlinks`。

| 行为 | 故障影响范围 |
|---|---|
| 检查当前请求的 staging / target | 当前卷异常拖慢当前卷操作 |
| 解析所有挂载表条目的实际路径 | 无关挂载异常也可能拖慢当前卷操作 |

因此问题不只是额外 `stat` 的开销，而是扩大了故障影响范围。旧逻辑并不是完全不访问网络文件系统；差别在于是否主动访问无关挂载。

## 6. 修复建议

**保留 stale-bind 识别，但避免为查找挂载条目而访问所有挂载点。**

建议：

1. 对挂载表中的路径做纯字符串规范化后比较，例如 `filepath.Clean`；在需要时处理绝对路径，但不要对每一个条目执行符号链接解析。
2. 如果必须支持 staging / target 的符号链接别名，仅解析这两个请求路径，避免访问无关条目。
3. 保留叠加挂载和同路径多条记录下正确选择条目的语义。当前循环保留最后一个匹配项，不能在未分析语义前简单改成首个匹配即退出。
4. 为路径别名、重复挂载记录和 stale bind 的预期行为补充针对性验证。

以下方式不能作为完整修复：

- **仅增加 `break`**：在匹配项之前仍可能遇到异常挂载，还可能改变同路径多挂载记录的选择语义。
- **仅在外围包超时 goroutine**：底层同步文件系统操作可能仍然运行，另外还要处理 goroutine 生命周期和锁交接问题。
- **直接删除 stale-bind 检查**：会丢失本 PR 要提供的恢复能力。

## 7. 建议的验证方式（尚未执行）

在隔离环境中验证，不应直接对生产节点注入网络故障：

1. 准备独立共享 A 与 B，并确认都出现在 driver 的挂载命名空间中。
2. 完成 A 的 Stage / Publish，使后续 Publish 进入“target 已挂载”分支。
3. 让 B 的元数据访问处于等待状态，同时确保 A 的服务端与网络仍正常；具体方法需要针对测试文件系统设计，不应假设断网必然触发元数据 IO。
4. 再次对 A 调用 Publish，记录耗时，并通过系统调用跟踪定位是否在 B 的路径上等待。
5. 检查同一 A 锁键下的后续请求行为，以及恢复 B 后原请求和锁是否恢复。
6. 对比修改前后版本，确认修复后不再访问无关 B，并保持 stale-bind 修复及路径别名场景正确。

可另用可控的路径解析测试替身验证“不得解析无关挂载条目”，但这类单元测试不能代替真实网络文件系统超时行为验证。

## 8. 与 CI 失败的关系

在上述核对时点，PR 仍有以下失败检查：

- `pull-csi-driver-smb-e2e-windows-2022-hostprocess`
- `pull-csi-driver-smb-external-e2e`

**没有分析证据将这些失败与本文风险关联起来。** CI 状态只是当时的快照，不是故障归因。

Windows 的 CSI Proxy 与 HostProcess mounter 的 `List()` 均返回“不支持”。`targetBindIsStale` 收到该错误后，在 Windows 上直接调用 `symlinkTargetDiffers`，不会进入 `findMountPoint` 全表遍历：

- [Windows CSI Proxy mounter.List](https://github.com/kubernetes-csi/csi-driver-smb/blob/ce6f3a07772dac333b1f8c06de9bf4f46a99bf86/pkg/mounter/safe_mounter_windows.go#L216-L220)
- [Windows HostProcess mounter.List](https://github.com/kubernetes-csi/csi-driver-smb/blob/ce6f3a07772dac333b1f8c06de9bf4f46a99bf86/pkg/mounter/safe_mounter_host_process_windows.go#L242-L246)
- [Windows fallback 分支](https://github.com/kubernetes-csi/csi-driver-smb/blob/ce6f3a07772dac333b1f8c06de9bf4f46a99bf86/pkg/smb/nodeserver.go#L635-L644)

因此，不能用这个 Linux 路径上的分析解释 Windows HostProcess 失败。external E2E 也需要独立查看日志与现场证据，才能判断是否有关。

## 9. 最终判断

这是具有明确代码依据的 **条件性跨挂载可用性风险**：查询当前卷的挂载信息不应无意间对所有无关网络挂载执行文件系统访问。

建议修正路径比较方式，并通过隔离环境故障验证确认实际影响。当前证据支持提出审查意见，但不足以声称已经复现、证明永久死锁，或认定为现有 CI 失败的根因。

本文仅记录分析，未向上游 PR 发布 review 评论，也未修改该 PR 的代码。
