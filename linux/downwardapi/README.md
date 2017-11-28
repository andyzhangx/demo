## 1. create a pod with downwardAPI mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/downwardapi/nginx-downwardapi.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-downwardapi

## 2. enter the pod container to do validation
kubectl exec -it nginx-downwardapi -- bash

```
bash-4.4# df -h
Filesystem      Size  Used Avail Use% Mounted on
overlay          30G  4.3G   25G  15% /
tmpfs           6.9G     0  6.9G   0% /dev
tmpfs           6.9G     0  6.9G   0% /sys/fs/cgroup
tmpfs           6.9G  8.0K  6.9G   1% /etc
/dev/sda1        30G  4.3G   25G  15% /dev/termination-log
shm              64M     0   64M   0% /dev/shm
tmpfs           6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount
bash-4.4# cd /etc/
bash-4.4# ls -lt
total 0
lrwxrwxrwx 1 0 0 18 Nov 28 07:34 annotations -> ..data/annotations
lrwxrwxrwx 1 0 0 13 Nov 28 07:34 labels -> ..data/labels

bash-4.4# cat annotations
build="two"
builder="john-doe"
kubernetes.io/config.seen="2017-11-28T07:34:44.970813914Z"

kubernetes.io/config.source="api"bash-4.4# cat labels
cluster="test-cluster1"
rack="rack-22"
```
