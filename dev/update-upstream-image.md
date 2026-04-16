# Update Upstream Image to registry.k8s.io

This guide covers how to promote container images from the staging GCR registry to the production `registry.k8s.io`.

## Overview

Upstream Kubernetes SIG images go through a promotion process:
1. CI builds push images to `gcr.io/k8s-staging-*`
2. Image promoter config in [k8s.io/registry.k8s.io](https://github.com/kubernetes/k8s.io/blob/main/registry.k8s.io/images/k8s-staging-sig-storage/images.yaml) defines which images/tags get promoted
3. A PR to update `images.yaml` triggers promotion to `registry.k8s.io`

## Prerequisites

```bash
# Install and authenticate gcloud CLI
gcloud auth login
```

## Step 1: Verify Staging Image Exists

Before submitting a promotion PR, verify the image and tag exist in the staging registry:

```bash
# NFS CSI driver
gcloud container images list-tags gcr.io/k8s-staging-sig-storage/nfsplugin --filter="tags:v4.13.2" --format=json

# SMB CSI driver
gcloud container images list-tags gcr.io/k8s-staging-sig-storage/smbplugin --filter="tags:v1.20.1" --format=json
```

### Other useful staging registries

```bash
# List all images in a staging project
gcloud container images list --repository=gcr.io/k8s-staging-sig-storage

# Check test-infra images
gcloud container images list-tags gcr.io/k8s-staging-test-infra/gcb-docker-gcloud

# Check specific image with all tags
gcloud container images list-tags gcr.io/k8s-staging-sig-storage/nfsplugin --format=json
```

## Step 2: Update Image Promoter Config

Edit the promotion manifest:
- **File:** [`registry.k8s.io/images/k8s-staging-sig-storage/images.yaml`](https://github.com/kubernetes/k8s.io/blob/main/registry.k8s.io/images/k8s-staging-sig-storage/images.yaml)
- **Repo:** https://github.com/kubernetes/k8s.io

Add the new tag under the corresponding image entry. Example:

```yaml
- name: nfsplugin
  dmap:
    "sha256:abc123...": ["v4.13.2"]
```

The SHA256 digest can be found from the `gcloud container images list-tags` output.

## Step 3: Submit PR

Submit a PR to [kubernetes/k8s.io](https://github.com/kubernetes/k8s.io) with the updated `images.yaml`. Once merged, the image promoter will automatically copy the image to `registry.k8s.io`.

## Verify Promotion

After the PR is merged, verify the image is available:

```bash
# Pull from production registry
docker pull registry.k8s.io/sig-storage/nfsplugin:v4.13.2
```

## Common Image Names

| Component | Staging Path | Production Path |
|-----------|-------------|-----------------|
| NFS CSI | `gcr.io/k8s-staging-sig-storage/nfsplugin` | `registry.k8s.io/sig-storage/nfsplugin` |
| SMB CSI | `gcr.io/k8s-staging-sig-storage/smbplugin` | `registry.k8s.io/sig-storage/smbplugin` |
| Azure File CSI | `gcr.io/k8s-staging-sig-storage/azurefileplugin` | `registry.k8s.io/sig-storage/azurefileplugin` |
| Azure Disk CSI | `gcr.io/k8s-staging-sig-storage/azurediskplugin` | `registry.k8s.io/sig-storage/azurediskplugin` |
| Blob CSI | `gcr.io/k8s-staging-sig-storage/blobplugin` | `registry.k8s.io/sig-storage/blobplugin` |
| CSI Provisioner | `gcr.io/k8s-staging-sig-storage/csi-provisioner` | `registry.k8s.io/sig-storage/csi-provisioner` |
| CSI Attacher | `gcr.io/k8s-staging-sig-storage/csi-attacher` | `registry.k8s.io/sig-storage/csi-attacher` |
| CSI Resizer | `gcr.io/k8s-staging-sig-storage/csi-resizer` | `registry.k8s.io/sig-storage/csi-resizer` |
| CSI Node Driver Registrar | `gcr.io/k8s-staging-sig-storage/csi-node-driver-registrar` | `registry.k8s.io/sig-storage/csi-node-driver-registrar` |
| LivenessProbe | `gcr.io/k8s-staging-sig-storage/livenessprobe` | `registry.k8s.io/sig-storage/livenessprobe` |
