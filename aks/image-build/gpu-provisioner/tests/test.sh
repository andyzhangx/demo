#!/usr/bin/env bash
# specs/aks/gpu-provisioner/tests/test.sh
#
# Entry point invoked by the aks-managed-dalec build-validation pipeline.
#
# The pipeline calls this script with a subset of:
#   --image    <full ACR path to the staged container image>
#   --packages <local path to package artifacts>
#
# gpu-provisioner only produces container images (azlinux3/container),
# so we expect --image and no --packages.
#
# Exit code:
#   0  -> tests passed
#   !0 -> tests failed (fails the pipeline)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="${SCRIPT_DIR}/core-tests"

IMAGE=""
PACKAGES=""

usage() {
    cat <<'EOF'
Usage: test.sh [--image <acr-image-ref>] [--packages <path-to-packages>]

At least one of --image or --packages must be provided.
EOF
    exit 2
}

# ---- argument parsing --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)
            IMAGE="${2:-}"
            shift 2
            ;;
        --packages)
            PACKAGES="${2:-}"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "unknown argument: $1" >&2
            usage
            ;;
    esac
done

if [[ -z "${IMAGE}" && -z "${PACKAGES}" ]]; then
    echo "error: at least one of --image or --packages must be provided" >&2
    usage
fi

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

fail() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] FAIL: $*" >&2
    exit 1
}

# ---- run image tests ---------------------------------------------------------
if [[ -n "${IMAGE}" ]]; then
    log "validating container image: ${IMAGE}"
    if [[ ! -x "${CORE_DIR}/test-image.sh" ]]; then
        fail "core-tests/test-image.sh is missing or not executable"
    fi
    "${CORE_DIR}/test-image.sh" --image "${IMAGE}" || fail "container image validation failed"
    log "container image validation OK"
fi

# ---- run package tests -------------------------------------------------------
if [[ -n "${PACKAGES}" ]]; then
    log "validating packages under: ${PACKAGES}"
    if [[ ! -x "${CORE_DIR}/test-package.sh" ]]; then
        fail "core-tests/test-package.sh is missing or not executable"
    fi
    "${CORE_DIR}/test-package.sh" --packages "${PACKAGES}" || fail "package validation failed"
    log "package validation OK"
fi

log "all requested tests passed"
exit 0
