## Azure disk attach/detach stress test with Deployment
#### Prerequisite
 - [create an azure disk storage class if hdd does not exist](https://github.com/andyzhangx/demo/tree/master/linux/azuredisk#1-create-an-azure-disk-storage-class-if-hdd-does-not-exist)

### 1. Let k8s schedule all pods on one node by `kubectl cordon NODE-NAME`

### 2. Set up a few Deployments with azure disk mount on a node#1
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk1.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk2.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk3.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk4.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk5.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk6.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk7.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk8.yaml
```

### 3. Let k8s schedule all pods on node#2
```
kubectl cordon node#2
kubectl drain node#1 --ignore-daemonsets --delete-local-data
```

### 4. Watch the pod scheduling process
```
watch kubectl get po -o wide
```

#### Note
 - In my testing#1(on region westus2), I scheduled 3 pods with azure disk mount on one node, it took around **3 min** for scheduling all three pods from node#1 to node#2 (After fix in v1.9.7, it took about 1 min for scheduling azure disk mount from one node to another, details: 
https://github.com/kubernetes/kubernetes/issues/62282#issuecomment-380794459)
```
Events:
  Type     Reason                 Age   From                               Message
  ----     ------                 ----  ----                               -------
  Normal   Scheduled              3m    default-scheduler                  Successfully assigned deployment-azuredisk1-6cd8bc7945-kbkvz to k8s-agentpool-88970029-0
  Warning  FailedAttachVolume     3m    attachdetach-controller            Multi-Attach error for volume "pvc-6f2d0788-3b0b-11e8-a378-000d3afe2762" Volume is already exclusively attached to one node and can't be attached to another
  Normal   SuccessfulMountVolume  3m    kubelet, k8s-agentpool-88970029-0  MountVolume.SetUp succeeded for volume "default-token-qt7h6"
  Warning  FailedMount            1m    kubelet, k8s-agentpool-88970029-0  Unable to mount volumes for pod "deployment-azuredisk1-6cd8bc7945-kbkvz_default(5346c040-3e4c-11e8-a378-000d3afe2762)": timeout expired waiting for volumes to attach/mount for pod "default"/"deployment-azuredisk1-6cd8bc7945-kbkvz". list of unattached/unmounted volumes=[azuredisk]
  Normal   SuccessfulMountVolume  1m    kubelet, k8s-agentpool-88970029-0  MountVolume.SetUp succeeded for volume "pvc-6f2d0788-3b0b-11e8-a378-000d3afe2762"
  Normal   Pulling                45s   kubelet, k8s-agentpool-88970029-0  pulling image "nginx"
  Normal   Pulled                 44s   kubelet, k8s-agentpool-88970029-0  Successfully pulled image "nginx"
  Normal   Created                44s   kubelet, k8s-agentpool-88970029-0  Created container
  Normal   Started                42s   kubelet, k8s-agentpool-88970029-0  Started container
```

 - In my testing#2(on region eastus with k8s v1.11.2), I rescheduled 4 pods with azure disk mount on one node to another, it costs about **4 min**
```
Events:
  Type     Reason                  Age   From                               Message
  ----     ------                  ----  ----                               -------
  Normal   Scheduled               4m    default-scheduler                  Successfully assigned default/deployment-azuredisk3-68959c48c4-rc88k to k8s-agentpool-34076307-1
  Warning  FailedAttachVolume      4m    attachdetach-controller            Multi-Attach error for volume "pvc-9e5b732a-b7f3-11e8-a9e9-000d3a107fa7" Volume is already used by pod(s) deployment-azuredisk3-68959c48c4-7jlt8
  Warning  FailedMount             2m    kubelet, k8s-agentpool-34076307-1  Unable to mount volumes for pod "deployment-azuredisk3-68959c48c4-rc88k_default(0ac0a5d3-b7f4-11e8-a9e9-000d3a107fa7)": timeout expired waiting for volumes to attach or mount for pod "default"/"deployment-azuredisk3-68959c48c4-rc88k". list of unmounted volumes=[azuredisk]. list of unattached volumes=[azuredisk default-token-hdhnv]
  Normal   SuccessfulAttachVolume  1m    attachdetach-controller            AttachVolume.Attach succeeded for volume "pvc-9e5b732a-b7f3-11e8-a9e9-000d3a107fa7"
  Normal   Pulling                 3s    kubelet, k8s-agentpool-34076307-1  pulling image "nginx"
  Normal   Pulled                  3s    kubelet, k8s-agentpool-34076307-1  Successfully pulled image "nginx"
  Normal   Created                 2s    kubelet, k8s-agentpool-34076307-1  Created container
  Normal   Started                 2s    kubelet, k8s-agentpool-34076307-1  Started container
```

 - In my testing#3(on region eastus with k8s v1.11.2), I rescheduled 8 pods with azure disk mount on one node to another, it costs about **6 min**
```
Every 2.0s: kubectl get po -o wide                                                                                                                                                     Fri Sep 14 08:11:21 2018

NAME                                     READY     STATUS    RESTARTS   AGE       IP            NODE                       NOMINATED NODE
deployment-azuredisk1-bccc7c5d8-k4q5j    1/1       Running   0          6m        10.240.0.16   k8s-agentpool-34076307-0   <none>
deployment-azuredisk2-697d798b57-tjr4m   1/1       Running   0          6m        10.240.0.22   k8s-agentpool-34076307-0   <none>
deployment-azuredisk3-68959c48c4-kr6ps   1/1       Running   0          6m        10.240.0.31   k8s-agentpool-34076307-0   <none>
deployment-azuredisk4-76d57d9f99-5l4xr   1/1       Running   0          6m        10.240.0.24   k8s-agentpool-34076307-0   <none>
deployment-azuredisk5-99b94f68-zqwjm     1/1       Running   0          6m        10.240.0.9    k8s-agentpool-34076307-0   <none>
deployment-azuredisk6-6db6b647d9-n8j7c   1/1       Running   0          6m        10.240.0.12   k8s-agentpool-34076307-0   <none>
deployment-azuredisk7-79cc8668fd-ltpnr   1/1       Running   0          6m        10.240.0.5    k8s-agentpool-34076307-0   <none>
deployment-azuredisk8-7fd8df68b7-rjfks   1/1       Running   0          6m        10.240.0.21   k8s-agentpool-34076307-0   <none>

Events:
  Type     Reason                  Age              From                               Message
  ----     ------                  ----             ----                               -------
  Normal   Scheduled               6m               default-scheduler                  Successfully assigned default/deployment-azuredisk5-99b94f68-zqwjm to k8s-agentpool-34076307-0
  Warning  FailedAttachVolume      6m               attachdetach-controller            Multi-Attach error for volume "pvc-9f0abf3a-b7f3-11e8-a9e9-000d3a107fa7" Volume is already used by pod(s) deployment-azuredisk5-99b94f68-6r5zr
  Warning  FailedMount             2m (x2 over 4m)  kubelet, k8s-agentpool-34076307-0  Unable to mount volumes for pod "deployment-azuredisk5-99b94f68-zqwjm_default(cee2c648-b7f4-11e8-a9e9-000d3a107fa7)": timeout expired waiting for volumes to attach or mount for pod "default"/"deployment-azuredisk5-99b94f68-zqwjm". list of unmounted volumes=[azuredisk]. list of unattached volumes=[azuredisk default-token-hdhnv]
  Normal   SuccessfulAttachVolume  1m               attachdetach-controller            AttachVolume.Attach succeeded for volume "pvc-9f0abf3a-b7f3-11e8-a9e9-000d3a107fa7"
  Normal   Pulling                 15s              kubelet, k8s-agentpool-34076307-0  pulling image "nginx"
  Normal   Pulled                  14s              kubelet, k8s-agentpool-34076307-0  Successfully pulled image "nginx"
  Normal   Created                 14s              kubelet, k8s-agentpool-34076307-0  Created container
  Normal   Started                 14s              kubelet, k8s-agentpool-34076307-0  Started container
```

#### clean up
```
kubectl delete deployment deployment-azuredisk1
kubectl delete deployment deployment-azuredisk2
kubectl delete deployment deployment-azuredisk3
kubectl delete deployment deployment-azuredisk4
kubectl delete deployment deployment-azuredisk5
kubectl delete deployment deployment-azuredisk6
kubectl delete deployment deployment-azuredisk7
kubectl delete deployment deployment-azuredisk8

kubectl delete pvc pvc-azuredisk1
kubectl delete pvc pvc-azuredisk2
kubectl delete pvc pvc-azuredisk3
kubectl delete pvc pvc-azuredisk4
kubectl delete pvc pvc-azuredisk5
kubectl delete pvc pvc-azuredisk6
kubectl delete pvc pvc-azuredisk7
kubectl delete pvc pvc-azuredisk8
```

#### expected behavior on agent node
```
azureuser@aks-nodepool1-26705064-2:~$ sudo tree /dev/disk/azure
...
â””â”€â”€ scsi1
    â”œâ”€â”€ lun0 -> ../../../sdc
    â”œâ”€â”€ lun1 -> ../../../sdd
    â”œâ”€â”€ lun2 -> ../../../sde
    â”œâ”€â”€ lun3 -> ../../../sdf
    â”œâ”€â”€ lun4 -> ../../../sdg
    â”œâ”€â”€ lun5 -> ../../../sdh
    â”œâ”€â”€ lun6 -> ../../../sdi
    â””â”€â”€ lun7 -> ../../../sdj
    
azureuser@aks-nodepool1-26705064-2:~$ sudo df -aTH | grep dev
udev           devtmpfs      17G     0   17G   0% /dev
devpts         devpts          0     0     0    - /dev/pts
/dev/sda1      ext4          32G  4.3G   27G  14% /
tmpfs          tmpfs         17G     0   17G   0% /dev/shm
cgroup         cgroup          0     0     0    - /sys/fs/cgroup/devices
mqueue         mqueue          0     0     0    - /dev/mqueue
hugetlbfs      hugetlbfs       0     0     0    - /dev/hugepages
/dev/sdb1      ext4          68G   55M   64G   1% /mnt
/dev/sda1      ext4          32G  4.3G   27G  14% /var/lib/docker/overlay2
/dev/sda1      ext4          32G  4.3G   27G  14% /var/lib/kubelet
/dev/sdc       ext4         3.2G  4.8M  3.0G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3982675170
/dev/sdc       ext4         3.2G  4.8M  3.0G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3982675170
/dev/sdc       ext4         3.2G  4.8M  3.0G   1% /var/lib/kubelet/pods/52f5e57f-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b82694c3-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdc       ext4         3.2G  4.8M  3.0G   1% /var/lib/kubelet/pods/52f5e57f-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b82694c3-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdd       ext4         4.1G  8.5M  3.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m2789537411
/dev/sdd       ext4         4.1G  8.5M  3.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m2789537411
/dev/sdd       ext4         4.1G  8.5M  3.9G   1% /var/lib/kubelet/pods/52f4982c-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b892b81f-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdd       ext4         4.1G  8.5M  3.9G   1% /var/lib/kubelet/pods/52f4982c-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b892b81f-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sde       ext4         5.2G   11M  4.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3994774048
/dev/sde       ext4         5.2G   11M  4.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3994774048
/dev/sde       ext4         5.2G   11M  4.9G   1% /var/lib/kubelet/pods/52f9e5b0-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b8f85397-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sde       ext4         5.2G   11M  4.9G   1% /var/lib/kubelet/pods/52f9e5b0-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b8f85397-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdg       ext4         7.3G   17M  6.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m2478919455
/dev/sdg       ext4         7.3G   17M  6.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m2478919455
/dev/sdg       ext4         7.3G   17M  6.9G   1% /var/lib/kubelet/pods/52fa00ea-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b9c9eb48-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdg       ext4         7.3G   17M  6.9G   1% /var/lib/kubelet/pods/52fa00ea-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b9c9eb48-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdf       ext4         6.3G   13M  5.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3724353225
/dev/sdf       ext4         6.3G   13M  5.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3724353225
/dev/sdf       ext4         6.3G   13M  5.9G   1% /var/lib/kubelet/pods/52f9c39a-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b964e843-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdf       ext4         6.3G   13M  5.9G   1% /var/lib/kubelet/pods/52f9c39a-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b964e843-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdi       ext4         1.1G  1.4M  952M   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1717135653
/dev/sdi       ext4         1.1G  1.4M  952M   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1717135653
/dev/sdi       ext4         1.1G  1.4M  952M   1% /var/lib/kubelet/pods/52f5eab7-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b753a817-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdi       ext4         1.1G  1.4M  952M   1% /var/lib/kubelet/pods/52f5eab7-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b753a817-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdj       ext4         2.1G  3.2M  2.0G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3566200714
/dev/sdj       ext4         2.1G  3.2M  2.0G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3566200714
/dev/sdj       ext4         2.1G  3.2M  2.0G   1% /var/lib/kubelet/pods/52f4c20b-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b7c18e46-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdj       ext4         2.1G  3.2M  2.0G   1% /var/lib/kubelet/pods/52f4c20b-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-b7c18e46-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdh       ext4         8.4G   19M  7.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3714547076
/dev/sdh       ext4         8.4G   19M  7.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3714547076
/dev/sdh       ext4         8.4G   19M  7.9G   1% /var/lib/kubelet/pods/52fa8b6c-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-bc4c7433-6a2a-11e8-ad70-0a58ac1f0c4a
/dev/sdh       ext4         8.4G   19M  7.9G   1% /var/lib/kubelet/pods/52fa8b6c-6a2c-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-bc4c7433-6a2a-11e8-ad70-0a58ac1f0c4a
```

### Tips
#### 1. Get disk attach/detach API call time cost
```
# curl http://localhost:10252/metrics | grep cloudprovider_azure_api_request | grep -e sum -e count | grep disk

cloudprovider_azure_api_request_duration_seconds_sum{request="vmssvm_create_or_update",resource_group="andy-vmss1141",source="attach_disk",subscription_id="b9d2281e-dcd5-4dfd-9a97-xxx"} 40.985180089
cloudprovider_azure_api_request_duration_seconds_count{request="vmssvm_create_or_update",resource_group="andy-vmss1141",source="attach_disk",subscription_id="b9d2281e-dcd5-4dfd-9a97-xxx"} 2
cloudprovider_azure_api_request_duration_seconds_sum{request="vmssvm_create_or_update",resource_group="andy-vmss1141",source="detach_disk",subscription_id="b9d2281e-dcd5-4dfd-9a97-xxx"} 40.933383735
cloudprovider_azure_api_request_duration_seconds_count{request="vmssvm_create_or_update",resource_group="andy-vmss1141",source="detach_disk",subscription_id="b9d2281e-dcd5-4dfd-9a97-xxx"} 2
```
In above example, two disk attach API calls cost 40.98s, and 2 disk detach API calls cost 40.9s
