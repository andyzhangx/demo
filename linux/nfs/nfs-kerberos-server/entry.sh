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
krb5kdc          -P /var/run/krb5kdc.pid
kadmind          -P /var/run/kadmind.pid
sleep 1

# ---- NFS -------------------------------------------------------------------
# order matters: statd -> nfsd -> mountd -> idmapd -> svcgssd
rpc.statd  --no-notify
exportfs -rav
rpc.nfsd 8
rpc.mountd --no-nfs-version 2 --no-nfs-version 3 --debug=all &
rpc.idmapd  -f -vvv &
rpc.svcgssd -f -vvv &

echo "[entry] all services started. tailing logs."
touch /var/log/messages /var/log/gssd.log
tail -F /var/log/messages /var/log/gssd.log &

# Reap zombies + stay alive.
wait -n
echo "[entry] a child exited; sleeping to keep logs visible for inspection"
sleep infinity
