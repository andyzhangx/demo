#!/usr/bin/env bash
# specs/aks/gpu-provisioner/tests/core-tests/test-image.sh
#
# Container image validation for gpu-provisioner.
#
# Contract:
#   - Pulls the staged image from ACR
#   - Verifies the manager binary is present in the layer
#   - Runs the binary with `--help` to make sure the entrypoint is wired up
#     and the process doesn't crash immediately (e.g., missing shared libs,
#     wrong architecture, corrupted binary).
#
# The upstream Dockerfile builds a distroless image with a single ENTRYPOINT
# of `/manager`, so we lean on that here.

set -euo pipefail

IMAGE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)
            IMAGE="${2:-}"
            shift 2
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [[ -z "${IMAGE}" ]]; then
    echo "error: --image is required" >&2
    exit 2
fi

log() { echo "[test-image] $*"; }

# ---- pull --------------------------------------------------------------------
log "docker pull ${IMAGE}"
docker pull "${IMAGE}"

# ---- inspect -----------------------------------------------------------------
# Distroless runtime uses uid 65532 (nonroot) — make sure the runtime user
# didn't regress to root, which would fail our security bar.
USER_UID="$(docker inspect --format '{{.Config.User}}' "${IMAGE}")"
log "image runtime user: ${USER_UID}"
if [[ "${USER_UID}" != "65532:65532" && "${USER_UID}" != "65532" ]]; then
    echo "error: expected non-root user 65532, got '${USER_UID}'" >&2
    exit 1
fi

ENTRYPOINT_JSON="$(docker inspect --format '{{json .Config.Entrypoint}}' "${IMAGE}")"
log "image entrypoint: ${ENTRYPOINT_JSON}"
if [[ "${ENTRYPOINT_JSON}" != *"/manager"* ]]; then
    echo "error: expected entrypoint to invoke /manager, got '${ENTRYPOINT_JSON}'" >&2
    exit 1
fi

# ---- smoke-run ---------------------------------------------------------------
# `--help` on the karpenter operator prints flag docs and exits 0.
log "running '${IMAGE} --help' to smoke-test the entrypoint"
if ! docker run --rm --network=none "${IMAGE}" --help; then
    echo "error: gpu-provisioner --help exited non-zero" >&2
    exit 1
fi

log "container image validation succeeded"
exit 0
