# KAITO ModelMirror 下载失败：Azure Linux helper 镜像与 HF Xet TLS 信任库

记录日期：2026-10-23。

## 1. 结论与证据边界

将 ModelMirror 下载 helper 从 `mcr.microsoft.com/mirror/docker/library/python:3.11-slim` 切换到 `mcr.microsoft.com/azurelinux/base/python:3.12` 后，`job/43903f-download-rt8dt` 的一个 Pod 在下载模型权重时失败。

**高置信度原因：Azure Linux helper 的系统 CA 信任库较精简，原生 HF Xet 下载客户端无法验证 `cas-server.xethub.hf.co` 的证书链，底层错误为 `UnknownIssuer`。** Python 3.12 本身、pip 的 root warning、HF 版本更新提示和短暂的文件锁等待不是当前证据指向的失败原因。

证据边界必须区分：

- **现场证据**：用户提供了 `43903f-download-rt8dt-cvrdb` 的 downloader 日志；调用栈在 `xet_get()` / `hf_xet.download_files()` 访问 Xet CAS 时失败。
- **本地复现**：使用实际 Azure Linux 镜像中提取的 CA bundle，在 Azure Linux 3.0 / Python 3.12 环境复现了同类异常；Xet 内部日志明确出现 `UnknownIssuer`。替换 CA bundle 或禁用 Xet 后，对照下载均成功。
- **尚未完成**：没有直接访问故障集群，也没有取得该 Pod 自己的 Xet 内部日志。因此，`UnknownIssuer` 是受控复现的直接证据，不应写成已从故障 Pod 中读到的日志。
- `kubectl logs job/...` 找到了 4 个 Pod，但只选取其中一个；不能据此断言 4 次失败原因完全相同，也不能仅凭这一条日志确认 Job 的最终 condition。

本次选用的 workaround 为 **方案二：`HF_HUB_DISABLE_XET=1`，改用 HTTP 下载路径**。已提交到 helper-image 更新分支，详见第 6 节；尚未声称原集群已部署修复或完整大模型重试成功。

## 2. 现场环境

| 项目 | 信息 |
| --- | --- |
| Job | `43903f-download-rt8dt` |
| 此次日志对应 Pod | `43903f-download-rt8dt-cvrdb` |
| 主容器 | `downloader` |
| Native sidecar | `sampler`，位于 `initContainers` |
| 模型 | `Qwen/Qwen3-Coder-30B-A3B-Instruct` |
| Python | 日志中的路径为 `/usr/lib/python3.12/site-packages/` |
| huggingface-hub | `1.18.0` |
| 失败客户端路径 | `hf download` → `snapshot_download` → `xet_get` → `download_files` |
| 失败服务 | `https://cas-server.xethub.hf.co/v2/reconstructions/...` |

日志没有提供实际 Pod 的 imageID/digest。以下是本次独立检查的 Azure Linux tag 所指向的镜像，不应当作从故障 Pod 读取的 imageID：

```text
mcr.microsoft.com/azurelinux/base/python:3.12
sha256:9343005b72a7cc34847dcb8d09bb8a0c145311eff88c151c60d9c4904edaf6e9
```

检查了该 index 下的 `linux/amd64` 和 `linux/arm64`：

- `ca-certificates-base`：`3.0.0-19.azl3`。
- `python3-pip`：`24.2-10.azl3`。
- 系统 TLS bundle：`/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem`，包含 23 个证书。
- pip 自带的 certifi bundle 是另一份独立证书库，不能与系统 CA 库混为一谈。

## 3. 原始错误日志

以下保留用户提供的日志文本；traceback 的缩进和方法名格式以粘贴内容为准。

