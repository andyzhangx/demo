#!/usr/bin/env bash
# specs/aks/gpu-provisioner/tests/core-tests/test-package.sh
#
# gpu-provisioner is a container-only component — it produces no RPM/DEB
# artifacts today. The build-validation pipeline will only ever pass
# --packages to us if a package target is enabled in onboard.yml, and we
# do not enable one.
#
# This helper is kept as a placeholder so:
#   - tests/test.sh can call it unconditionally without special-casing,
#   - and adding a package target later (e.g. azlinux3/rpm) is a one-file
#     edit rather than a directory-shape change.

set -euo pipefail

PACKAGES=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --packages)
            PACKAGES="${2:-}"
            shift 2
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [[ -z "${PACKAGES}" ]]; then
    echo "error: --packages is required" >&2
    exit 2
fi

echo "[test-package] gpu-provisioner produces no packages; skipping ${PACKAGES}"
exit 0
