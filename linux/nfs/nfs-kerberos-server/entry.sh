#!/usr/bin/env bash
# entry.sh — start rpcbind, KDC, kadmin, nfsd, mountd, svcgssd. PID 1.
set -euo pipefail

/init.sh

# rpc_pipefs is required by rpc.svcgssd + rpc.idmapd on modern kernels.
if ! mountpoint -q /var/lib/nfs/rpc_pipefs; then
    mount -t rpc_pipefs sunrpc /var/lib/nfs/rpc_pipefs || echo "[entry] warn: rpc_pipefs mount failed (need CAP_SYS_ADMIN)"
fi
if ! mountpoint -q /proc/fs/nfsd; then
    mount -t nfsd nfsd /proc/fs/nfsd || echo "[entry] warn: nfsd mount failed (need CAP_SYS_ADMIN)"
fi

# ---- rpcbind ---------------------------------------------------------------
rpcbind -w
sleep 1

# ---- KDC + kadmind ---------------------------------------------------------
# Run in the foreground (-n / -nofork) so their PIDs are shell children of
# this script and `wait -n` below can detect a crash. Otherwise the daemons
# fork away, `wait -n` never sees them, and a dead KDC would leave the pod
# looking healthy while every Kerberos mount fails.
krb5kdc -n &
KDC_PID=$!
kadmind -nofork &
KADMIND_PID=$!
sleep 1

# ---- NFS -------------------------------------------------------------------
# order matters: statd -> nfsd -> mountd -> idmapd -> svcgssd
#
# All long-running daemons stay in the FOREGROUND (-F / -f / -n / -nofork)
# so that if any one of them dies, `wait -n` returns and we exit with a
# non-zero status. That lets Kubernetes restart the pod instead of us
# silently sleeping on top of a broken server. `rpc.mountd` and `rpc.statd`
# default to daemonizing, hence -F / -F.
rpc.statd -F --no-notify &
STATD_PID=$!
exportfs -rav
rpc.nfsd 8
rpc.mountd -F --no-nfs-version 2 --no-nfs-version 3 --debug=all &
MOUNTD_PID=$!
rpc.idmapd  -f -vvv &
IDMAPD_PID=$!
rpc.svcgssd -f -vvv &
SVCGSSD_PID=$!

echo "[entry] all services started (kdc=${KDC_PID} kadmind=${KADMIND_PID} statd=${STATD_PID} mountd=${MOUNTD_PID} idmapd=${IDMAPD_PID} svcgssd=${SVCGSSD_PID}). tailing logs."
touch /var/log/messages /var/log/gssd.log
tail -F /var/log/messages /var/log/gssd.log &

# Wait for the FIRST monitored daemon to exit, then exit non-zero so that
# Kubernetes restarts the container. Do NOT sleep infinity here — that would
# mask failures of any monitored daemon behind a healthy-looking PID 1.
set +e
wait -n "${KDC_PID}" "${KADMIND_PID}" "${STATD_PID}" \
        "${MOUNTD_PID}" "${IDMAPD_PID}" "${SVCGSSD_PID}"
RC=$?
echo "[entry] a monitored daemon exited (rc=${RC}); shutting down for Kubernetes to restart us"
exit "${RC}"
