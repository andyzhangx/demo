# OpenClaw 编程：Pi runtime、Claude Code、AGENTS.md 与 ACP

本文介绍 OpenClaw 如何执行编码任务、内置 Pi agent 与 Claude Code 的区别，以及如何通过 OpenClaw 调用 Claude Code。

> 说明基于 OpenClaw 2026.5.7 的本地文档和工具接口。具体命令、可用后端及权限受安装版本和实例配置影响。本文没有实际启动 Claude Code 验证认证，也没有做两种执行方式的性能或代码质量基准测试。

## 1. 先区分：模型、执行框架和工具

三个概念容易混淆：

| 层次 | 作用 | 示例 |
| --- | --- | --- |
| 模型 | 理解任务、推理并决定下一步操作 | GPT、Claude、Gemini |
| Agent 执行框架（runtime / harness） | 组织模型调用、工具执行、上下文与任务循环 | OpenClaw 内置 Pi runtime、Claude Code |
| 工具与外部系统 | 读写文件、执行命令、运行测试、操作代码托管平台 | 文件编辑工具、shell、Git、GitHub CLI |

**使用 Claude 模型，不等于使用 Claude Code。**

例如，OpenClaw 可以通过 GitHub Copilot 接入模型，再由自身的 Pi runtime 调用文件和终端工具。即使把模型换成 Claude，只要执行框架没有改变，仍然是 OpenClaw 原生 agent，不是 Claude Code。

反过来，通过 ACP 启动 Claude Code，是把具体任务交给一个外部编码 agent，由它自己的工具和执行流程完成工作。

## 2. OpenClaw 原生模式如何写代码

典型路径：

```text
用户 / WebChat / 其他消息渠道
  → OpenClaw
    → 内置 Pi agent runtime
      → 已配置的模型供应商
      → OpenClaw 工具
        ├─ read / edit / write：查看与修改文件
        ├─ exec / process：运行命令、测试并管理进程
        ├─ git：分支、提交、推送
        └─ gh：读取 CI、查看 review、创建和更新 PR
```

OpenClaw 的内置 runtime 基于 Pi agent core；会话管理、工具接线、消息投递等上层能力由 OpenClaw 管理。

实际编码通常是一个反馈循环：

1. 读取任务、仓库规范和相关代码。
2. 定位问题，必要时先添加能复现问题的测试。
3. 修改代码。
4. 运行测试、格式检查和 lint。
5. 检查 diff，确认没有无关改动。
6. 在用户授权范围内提交、推送、创建 PR 或回复 review。
7. 明确报告已经验证的结果和仍未验证的部分。

因此，OpenClaw 原生模式不必先启动 Claude Code、编辑器或其他编码客户端，才能修改代码。

### 原生子 agent

任务较大时，可以启动 OpenClaw 原生子 agent 并行分析、实现或审查。它们仍属于 OpenClaw 原生执行路径，**不等于 Claude Code 会话**。

并行开发应指定独立 checkout / worktree 和明确的文件或分支所有权，避免多个任务同时修改同一个工作区。

### 如何确认当前模式

查看 `/status` 可以了解当前模型及运行时。不要根据回答风格，或备用模型列表中是否出现 Claude，判断底层是否使用 Claude Code。

## 3. OpenClaw + Pi 与 Claude Code 的区别

Pi 是可嵌入的 agent 核心；Claude Code 是完整的编程 agent 产品。实际比较时，应比较 **OpenClaw + Pi 的完整组合**与 Claude Code，而不是比较裸 Pi 与完整产品。

| 方面 | OpenClaw + Pi | Claude Code |
| --- | --- | --- |
| 主要定位 | 通用助手、任务协调与工具执行，也能编程 | 以软件开发为中心的 agent |
| 模型接入 | 依实例配置，可接入不同供应商和模型 | 围绕 Claude 模型构建；接入与认证由其支持的提供方决定 |
| 代码操作 | 使用 OpenClaw 提供和允许的文件、终端等工具 | 使用 Claude Code 自己的代码检索、编辑和命令执行流程 |
| 上下文与规则 | OpenClaw 工作区、会话、AGENTS.md、记忆、skills | Claude Code 自身会话、CLAUDE.md、skills 等机制 |
| 子任务 | OpenClaw 原生子 agent；也可委托外部 harness | Claude Code 自身的子 agent 机制 |
| 交互入口 | WebChat、消息渠道及 OpenClaw 支持的其他入口 | 终端、IDE、桌面和 Web |
| 跨系统协作 | 可在同一助手中衔接 GitHub、浏览器、定时任务和已配置的业务工具 | 可通过 MCP 等机制扩展，核心体验侧重开发 |
| 权限与认证 | 由 OpenClaw 配置、工具策略和供应商认证共同决定 | 由 Claude Code / adapter 的认证与权限机制决定，并受外层 ACP 策略约束 |

