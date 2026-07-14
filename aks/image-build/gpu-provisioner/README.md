# Managed DALEC onboarding: `gpu-provisioner`

Component: [`Azure/gpu-provisioner`](https://github.com/Azure/gpu-provisioner) — a
Karpenter Azure provider used by [KAITO](https://github.com/kaito-project/kaito)
to create Azure VM-backed node pools for GPU workloads.

## Target MCR path

When this bundle is promoted to `aks-managed-dalec` under
`specs/aks/gpu-provisioner/`, the pipeline will publish to:

```
mcr.microsoft.com/aks/v2/gpu-provisioner:<tag>-<build>
```

Formula from the onboarding guide: `<repository>` (`aks`) → first segment,
`/v2/` injected, then `<name>` (`gpu-provisioner`).

## Files

| File                                                       | Purpose                                          |
| ---------------------------------------------------------- | ------------------------------------------------ |
| `onboard.yml`                                              | Component spec consumed by aks-managed-dalec     |
| `README.managed-dalec-azure-gpu-provisioner.portal.md`     | MCR Discovery Portal readme                      |
| `tests/test.sh`                                            | Build-validation entry point (required)          |
| `tests/core-tests/test-image.sh`                           | Container image validation helper                |
| `tests/core-tests/test-package.sh`                         | Package validation helper (no-op — no packages)  |

## Tag pattern

`gpu-provisioner` uses `vMAJOR.MINOR.PATCH` releases (e.g. `v0.4.2`). The
regex `^v\d+\.\d+\.\d+$` matches every semver tag. Adjust to
`^v0\.[3-9]\.\d+$` or similar if you want a narrower gate.

## Build target

Only `azlinux3/container` is enabled — `gpu-provisioner`'s upstream
Dockerfile uses `mcr.microsoft.com/oss/go/microsoft/golang:1.26.4` as the
builder and `gcr.io/distroless/static:nonroot` as the runtime base, both
of which are compatible with Azure Linux 3's container build environment.
No RPM/DEB output, so `--packages` is not used by the test script.

## Local sanity check

```bash
# Simulate the build-validation invocation against a staged image
./tests/test.sh --image aksmanageddalecstaging.azurecr.io/staging/xyz/aks/v2/gpu-provisioner:v0.4.2-1
```