```text
k logs job/43903f-download-rt8dt
Found 4 pods, using pod/43903f-download-rt8dt-cvrdb
Defaulted container "downloader" out of: downloader, sampler (init)
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable.It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
Hint: A new version of huggingface_hub (2.2.0) is available! You are using version 1.18.0.
To update, run: hf update
Fetching 28 files: 0%| | 0/28 [00:00<?, ?it/s]Still waiting to acquire lock on /models/Qwen/Qwen3-Coder-30B-A3B-Instruct/.cache/huggingface/.gitignore.lock (elapsed: 0.1 seconds)
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Fetching 28 files: 86%|████████▌ | 24/28 [01:34<00:15, 3.95s/it]
Traceback (most recent call last):
File "/usr/bin/hf", line 8, in <module>
sys.exit(main())
^^^^^^
File "/usr/lib/python3.12/site-packages/huggingface_hub/cli/hf.py", line 116, in main
app()
File "/usr/lib/python3.12/site-packages/typer/main.py", line 1152, in call
raise e
File "/usr/lib/python3.12/site-packages/typer/main.py", line 1135, in call
return get_command(self)(*args, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/click/core.py", line 1631, in call
return self.main(*args, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/typer/core.py", line 794, in main
return _main(
^^^^^^
File "/usr/lib/python3.12/site-packages/typer/core.py", line 188, in _main
rv = self.invoke(ctx)
^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/huggingface_hub/cli/_cli_utils.py", line 131, in invoke
return super().invoke(ctx)
^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/click/core.py", line 2032, in invoke
return _process_result(sub_ctx.command.invoke(sub_ctx))
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/click/core.py", line 1415, in invoke
return ctx.invoke(self.callback, **ctx.params)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/click/core.py", line 910, in invoke
return callback(*args, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/typer/main.py", line 1514, in wrapper
return callback(**use_params)
^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/huggingface_hub/cli/download.py", line 219, in download
_print_result(run_download())
^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/huggingface_hub/cli/download.py", line 181, in run_download
return snapshot_download(
^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/huggingface_hub/utils/_validators.py", line 88, in _inner_fn
return fn(*args, **kwargs)
^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/huggingface_hub/_snapshot_download.py", line 456, in snapshot_download
thread_map(
File "/usr/lib/python3.12/site-packages/tqdm/contrib/concurrent.py", line 191, in thread_map
return _executor_map(ThreadPoolExecutor, fn, *iterables, **tqdm_kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/tqdm/contrib/concurrent.py", line 163, in _executor_map
return list(ex.map(
^^^^^^^^^^^^
File "/usr/lib/python3.12/concurrent/futures/_base.py", line 619, in result_iterator
yield _result_or_cancel(fs.pop())
^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/concurrent/futures/_base.py", line 317, in _result_or_cancel
return fut.result(timeout)
^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/concurrent/futures/_base.py", line 456, in result
return self.__get_result()
^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/concurrent/futures/_base.py", line 401, in __get_result
raise self._exception
File "/usr/lib/python3.12/concurrent/futures/thread.py", line 59, in run
result = self.fn(*self.args, **self.kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/huggingface_hub/_snapshot_download.py", line 436, in _inner_hf_hub_download
hf_hub_download( # type: ignore
File "/usr/lib/python3.12/site-packages/huggingface_hub/utils/_validators.py", line 88, in _inner_fn
return fn(*args, **kwargs)
^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/huggingface_hub/file_download.py", line 998, in hf_hub_download
return _hf_hub_download_to_local_dir(
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/site-packages/huggingface_hub/file_download.py", line 1452, in _hf_hub_download_to_local_dir
_download_to_tmp_and_move(
File "/usr/lib/python3.12/site-packages/huggingface_hub/file_download.py", line 1864, in _download_to_tmp_and_move
xet_get(
File "/usr/lib/python3.12/site-packages/huggingface_hub/file_download.py", line 573, in xet_get
download_files(
ConnectionError: Network error: Request middleware error: error sending request for url (https://cas-server.xethub.hf.co/v2/reconstructions/38eada67f45ca8bdcf00d0358be2092007578c0573c622b51be28b1c39308d78)
```

