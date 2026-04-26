#!/bin/bash
set -e

DISK_SIZE=${DISK_SIZE:-1024}  # Size in MB, default 1GB
IQN=${IQN:-"iqn.2026-01.com.test:storage"}
DISK_PATH="/var/lib/iscsi/disk0.img"

mkdir -p /var/lib/iscsi

echo "Creating ${DISK_SIZE}MB disk image at ${DISK_PATH}..."
dd if=/dev/zero of="$DISK_PATH" bs=1M count="$DISK_SIZE"

echo "Starting tgtd..."
tgtd -f &
TGTD_PID=$!

# Wait for tgtd to be ready
for i in $(seq 1 10); do
    if tgtadm --lld iscsi --op show --mode sys > /dev/null 2>&1; then
        break
    fi
    echo "Waiting for tgtd to start... ($i/10)"
    sleep 1
done

echo "Configuring iSCSI target..."
tgtadm --lld iscsi --op new --mode target --tid 1 -T "$IQN"
tgtadm --lld iscsi --op new --mode logicalunit --tid 1 --lun 1 -b "$DISK_PATH"
tgtadm --lld iscsi --op bind --mode target --tid 1 -I ALL

echo "========================================="
echo "iSCSI target ready:"
echo "  IQN:  $IQN"
echo "  LUN:  1"
echo "  Disk: $DISK_PATH (${DISK_SIZE}MB)"
echo "========================================="
tgtadm --lld iscsi --op show --mode target

wait $TGTD_PID
