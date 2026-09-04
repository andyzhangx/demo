# Gantry vs DACS and KAITO model distribution paths

This note summarizes the analysis of whether [Gantry](https://unbounded-cloud.io/guides/gantry/) is similar to the DACS integration documented in [`enable-dacs-in-kaito-workspace.md`](./enable-dacs-in-kaito-workspace.md), whether it can replace DACS, and how KAITO could use OCI artifacts for model distribution.

## Short answer

- **Gantry and DACS are directionally similar** in that both try to reduce repeated downloads across nodes.
- **They are not the same layer of the stack**:
  - **Gantry** accelerates **OCI image/layer pulls** at the **containerd / registry** layer.
  - **DACS integration in KAITO** aims to accelerate **model-weight access / caching** at the **inference runtime** layer.
- Therefore, **Gantry cannot directly replace DACS** for KAITO model-weight caching/loading.
- If KAITO wants to benefit from OCI-registry-style distribution for model weights, the practical path is:
  1. mirror/package Hugging Face model files into an **OCI artifact** in **ACR** (or another OCI registry),
  2. use an **initContainer + ORAS** to pull the artifact onto a PVC/local disk,
  3. let the inference container load the model from that local path.

---

## 1. What Gantry does

According to <https://unbounded-cloud.io/guides/gantry/>:

- Gantry is a **peer-to-peer containerd registry mirror**.
- It runs as a **DaemonSet**.
- It accelerates **OCI image / layer** distribution.
- It uses each node's existing **containerd content store**.
- Peer discovery is via **libp2p + DHT**.
- `containerd` still validates content digests before use.

### Pull path with Gantry

1. `containerd` resolves an image tag at the origin registry.
2. It gets a content digest.
3. The node-local Gantry agent checks whether a peer already has the digest.
4. One or a few nodes fetch from origin.
5. Other nodes fetch the same content from peers.
6. `containerd` stores the blobs in the node-local content store.

So Gantry optimizes **image pull traffic** for:

- base images
- sidecar images
- initContainer images
- OCI layers/blobs pulled by `containerd`

It does **not** automatically optimize application-level downloads that happen *inside* a running container.

---

## 2. What the DACS integration in KAITO is trying to do

From [`enable-dacs-in-kaito-workspace.md`](./enable-dacs-in-kaito-workspace.md), the DACS path is intended to inject cache-aware runtime behavior into inference pods.

### Signals from the current DACS integration

The documented integration adds or depends on:

- feature gate: `distributedCache=true`
- controller env such as:
  - `DACS_DISCOVERY_ENDPOINT`
  - `DACS_KV_CONNECTOR_PROTOCOL`
  - `DACS_CLIENT_IMAGE`
- workload-side injected env such as:
  - `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_ENABLED=true`
  - `RUNAI_STREAMER_EXPERIMENTAL_AZURE_CACHE_LIB=...libStorageDirect.so`
  - `CACHE_DISCOVERY_URL=...`
  - `LD_LIBRARY_PATH=...`
- an injected `ImageVolume` containing the `dacs-client` image

This means the DACS path is operating at the **model loading / runtime access** layer, not the registry layer.

### Important current finding from the DACS test doc

The current test result in that doc shows that even when DACS injection looked enabled, the inference container still used:

- `--model=microsoft/phi-4`
- `--download-dir=/workspace/weights`
- `--load_format=auto`

and the logs showed direct **Hugging Face download** into `/workspace/weights`.

So the currently documented DACS path appears to be **experimental / incomplete**:

- there was a `glibc` / `LD_LIBRARY_PATH` compatibility problem,
- and there is evidence of **silent fallback to normal HF download** instead of true cache-backed model loading.

That does **not** make Gantry a replacement; it just means the current DACS path is not yet a robust default.

---

## 3. Why Gantry cannot directly replace DACS

### Core reason: different interception point

#### Gantry intercepts

- `image: ...`
- kubelet -> containerd -> registry traffic
- OCI image/layer transfer

#### DACS tries to accelerate

- model downloads / model reads after the container has started
- vLLM / transformers / streamer runtime I/O
- paths like:
  - Hugging Face repo download
  - local mounted weights
  - `az://...` style model streaming

These are **different planes**.

### Practical consequence

If vLLM downloads model weights from Hugging Face from inside the container, Gantry does **not** see or accelerate that traffic.

Therefore:

- **Gantry helps with container image distribution**.
- **DACS aims to help with model-weight distribution/loading**.
- **One is not a drop-in replacement for the other.**

---

## 4. How KAITO could use OCI artifacts for model weights

KAITO already has a proposal and partial tooling for this direction:

- `docs/proposals/20250609-model-as-oci-artifacts.md`
- `website/docs/model-as-oci-artifacts.md`
- `docker/presets/models/tfs/build_oci_artifact.sh`

### Intended model-as-OCI-artifacts flow

1. **Source model files from Hugging Face**
2. **Package them into an OCI artifact**
3. **Push the artifact to an OCI registry**
4. **At runtime, use an initContainer to pull the artifact to a PVC/local disk**
5. **Start the inference container and load the model from the local path**

### Important clarification

The image `ghcr.io/kaito-project/aikit/aikit:latest` is used as a **builder/packager frontend**, not as the runtime image that directly serves or downloads the model in the inference pod.

The existing script shows the packaging side:

- take a Hugging Face source like:
  - `huggingface://org/repo@revision`
- build OCI layout / artifact using AIKit tooling
- push it to a registry using `oras cp`

### Runtime pull model

At runtime, the inference pod would typically need an **initContainer** running an OCI artifact client such as **ORAS**:

```bash
oras pull <registry>/<repo>:<tag> -o /workspace/weights
```

Then the main container would use:

- `--model=/workspace/weights/<model-dir>`

instead of:

- `--model=<huggingface-repo-id> --download-dir=/workspace/weights`

### Why this matters

This is the cleanest way to make model distribution look more like enterprise artifact distribution while still letting the inference runtime load **local files**.

---

## 5. Where should the OCI artifact be stored?

### Recommendation: ACR

For AKS/KAITO, the most natural registry for model OCI artifacts is **ACR**.

Why ACR:

- aligns naturally with Azure / AKS environments
- better enterprise control than pulling directly from Hugging Face in production
- registry auth / RBAC / network path are easier to integrate in Azure environments
- keeps model distribution inside the same operational boundary as the cluster

Example artifact reference:

```text
myregistry.azurecr.io/kaito-models/phi-4:model
```

The runtime initContainer could then pull:

```bash
oras pull myregistry.azurecr.io/kaito-models/phi-4:model -o /workspace/weights
```

### Could it be stored somewhere else?

Yes, any OCI-artifact-capable registry could work in principle, such as:

- ACR
- GHCR
- Harbor
- another enterprise OCI registry

But for AKS/KAITO, **ACR is the best default choice**.

---

## 6. Does Hugging Face itself support OCI artifacts as the runtime registry?

### Short answer

**Do not assume so for this design.**

Hugging Face is the **model source**, but not the natural target for KAITO's OCI-artifact distribution design.

### Why

Hugging Face model hosting is primarily:

- model repository hosting
- Git/LFS + Hub APIs
- file downloads by repo/revision

KAITO's OCI artifact design expects:

- OCI distribution semantics
- artifact manifests / layers / media types
- `oras push/pull` style registry behavior

So the clean architecture is:

```text
Hugging Face model repo
  -> package/mirror
  -> OCI artifact in ACR
  -> initContainer ORAS pull
  -> local PVC/disk
  -> vLLM loads local files
```

In other words:

- **HF is the source of model files**
- **ACR is the OCI artifact distribution backend**

---

## 7. Why Gantry still does not solve the OCI-artifact model path automatically

This is a subtle but important point.

If the runtime path is:

```bash
oras pull myregistry.azurecr.io/kaito-models/phi-4:model
```

then the model artifact is being pulled by **ORAS inside the initContainer**, not by the node's normal `containerd image pull` path.

That means:

- Gantry may still help with the **initContainer image itself**,
- but it does **not automatically accelerate the ORAS artifact download** in the same way it accelerates normal image-layer pulls.

So even with OCI artifacts, Gantry is **not automatically the solution** unless the model distribution path is redesigned to use a runtime-native OCI mounting/pull flow that the container runtime itself can manage.

---

## 8. Comparison of KAITO model distribution paths

| Path | Model location | Access pattern | Current KAITO fit | Main advantages | Main limits |
|---|---|---|---|---|---|
| Hugging Face direct download | Hugging Face Hub | main container downloads to `/workspace/weights` | high | simplest, no pre-mirroring | cold start slow; repeated downloads |
| PVC-backed HF download | PVC / NVMe / Azure Disk / `emptyDir` | same HF download path, but persisted to chosen volume | high | practical, easy improvement over pure `emptyDir` | still download-first; duplicates across replicas |
| Local baked weights | node local disk (`/opt/kaito/models/...`) | hostPath mount + local load | supported | fastest startup | image/pool maintenance burden |
| Blob + ModelMirror / streaming | Azure Blob / RWX storage | mirror first, then stream/load via `az://...` | strong design direction | good for large models, more shareable | more infra/auth complexity |
| OCI artifact in ACR | ACR / OCI registry | initContainer `oras pull` to local volume | proposal/tooling exists | enterprise-friendly artifact distribution | requires packaging + runtime initContainer + auth |
| DACS integration | distributed cache system | injected cache-aware runtime path | experimental in current doc | potential runtime acceleration | current doc shows compatibility + fallback issues |
| Gantry | node `containerd` content store | P2P acceleration for OCI image/layer pulls | orthogonal | great for image distribution | not a direct model-weight caching solution |

---

## 9. Practical recommendation for KAITO

If the goal is to make KAITO model delivery more production-friendly without depending on the current experimental DACS path, a pragmatic priority order is:

### Near term

1. **Make classic model-weights PVC storage configurable**
   - e.g. support Azure Disk or cluster-default StorageClass for `/workspace/weights`
   - this improves the ordinary download path without changing the model source

2. **Keep local baked weights as the fastest option for fixed-model pools**

3. **Continue investing in ModelMirror / streaming for large-model production paths**

### Medium term

4. **Add OCI artifact support backed by ACR**
   - package HF models into OCI artifacts
   - pull them via initContainer + ORAS
   - load locally from PVC/NVMe/Azure Disk

### Avoid incorrect substitution

5. **Do not treat Gantry as a direct DACS replacement**
   - Gantry is useful, but for the image-distribution problem, not the runtime model-weight caching problem

---

## 10. Final conclusion

### Is Gantry similar to DACS?

**Only at a high-level goal.** Both try to reduce redundant data movement across nodes.

### Can Gantry replace DACS in KAITO?

**Not directly.** They act at different layers:

- Gantry: OCI image distribution layer
- DACS: model-weight runtime/cache layer

### If KAITO wants OCI-based model distribution, what should it do?

Use this flow:

1. take model files from Hugging Face,
2. package them into OCI artifacts,
3. store them in **ACR**,
4. pull them via **ORAS initContainer** to a local volume,
5. let the inference container load from the local filesystem.

### Does Hugging Face itself serve as the OCI artifact backend here?

**No, not for this design.** Hugging Face should be treated as the source repository, while **ACR** should be treated as the OCI artifact registry for AKS/KAITO.