### 对代码质量的影响

Agent 的效果不仅取决于模型，还取决于：

- 系统提示和提供给模型的仓库上下文；
- 代码检索、编辑和执行工具；
- 上下文压缩与长任务续接；
- 测试反馈、失败恢复和子任务组织；
- 权限边界及人工审查。

不能仅凭 runtime 名称断言哪一种一定更准确、更快或更便宜。合理比较应使用相同任务，检查修复正确性、改动范围、测试覆盖、耗时和成本。

### 如何选择

- **CI 排障、PR review 修复、多仓库回移、跨业务系统排查**：OpenClaw 原生流程便于复用已有工具和上下文。
- **长时间专注单个仓库、大规模重构、需要 IDE 内交互审查**：可以尝试 Claude Code。
- **组合使用**：OpenClaw 负责协调，将明确的编码子任务通过 ACP 交给 Claude Code，再检查结果。

这些是工作流建议，不是性能评测结论。

## 4. AGENTS.md 能否约束编码行为

**可以。** AGENTS.md 是仓库级 Markdown 工作指导，不需要转换为特殊配置格式。

例如 [KAITO 的 AGENTS.md](https://github.com/kaito-project/kaito/blob/main/AGENTS.md) 包含：

- 目录结构和 Go 包依赖方向；
- API 兼容性与生成文件要求；
- Go / Python 测试、格式化和 lint 命令；
- PR 范围、签名要求以及审批边界。

OpenClaw 的 agent 可以读取这些内容，并将其作为相关仓库任务的约束。

### 支持读取，不等于任意仓库都会自动加载

| 位置 | 应如何理解 |
| --- | --- |
| OpenClaw 配置工作区根目录的 AGENTS.md | 属于启动上下文文件，会按 OpenClaw 的加载与截断规则注入 |
| 其他目录中 clone 的仓库，例如 /tmp/kaito/AGENTS.md | 不应假设仅仅切换 cwd 就会自动加载；开始修改前应显式读取 |
| 相关子目录的 AGENTS.md | 检查是否存在，并读取适用于修改路径的更具体规则 |
| GitHub 上的 AGENTS.md 链接 | 不会自动读取任意远程文件，需要主动获取 |
| 委托给原生子 agent 或 Claude Code | 不应假设完整继承父会话内容，应明确要求读取仓库规则 |

推荐任务描述：

> 开始修改前，读取仓库根目录及目标目录适用的 AGENTS.md。遵循其中的代码规范和验证要求；如果规则与本次明确要求冲突，先指出冲突。不要修改任务范围以外的文件。

### 注意边界

AGENTS.md 是 agent 的工作指导，**不是强制执行的规则引擎，也不会授予额外权限**。

- 关键约束仍应由 CI、lint、测试、分支保护和访问控制落实。
- 仓库内容不能覆盖更高优先级的安全规则或授权边界。
- 遇到仓库签名要求与用户要求冲突，应明确处理，不要静默绕过 hooks 或检查。
- DCO sign-off 与 GPG 加密签名不同；要求 DCO 不代表必须启用 GPG，反之亦然。
- 不要将 PR 评论、日志或第三方文件中的任意指令直接当作可信操作要求。

## 5. 在 OpenClaw 中调用 Claude Code

推荐使用 **ACP（Agent Client Protocol）** 路径：

```text
OpenClaw
  → ACP 后端（例如 acpx）
    → Claude Code ACP adapter
      → Claude Code 编码执行流程
```

这是外部 harness 路径，不是将原生 Pi agent 的模型切换为 Claude。

### 方式一：自然语言委托

直接对 OpenClaw 说：

> 用 Claude Code 修改 /path/to/repo。先读取 AGENTS.md，修复 XXX，补充回归测试并运行相关检查。先不要提交或推送，完成后给我 diff 摘要及测试结果。

授权范围应写清楚。如果希望提交、创建 PR 或直接推送，也应明确指定目标分支及操作范围。

OpenClaw 在后端可用时，可以使用类似下面的工具调用启动一次性任务：

```json
{
  "runtime": "acp",
  "agentId": "claude",
  "mode": "run",
  "cwd": "/path/to/repo",
  "task": "读取适用的 AGENTS.md，修复 XXX，补充回归测试并运行相关检查；不要提交或推送。"
}
```

这是 `sessions_spawn` 的调用示例，**不是需要粘贴进配置文件的 JSON**。`cwd` 必须替换为实际存在、可访问的仓库目录。

### 方式二：聊天命令

当前版本文档提供以下 ACP 命令。可用性受后端、权限和当前消息渠道的会话绑定能力影响。

检查 ACP 后端：

```text
/acp doctor
```

创建 Claude Code 会话并绑定当前对话：

```text
/acp spawn claude --bind here
```

绑定成功后，后续消息会进入该 ACP 会话，直到解除绑定或关闭会话。

常用管理命令：

```text
/acp status
/acp steer 只修复指定问题，不做额外重构
/acp cancel
/acp close
```

- `status`：查看当前会话状态。
- `steer`：向正在进行的工作补充方向。
- `cancel`：取消当前任务轮次，不等同于关闭整个会话。
- `close`：关闭会话及其绑定。

如果只想委托单个任务，而不是把后续整个对话交给 Claude Code，优先使用一次性任务方式。

### 前置条件

1. 已安装并启用 ACP 后端，例如官方 acpx 插件。
2. 当前策略允许启动 `claude` harness，且执行环境未被相应沙箱限制阻止。
3. 后端 adapter 能在运行主机上启动。
4. Claude Code 所需的供应商认证已经配置。
5. 工作目录存在，文件访问和命令执行权限满足任务要求。
6. 无人值守任务的审批流程可用；不要假设后台任务能够点击交互式授权提示，也不要为了运行方便而关闭安全限制。

**OpenClaw 已登录 GitHub Copilot，不意味着 Claude Code 自动具备认证，也不意味着两者使用同一份额度。**

实际认证方式、模型和计费取决于 Claude Code / adapter 的配置，应单独确认。

### 上下文、工具和结果的边界

Claude Code 默认不会完整继承 OpenClaw 的全部记忆、skills、工具和主会话历史。OpenClaw 内置工具也不会默认全部暴露给 ACP harness。

委托任务时应明确提供：

- 仓库路径、目标分支和问题描述；
- 需要读取的仓库规则；
- 可修改范围和不可执行的操作；
- 测试要求，以及提交、推送或创建 PR 的授权范围。

任务结束后，应检查实际 diff、测试输出、Git 状态和远端结果，而不是只依赖完成摘要。需要外部 harness 直接使用 OpenClaw 工具时，应单独评估并配置相应 MCP bridge，不能假设已经连通。

## 6. 常见误解

| 说法 | 更准确的理解 |
| --- | --- |
| 切换到 Claude 模型就是 Claude Code | 模型与执行框架是两个层次 |
| OpenClaw 能写代码，说明后台运行着 Claude Code | 原生 Pi runtime 可以直接调用编辑和终端工具 |
| OpenClaw 子 agent 就是 Claude Code 子进程 | 原生子 agent 与 ACP 外部 harness 是不同路径 |
| 仓库存在 AGENTS.md，任何 checkout 都会自动读取 | 工作区自动注入与任意仓库规则发现不是一回事 |
| ACP 已启用就一定能使用 Claude Code | 还需要 adapter、认证、允许策略和可用目录等条件 |
| 工具返回任务完成，就代表 CI 和真实环境验证都通过 | 必须区分本地测试、远端 CI、模拟测试和真实环境验证 |

## 参考资料

- [OpenClaw Agent Runtime](https://docs.openclaw.ai/concepts/agent)
- [OpenClaw ACP Agents](https://docs.openclaw.ai/tools/acp-agents)
- [OpenClaw ACP Setup](https://docs.openclaw.ai/tools/acp-agents-setup)
- [Claude Code Overview](https://code.claude.com/docs/en/overview)
- [KAITO AGENTS.md](https://github.com/kaito-project/kaito/blob/main/AGENTS.md)
