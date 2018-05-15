### Prerequisite
[Raw Block Volumes is included as an alpha feature for v1.9](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#block-block-volume-support), `--feature-gates=BlockVolume=true` (split different `feature-gates` by `,`) should be configured in following kubernetes service:
 - `kube-apiserver`: `/etc/kubernetes/manifests/kube-apiserver.yaml`
 - `kube-controller-manager`: `/etc/kubernetes/manifests/kube-controller-manager.yaml`
 - `kube-scheduler`: `/etc/kubernetes/manifests/kube-scheduler.yaml`
 - `kubelet`: `/etc/default/kubelet`

## 1. create an azuredisk Persistent Volume (PV)
 - download `pv-azuredisk-block.yaml` and modify `spec.azureDisk.diskName`, `spec.azureDisk.diskURI` fields
```
wget https://raw.githubusercontent.com/andyzhangx/demo/master/linux/block/azuredisk/pv-azuredisk-block.yaml
vi pv-azuredisk-block.yaml
kubectl create -f pv-azuredisk-block.yaml
```
## 2. create an azuredisk Persistent Volume Clain (PVC) tied to above PV
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/block/azuredisk/pvc-azuredisk-block.yaml
```

 - watch the status of PVC until its Status changed from `Pending` to `Bound`
```watch kubectl describe pvc pvc-azuredisk-block```

## 3. create a pod with azuredisk mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/block/azuredisk/nginx-pod-azuredisk-block.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-azuredisk-block```

Expected events:
```
Events:
  Type    Reason                  Age   From                               Message
  ----    ------                  ----  ----                               -------
  Normal  Scheduled               1m    default-scheduler                  Successfully assigned nginx-azuredisk-block to k8s-agentpool-17607330-0
  Normal  SuccessfulMountVolume   1m    kubelet, k8s-agentpool-17607330-0  MountVolume.SetUp succeeded for volume "default-token-j9fjr"
  Normal  SuccessfulAttachVolume  49s   attachdetach-controller            AttachVolume.Attach succeeded for volume "pv-azuredisk-block"
  Normal  SuccessfulMountVolume   14s   kubelet, k8s-agentpool-17607330-0  MapVolume.MapDevice succeeded for volume "pv-azuredisk-block" globalMapPath "/var/lib/kubelet/plugins/kubernetes.io/azure-disk/volumeDevices/block-azuredisk-test"
  Normal  SuccessfulMountVolume   14s   kubelet, k8s-agentpool-17607330-0  MapVolume.MapDevice succeeded for volume "pv-azuredisk-block" volumeMapPath "/var/lib/kubelet/pods/5354c3dc-5756-11e8-8382-000d3a0643a8/volumeDevices/kubernetes.io~azure-disk"
  Normal  Pulling                 13s   kubelet, k8s-agentpool-17607330-0  pulling image "nginx"
  Normal  Pulled                  11s   kubelet, k8s-agentpool-17607330-0  Successfully pulled image "nginx"
  Normal  Created                 11s   kubelet, k8s-agentpool-17607330-0  Created container
  Normal  Started                 11s   kubelet, k8s-agentpool-17607330-0  Started container
```

## 4. enter the pod container to do validation
```
$ kubectl exec -it nginx-azuredisk-block bash
root@nginx-azuredisk-block:~# mkfs.ext4 /dev/diskx
mke2fs 1.43.4 (31-Jan-2017)
/dev/diskx contains a ext4 file system
        last mounted on /mnt/azuredisk on Sun Apr 15 04:17:33 2018
Proceed anyway? (y,N) y
Creating filesystem with 262144 4k blocks and 65536 inodes
Filesystem UUID: 94cef150-32a6-472a-b3f3-8631039175cb
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376
```

### Tips
After creating a block device on agent node, the symlink could be like following:
```
#globalMapPath
$ sudo ls -lt /var/lib/kubelet/plugins/kubernetes.io/azure-disk/volumeDevices/block-azuredisk-test
total 0
lrwxrwxrwx 1 root root 26 May 14 09:09 5354c3dc-5756-11e8-8382-000d3a0643a8 -> /dev/disk/azure/scsi1/lun0

#volumeMapPath
$ sudo ls -lt /var/lib/kubelet/pods/5354c3dc-5756-11e8-8382-000d3a0643a8/volumeDevices/kubernetes.io~azure-disk
total 0
lrwxrwxrwx 1 root root 26 May 14 09:09 pv-azuredisk -> /dev/disk/azure/scsi1/lun0
```

#### Links
 - [Local Volume](https://kubernetes.io/docs/concepts/storage/volumes/#local)
 - [Raw Block Consumption in Kubernetes](https://github.com/kubernetes/community/blob/master/contributors/design-proposals/storage/block-block-pv.md)
