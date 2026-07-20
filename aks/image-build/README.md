# image-build — Managed DALEC onboarding examples

This directory holds **reference / demo** onboarding bundles for AKS-owned
components that publish container images through the **Managed DALEC**
build/sign/publish pipeline (repo: `aks-managed-dalec`).

Each subdirectory here mirrors what the corresponding directory under
`specs/<team>/<component>/` in `aks-managed-dalec` should look like, so you
can review the layout, `onboard.yml`, tests, and Discovery Portal README
together before opening the real onboarding PR against `aks-managed-dalec`.

## Layout

```
aks/image-build/
└── <component>/
    ├── onboard.yml                                           # component spec
    ├── README.managed-dalec-<team>-<component>.portal.md     # MCR discovery portal readme
    └── tests/
        ├── test.sh                                           # entry point (must be executable)
        └── core-tests/
            ├── test-image.sh
            └── test-package.sh
```

## How to promote a bundle to `aks-managed-dalec`

1. Copy `aks/image-build/<component>/` into
   `specs/<team>/<component>/` inside a fresh `aks-managed-dalec` branch.
   For AKS-owned components under `Azure/*`, `<team>` is typically `aks`,
   which yields an MCR path of `mcr.microsoft.com/aks/v2/<component>`.
2. Verify the `owners`, `mar.contactEmail`, `mar.logoUrl`, `mar.description`,
   and tag regex still match reality.
3. Open a PR against `aks-managed-dalec:main`; the onboard-detection
   pipeline will validate the schema and confirm `tests/test.sh` is present
   and executable.

## Components

| Component        | Repo                                     | MCR path (post-onboard)                          |
| ---------------- | ---------------------------------------- | ------------------------------------------------ |
| `gpu-provisioner`| https://github.com/Azure/gpu-provisioner | `mcr.microsoft.com/aks/v2/gpu-provisioner`       |

See `gpu-provisioner/` for a full working example.
