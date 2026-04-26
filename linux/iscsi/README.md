# Containerized iSCSI Target (tgtd)

A containerized iSCSI target server using `tgtd` for e2e testing.

## Build and Push

```bash
cd linux/iscsi
docker build -t andyzhangx/tgtd:latest .
docker push andyzhangx/tgtd:latest
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISK_SIZE` | `1024` | LUN size in MB |
| `IQN` | `iqn.2026-01.com.test:storage` | iSCSI target IQN |
