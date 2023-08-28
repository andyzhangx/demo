#/bin/bash

# Refer to https://learn.microsoft.com/en-us/azure/azure-netapp-files/performance-linux-nfs-read-ahead#how-to-persistently-set-read-ahead-for-nfs-mounts
# for more information on how to set read ahead for NFS mounts

READ_AHEAD_KB=$1
if [ -z "$READ_AHEAD_KB" ]; then
  READ_AHEAD_KB=16384
fi

echo "Setting read ahead to $READ_AHEAD_KB KB..."

cat <<EOF | kubectl apply -f -
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: set-read-ahead-kb
data:
  set-read-ahead-kb.sh: |-
    #!/bin/sh
    AWK_PATH=\$(which awk) 
    cat > /host/etc/udev/rules.d/99-nfs.rules <<EOF
    SUBSYSTEM=="bdi", ACTION=="add", PROGRAM="\$AWK_PATH -v bdi=\\\$kernel 'BEGIN{ret=1} {if (\\\$4 == bdi){ret=0}} END{exit ret}' /proc/fs/nfsfs/volumes", ATTR{read_ahead_kb}="$READ_AHEAD_KB"
    EOF
    nsenter --mount=/proc/1/ns/mnt udevadm control --reload
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: set-read-ahead-kb
spec:
  selector:
    matchLabels:
      app: set-read-ahead-kb
  template:
    metadata:
      labels:
        app: set-read-ahead-kb
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      hostPID: true
      initContainers:
      - name: set-read-ahead-kb
        image: alpine
        command: 
        - /set-read-ahead-kb.sh
        securityContext:
          privileged: true
        volumeMounts:
        - name: host-etc
          mountPath: /host/etc
        - name: config
          mountPath: /set-read-ahead-kb.sh
          readOnly: true
          subPath: set-read-ahead-kb.sh
      containers:
      - name: sleep
        image: alpine
        command: ["/bin/sh", "-c", "sleep infinity"]
      volumes:
        - name: host-etc
          hostPath:
            path: /etc
        - name: config
          configMap:
            defaultMode: 0700
            name: set-read-ahead-kb
EOF

#kubectl wait --for=condition=ready pod -l app=set-read-ahead-kb
#kubectl delete ds set-read-ahead-kb
#kubectl delete cm set-read-ahead-kb
