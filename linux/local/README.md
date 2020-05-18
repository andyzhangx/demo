## 1. create a local Persistent Volume (PV)
 - download `pv-local.yaml` and modify `spec.local.path`, `kubernetes.io/hostname` fields
```
wget https://raw.githubusercontent.com/andyzhangx/demo/master/linux/local/pv-local.yaml
vi pv-local.yaml
kubectl create -f pv-local.yaml
```
## 2. create a local Persistent Volume Clain (PVC) tied to above PV
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/local/pvc-local.yaml
```

## 3. create a pod with local mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/local/nginx-pod-local.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-local```

## 4. enter the pod container to do validation
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

#### Links
 - [Local Volume](https://kubernetes.io/docs/concepts/storage/volumes/#local)
 - [sig-storage-local-static-provisioner](https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner)
 - [Kubernetes 1.14: Local Persistent Volumes GA](https://kubernetes.io/blog/2019/04/04/kubernetes-1.14-local-persistent-volumes-ga/)
