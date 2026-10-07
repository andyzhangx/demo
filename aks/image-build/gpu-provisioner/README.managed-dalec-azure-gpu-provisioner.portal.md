# GPU Provisioner (managed DALEC)

## About

**GPU Provisioner** is a [Karpenter](https://karpenter.sh/) Azure provider
that dynamically creates Azure VM-backed node pools on demand. It is the
node-provisioning engine used by
[KAITO](https://github.com/kaito-project/kaito) to spin up GPU nodes for
large-language-model inference and fine-tuning workloads on Azure
Kubernetes Service (AKS).

Upstream source: <https://github.com/Azure/gpu-provisioner>

## Featured tags

```bash
docker pull mcr.microsoft.com/aks/v2/gpu-provisioner:v0.4.3-1
```

Tags follow the `<upstream-semver>-<managed-dalec-build>` convention;
the `-1` suffix is bumped every time managed DALEC re-builds the same
upstream release. Managed DALEC onboarding started at upstream `v0.4.3`;
older tags (`v0.4.2` and earlier) are not published under this path.

## Usage

`gpu-provisioner` is a Kubernetes controller and is expected to run
inside a cluster with a Karpenter-compatible RBAC surface. It is
usually deployed via the KAITO Helm chart, which wires up the CRDs,
service account, and Azure identity that the controller requires.

```bash
# Sanity-check the image outside a cluster
docker run --rm mcr.microsoft.com/aks/v2/gpu-provisioner:v0.4.3-1 --help
```

For an end-to-end AKS deployment example, see the KAITO installation
guide: <https://github.com/kaito-project/kaito#installation>.

## Support

- Issues / feature requests: <https://github.com/Azure/gpu-provisioner/issues>
- Team contact: `aks-core@microsoft.com`
- KAITO-side integration: <https://github.com/kaito-project/kaito>

## License

`gpu-provisioner` is released under the
[Apache-2.0 license](https://github.com/Azure/gpu-provisioner/blob/main/LICENSE).