## 4. 原因分析

### 4.1 Python HTTP 客户端和 Xet 不一定使用同一份 CA 库

KAITO 下载容器执行 `pip install`，随后运行 `hf download`。模型元数据、小文件和 Xet-backed 权重可能走不同的客户端路径：

```text
Python / huggingface_hub
  ├─ 元数据或普通 HTTP 下载：HTTPX / Python SSL
  └─ Xet-backed 文件：hf_xet 原生模块
                         └─ Rust reqwest / rustls-platform-verifier
                              └─ 系统信任库或显式配置的 CA bundle
```

在本次检查的 Azure Linux helper 中，系统 CA bundle 并不是 Debian Python 镜像中那份完整公共根证书集合。因此，Python 安装依赖成功、小文件下载成功，并不能证明原生 Xet TLS 路径可用。

### 4.2 Xet CAS 证书链验证失败

本次观察到 `cas-server.xethub.hf.co` 提供的证书链为：

```text
*.xethub.hf.co
  → Amazon RSA 2048 M04
    → Amazon Root CA 1（由 Starfield Services Root CA - G2 交叉签名）
```

对实际提取的镜像 CA bundle 做独立 OpenSSL 验证：

| 使用的信任库 | 结果 |
| --- | --- |
| Azure Linux helper 的系统 TLS bundle | `error 20: unable to get local issuer certificate` |
| 已检查的 Debian Python 镜像系统 CA bundle | 验证成功 |
| 独立的完整 certifi CA bundle | 验证成功 |

证书链和浮动 tag 都可能随时间变化；上述结果对应本记录日期及第 2 节的镜像 digest。这里说明的是信任链缺失，不建议通过关闭 TLS 验证来绕过。

### 4.3 哪些日志不是当前根因

- `WARNING: Running pip as the 'root' user`：警告，不是本次退出的异常。
- `A new version of huggingface_hub ... is available`：升级提示，不证明 `1.18.0` 与 Python 3.12 不兼容。
- `.gitignore.lock (elapsed: 0.1 seconds)`：短暂锁等待，后面已经推进到 24/28；末尾不是锁超时异常。
- `unauthenticated requests`：应配置 HF_TOKEN 改善限流与下载体验，但现场没有展示 401/403/429；本地也在匿名下载条件下复现失败和验证修复，不能把缺少 token 当作本次结论。
- `24/28` 是文件数量进度，不等于 86% 的模型字节数已经下载。

## 5. 受控复现与对照实验

本地环境：Azure Linux 3.0 / Python 3.12，隔离安装 `huggingface-hub==1.18.0`、`hf-xet==1.7.0`。

为了避免下载完整的数十 GB 模型，测试使用 `sshleifer/tiny-gpt2` 的 `pytorch_model.bin`：大小 **2,514,146 字节**，先通过元数据确认它是 Xet-backed 文件。

实验设计：

1. 使用实际 Azure Linux 镜像中提取的 CA bundle，而不是凭包版本猜测。
2. 为 Python HTTPX 客户端显式指定完整 certifi bundle，隔离 Python 元数据请求与 Rust Xet 信任路径。
3. 设置 `SSL_CERT_FILE` 为待测 bundle，`SSL_CERT_DIR` 为独立空目录，避免宿主机其他证书目录影响对照结果。
4. 各组使用独立 cache/local-dir；匿名访问，不使用已有 HF 凭据。

| 实验 | Xet 使用的信任库/路径 | 结果 |
| --- | --- | --- |
| A | Azure Linux 镜像系统 CA bundle，Xet 开启 | 相同形式的 `ConnectionError`，访问 `/v2/reconstructions/...` 失败 |
| B | 仅将 `SSL_CERT_FILE` 改为 `certifi==2026.10.19` 的 bundle | 下载成功，2,514,146 字节 |
| C | 保持实验 A 的 CA 设置，增加 `HF_HUB_DISABLE_XET=1` | HTTP fallback 下载成功，2,514,146 字节 |

