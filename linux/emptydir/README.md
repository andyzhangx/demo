## 1. create a pod with emptydir mount on Linux
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/emptydir/nginx-emptydir.yaml
```
#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-emptydir

## 2. enter the pod container to do validation

```
kubectl exec -it nginx-emptydir -- bash
root@nginx-emptydir:/# ls /mnt -lt
total 4
drwxrwxrwx 2 root root 4096 Nov 29 09:10 emptydir
```

### Notes: `empty-dir` mount path on Linux
```
/var/lib/kubelet/pods/60525791-02c9-11e9-a5d2-ee433296733c/volumes/kubernetes.io~empty-dir
```
