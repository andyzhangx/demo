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

`gpu-provisioner` is onboarded to managed DALEC **starting from `v0.4.3`**.
Everything older (`v0.4.2` and below, all of the `v0.3.x` series) is
intentionally excluded so we don't retro-build releases that predate the
onboarding.

The include list is written as three anchored patterns:

| Pattern | Matches |
| --- | --- |
| `^v0\.4\.([3-9]|\d{2,})$` | `v0.4.3` … `v0.4.9`, `v0.4.10+` |
| `^v0\.([5-9]|\d{2,})\.\d+$` | any `v0.5.x` / `v0.6.x` / … / `v0.10.x+` |
| `^v([1-9]|\d{2,})\.\d+\.\d+$` | any future `v1.x.x` and above |

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
