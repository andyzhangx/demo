### Prerequisite
[Raw Block Volumes is included as an alpha feature for v1.9](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#block-block-volume-support), `--feature-gates=BlockVolume=true` (split different `feature-gates` by `,`) should be configured in following kubernetes service:
 - `kube-apiserver`: `/etc/kubernetes/manifests/kube-apiserver.yaml`
 - `kube-controller-manager`: `/etc/kubernetes/manifests/kube-controller-manager.yaml`
 - `kube-scheduler`: `/etc/kubernetes/manifests/kube-scheduler.yaml`
 - `kubelet`: `/etc/default/kubelet`

## 1. create a local Persistent Volume (PV)
 - download `pv-local-block.yaml` and modify `spec.local.path`, `kubernetes.io/hostname` fields
```
wget https://raw.githubusercontent.com/andyzhangx/demo/master/linux/block/local/pv-local-block.yaml
vi pv-local-block.yaml
kubectl create -f pv-local-block.yaml
```
## 2. create a local Persistent Volume Clain (PVC) tied to above PV
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/block/local/pvc-local-block.yaml
```

 - watch the status of PVC until its Status changed from `Pending` to `Bound`
```watch kubectl describe pvc pvc-local-block```

## 3. create a pod with local mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/block/local/nginx-pod-local-block.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-local-block```

Expected events:
```
Events:
  Type    Reason                 Age   From                               Message
  ----    ------                 ----  ----                               -------
  Normal  Scheduled              5s    default-scheduler                  Successfully assigned nginx-local-block to k8s-agentpool-66825246-0
  Normal  SuccessfulMountVolume  5s    kubelet, k8s-agentpool-66825246-0  MapVolume.MapDevice succeeded for volume "pv-local-block" globalMapPath "/var/lib/kubelet/plugins/kubernetes.io~local-volume/volumeDevices/pv-local-block"
  Normal  SuccessfulMountVolume  5s    kubelet, k8s-agentpool-66825246-0  MapVolume.MapDevice succeeded for volume "pv-local-block" volumeMapPath "/var/lib/kubelet/pods/80317736-4854-11e8-b535-000d3af9f967/volumeDevices/kubernetes.io~local-volume"
  Normal  SuccessfulMountVolume  5s    kubelet, k8s-agentpool-66825246-0  MountVolume.SetUp succeeded for volume "default-token-cxk4v"
  Normal  Pulling                4s    kubelet, k8s-agentpool-66825246-0  pulling image "nginx"
  Normal  Pulled                 2s    kubelet, k8s-agentpool-66825246-0  Successfully pulled image "nginx"
  Normal  Created                2s    kubelet, k8s-agentpool-66825246-0  Created container
  Normal  Started                2s    kubelet, k8s-agentpool-66825246-0  Started container
```

## 4. enter the pod container to do validation
```
$ kubectl exec -it nginx-local-block bash
root@nginx-local-block:~# mkfs.ext4 /dev/diskx
mke2fs 1.43.4 (31-Jan-2017)
/dev/diskx contains a ext4 file system
        last mounted on /mnt/azuredisk on Sun Apr 15 04:17:33 2018
Proceed anyway? (y,N) y
Creating filesystem with 262144 4k blocks and 65536 inodes
Filesystem UUID: 94cef150-32a6-472a-b3f3-8631039175cb
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376
```

#### Links
 - [Local Volume](https://kubernetes.io/docs/concepts/storage/volumes/#local)
 - [Raw Block Consumption in Kubernetes](https://github.com/kubernetes/community/blob/master/contributors/design-proposals/storage/block-block-pv.md)
 - [sig-storage-local-static-provisioner](https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner)
 - [Kubernetes 1.14: Local Persistent Volumes GA](https://kubernetes.io/blog/2019/04/04/kubernetes-1.14-local-persistent-volumes-ga/)