实验 A 的 Xet 内部日志包含：

```text
failed to verify TLS certificate: invalid peer certificate: UnknownIssuer

Reqwest(reqwest::Error {
  kind: Request,
  url: "https://cas-server.xethub.hf.co/v2/reconstructions/...",
  source: ... InvalidCertificate(UnknownIssuer)
})
```

这条证据把笼统的 `Request middleware error` 进一步定位到 TLS 信任链，而不是单纯依据异常名称推断“网络不通”。

**测试范围限制**：这是小型 Xet 文件、实际镜像 CA 内容和本地客户端的受控实验，不是目标镜像在 AKS + Blob CSI PVC 上的完整 E2E。现场 hf-xet 具体版本也未从 Pod 中读取，本地复现使用的是 `1.7.0`。

### 为什么最初的 config.json smoke test 不够

此前对 Python 3.12 的兼容性测试验证了固定依赖安装、sampler 导入和 `config.json` 下载，但小型配置文件没有覆盖原生 Xet 权重下载路径。因此，“Python 3.12 能运行这些依赖”不能推导为“更换基础镜像后完整下载 Job 无需额外处理”。

## 6. 已选择的方案二：禁用原生 Xet，使用 HTTP fallback

给下载容器设置：

```yaml
env:
  - name: HF_HUB_DISABLE_XET
    value: "1"
```

必须在启动 `hf download` 的进程之前设置。它禁用的是 **HF 原生 Xet 客户端路径**，不是关闭 HTTPS/TLS 验证。HTTP fallback 仍可能访问 Hugging Face 的 CDN/bridge 域名，不应据此删除相关网络放行规则。

### 已提交的 KAITO 修改

