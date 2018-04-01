## 1. create a pod with local mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/local/nginx-pod-local.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-local

## 2. enter the pod container to do validation
kubectl exec -it nginx-local -- bash

```
$ kubectl exec -it nginx-local bash
root@nginx-local:/# df -h
Filesystem      Size  Used Avail Use% Mounted on
overlay         291G  2.9G  288G   1% /
tmpfs           3.4G     0  3.4G   0% /dev
tmpfs           3.4G     0  3.4G   0% /sys/fs/cgroup
/dev/sdb1        99G   60M   94G   1% /data
/dev/sda1       291G  2.9G  288G   1% /etc/hosts
shm              64M     0   64M   0% /dev/shm
tmpfs           3.4G   12K  3.4G   1% /run/secrets/kubernetes.io/serviceaccount
tmpfs           3.4G     0  3.4G   0% /sys/firmware
```
