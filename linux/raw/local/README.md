## 1. create a local Persistent Volume (PV)
 - download `pv-local-raw.yaml` and modify `spec.local.path`, `kubernetes.io/hostname` fields
```
wget https://raw.githubusercontent.com/andyzhangx/demo/master/linux/local/pv-local-raw.yaml
vi pv-local-raw.yaml
kubectl create -f pv-local-raw.yaml
```
## 2. create a local Persistent Volume Clain (PVC) tied to above PV
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/local/pvc-local-raw.yaml
```

## 3. create a pod with local mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/local/nginx-pod-local-raw.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-local-raw```

Expected events:
```
Events:
  Type    Reason                 Age   From                               Message
  ----    ------                 ----  ----                               -------
  Normal  Scheduled              5s    default-scheduler                  Successfully assigned nginx-local-raw to k8s-agentpool-66825246-0
  Normal  SuccessfulMountVolume  5s    kubelet, k8s-agentpool-66825246-0  MapVolume.MapDevice succeeded for volume "pv-local-raw" globalMapPath "/var/lib/kubelet/plugins/kubernetes.io~local-volume/volumeDevices/pv-local-raw"
  Normal  SuccessfulMountVolume  5s    kubelet, k8s-agentpool-66825246-0  MapVolume.MapDevice succeeded for volume "pv-local-raw" volumeMapPath "/var/lib/kubelet/pods/80317736-4854-11e8-b535-000d3af9f967/volumeDevices/kubernetes.io~local-volume"
  Normal  SuccessfulMountVolume  5s    kubelet, k8s-agentpool-66825246-0  MountVolume.SetUp succeeded for volume "default-token-cxk4v"
  Normal  Pulling                4s    kubelet, k8s-agentpool-66825246-0  pulling image "nginx"
  Normal  Pulled                 2s    kubelet, k8s-agentpool-66825246-0  Successfully pulled image "nginx"
  Normal  Created                2s    kubelet, k8s-agentpool-66825246-0  Created container
  Normal  Started                2s    kubelet, k8s-agentpool-66825246-0  Started container
```

## 4. enter the pod container to do validation
```
$ kubectl exec -it nginx-local-raw bash
root@nginx-local-raw:~# mkfs.ext4 /dev/diskx
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
 - [Raw Block Consumption in Kubernetes](https://github.com/kubernetes/community/blob/master/contributors/design-proposals/storage/raw-block-pv.md)