- 分支：[security/helper-image-update-downloader](https://github.com/andyzhangx/kaito/tree/security/helper-image-update-downloader)
- Commit：[75eab044b82ed151b3927baef5a238e70fe44a28](https://github.com/andyzhangx/kaito/commit/75eab044b82ed151b3927baef5a238e70fe44a28)
- 文件：`pkg/modelmirror/download/job.go`、`pkg/modelmirror/download/job_test.go`

生成 Job 的环境变量增加：

```go
envVars := []corev1.EnvVar{
    {Name: "MODEL_ID", Value: modelID},
    // Use HTTP downloads: the helper image's system CA bundle does not
    // include the roots required by the native Xet client's CAS endpoint.
    {Name: "HF_HUB_DISABLE_XET", Value: "1"},
}
```

`sampler` 已有逻辑会复制这组共享环境变量，因此它也会继承该设置。回归测试覆盖存在/不存在 HF Secret 两种情况，并检查 downloader 和 sampler 的环境变量。

提交保留 DCO `Signed-off-by`。验证状态：

- `gofmt` 通过。
- `git diff --check` 通过。
- 本地 HTTP fallback 小文件下载实验通过。
- Go 单包测试在当前环境超时，**未声称通过**。
- 全量 `make` 检查因环境缺少 `make` 未执行，需由 CI 验证。
- 尚未在原集群验证完整模型下载成功。

### 部署和重试注意事项

仅 push controller 代码不会改变已经运行或失败的 Job。需要按现有交付流程构建/部署包含该 commit 的 controller，并通过正常重试/协调流程生成新 Job。

不要直接把现有 Job 的 Pod template 当作可自由更新的对象；其主要字段通常不可变。本记录未执行删除 Job、重建 PVC 或清理模型文件等集群操作。重试前应避免多个 downloader 同时写同一模型目录。

禁用 Xet 可能改变大模型的并发、去重、缓存和传输性能，应在完整模型上补充验证。它是当前选择的兼容性 workaround，不是证明其他网络/PVC/资源问题不存在。

## 7. 其他修复方向与安全问题区分

如果希望保留 Xet，可以为它提供经过审核、更新后的完整 CA bundle。本次验证成功的另一组配置是：

```sh
pip install -q "huggingface-hub==1.18.0" "certifi==2026.10.19"
export SSL_CERT_FILE="$(python3 -m certifi)"
# 然后执行原有 hf download 命令
```

这是备选方向，不是本次已提交的方案。测试使用的 `certifi==2026.10.19` 包含 Amazon Root CA 1，且不包含前期安全排查涉及的 `AAA Certificate Services` 和 `emSign ECC Root CA - G3`。

两个问题不要混淆：

1. **本次功能故障**：Xet 所使用的系统 CA 集合缺少所需信任链。
2. **此前安全问题**：镜像自带 pip 的 `_vendor/certifi/cacert.pem` 仍可能包含应移除的失信 CA。

`HF_HUB_DISABLE_XET=1` 不修复第二个问题。安装独立 `certifi` 也不会自动替换 pip 自带的 vendored certifi。生产方案宜构建专用 helper 镜像，预装固定依赖、验证各自实际使用的 CA 库，减少每次 Job 启动都在线安装依赖的需求。

**不要使用 `verify=False`、`curl -k` 或禁用 TLS 验证作为修复。**

## 8. 集群侧进一步确认

以下只读命令中的 namespace 需替换为实际值：

```bash
NS="your-namespace"
JOB=43903f-download-rt8dt

# 列出全部重试 Pod；kubectl logs job/... 不会汇总所有 Pod。
kubectl get pods -n "$NS" \
  -l "batch.kubernetes.io/job-name=$JOB" -o wide

kubectl logs -n "$NS" 43903f-download-rt8dt-cvrdb -c downloader
kubectl logs -n "$NS" 43903f-download-rt8dt-cvrdb -c sampler
kubectl describe job -n "$NS" "$JOB"
kubectl describe pod -n "$NS" 43903f-download-rt8dt-cvrdb

# 确认实际镜像和解析后的 digest，而不是只看浮动 tag。
kubectl get pod -n "$NS" 43903f-download-rt8dt-cvrdb \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\t"}{.image}{"\t"}{.imageID}{"\n"}{end}'
```

如果复现容器仍在运行，可以检查 Xet 日志目录，搜索 `UnknownIssuer` / `InvalidCertificate`。默认位置通常是 `/root/.cache/huggingface/xet/logs/`，但 `HF_HOME`、`HF_XET_CACHE` 等设置会改变位置。已退出的容器通常不能再 `kubectl exec`；需要保留复现容器或提前收集这些文件，不能把本地复现日志替代为现场日志。

新 Job 验收建议：

- 确认 downloader 中存在 `HF_HUB_DISABLE_XET=1`。
- 检查全部重试 Pod，而不是只看 selector 自动选中的一个。
- 完整下载目标 Qwen 模型，并观察 Job `Complete` condition。
- 验证模型权重可被后续 streamer/inference 消费。
- 记录下载时长、峰值内存和 PVC 行为，评估 HTTP fallback 的性能影响。

## 9. 参考链接

- [KAITO Model Mirror Streaming 文档](https://kaito-project.github.io/kaito/docs/model-mirror-streaming)
- [Job 生成代码（本次检查的 main revision）](https://github.com/kaito-project/kaito/blob/fed6928b6ca9bf858c3ca64fb6f879ad93ea4733/pkg/modelmirror/download/job.go)
- [禁用 Xet 的修复 commit](https://github.com/andyzhangx/kaito/commit/75eab044b82ed151b3927baef5a238e70fe44a28)
- [Hugging Face Hub 环境变量文档](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables#hfhubdisablexet)
- [本地复现所用 xet-core v1.7.0](https://github.com/huggingface/xet-core/tree/v1.7.0)
- [Azure Linux CA 证书说明](https://learn.microsoft.com/en-us/azure/azure-linux/install-certificates-aks)
