## 1. create a pod with hostpath mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/hostpath/nginx-hostpath.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-hostpath

## 2. enter the pod container to do validation
kubectl exec -it nginx-hostpath -- bash

```
root@nginx-hostpath:/mnt/hostpath# df -h
Filesystem      Size  Used Avail Use% Mounted on
overlay          30G  2.7G   27G  10% /
tmpfs           3.4G     0  3.4G   0% /dev
tmpfs           3.4G     0  3.4G   0% /sys/fs/cgroup
/dev/sda1        30G  2.7G   27G  10% /etc/hosts
/dev/sdb1        99G   60M   94G   1% /mnt/hostpath
shm              64M     0   64M   0% /dev/shm
tmpfs           3.4G   12K  3.4G   1% /run/secrets/kubernetes.io/serviceaccount
```

#### Known issues
 - [Containerized kubelet won't start pods with host path volumes that contains type field](https://github.com/kubernetes/kubernetes/issues/61801) 
**error logs**:
```
Events:
  Type     Reason                 Age               From                   Message
  ----     ------                 ----              ----                   -------
  Normal   SuccessfulMountVolume  1m                kubelet, 20941k8s9010  MountVolume.SetUp succeeded for volume "csi-dysk-token-j4t9h"
  Warning  FailedMount            57s (x7 over 1m)  kubelet, 20941k8s9010  MountVolume.SetUp failed for volume "mountpoint-dir" : hostPath type check failed: /var/lib/kubelet/pods is not a directory
  Warning  FailedMount            24s (x8 over 1m)  kubelet, 20941k8s9010  MountVolume.SetUp failed for volume "plugin-dir" : hostPath type check failed: /var/lib/kubelet/plugins/csi-dysk is not a directory
```

**Fix**
 - PR [fix nsenter GetFileType issue in containerized kubelet](https://github.com/kubernetes/kubernetes/pull/62467) fixed this issue
 
| k8s version | fixed version |
| ---- | ---- |
| v1.8 | no such issue |
| v1.9 | 1.9.7 |
| v1.10 | in cherry-pick |
