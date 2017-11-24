## 1. create a pod with nfs mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/nfs/nginx-nfs.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-nfs

## 2. enter the pod container to do validation
kubectl exec -it nginx-nfs -- bash

```
root@nginx-nfs:/mnt/nfs# df -h
Filesystem      Size  Used Avail Use% Mounted on
overlay          30G  2.7G   27G  10% /
tmpfs           3.4G     0  3.4G   0% /dev
tmpfs           3.4G     0  3.4G   0% /sys/fs/cgroup
/dev/sda1        30G  2.7G   27G  10% /etc/hosts
/dev/sdb1        99G   60M   94G   1% /mnt/nfs
shm              64M     0   64M   0% /dev/shm
tmpfs           3.4G   12K  3.4G   1% /run/secrets/kubernetes.io/serviceaccount
```
