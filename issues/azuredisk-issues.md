# azure disk plugin known issues
### 1. disk attach error
**Issue details**:

In some corner case(detaching multiple disks on a node simultaneously), when scheduling a pod with azure disk mount from one node to another, there could be lots of disk attach error(no recovery) due to the disk not being released in time from the previous node. This issue is due to lack of lock before DetachDisk operation, actually there should be a central lock for both AttachDisk and DetachDisk opertions, only one AttachDisk or DetachDisk operation is allowed at one time.

The disk attach error could be like following:
```
Cannot attach data disk 'cdb-dynamic-pvc-92972088-11b9-11e8-888f-000d3a018174' to VM 'kn-edge-0' because the disk is currently being detached or the last detach operation failed. Please wait until the disk is completely detached and then try again or delete/detach the disk explicitly again.
```

**Related issues**
 - [Azure Disk Detach are not working with multiple disk detach on the same Node](https://github.com/kubernetes/kubernetes/issues/60101)
 - [Since Intel CPU Azure update, new Azure Disks are not mounting, very critical... ](https://github.com/Azure/acs-engine/issues/2002)
 - [Busy azure-disk regularly fail to mount causing K8S Pod deployments to halt](https://github.com/Azure/ACS/issues/12)

**Mitigation**:
 - option#1: Update every agent node that has attached or detached the disk in problem
 
###### in Azure cloud shell, run
```
$vm = Get-AzureRMVM -ResourceGroupName $rg -Name $vmname  
Update-AzureRmVM -ResourceGroupName $rg -VM $vm -verbose -debug
```
###### in Azure cli, run
```
az vm update -g <group> -n <name>
```

 - option#2: 
1) ```kubectl cordon node``` #make sure no scheduling on this node
2) ```kubectl drain node```  #schedule pod in current node to other node
3) restart the Azure VM for node via the API or portal, wait untli VM is "Running"
4) ```kubectl uncordon node```
 
**Fix**
 - PR [fix race condition issue when detaching azure disk](https://github.com/kubernetes/kubernetes/pull/60183) has fixed this issue by add a lock before DetachDisk

| k8s version | fixed version |
| ---- | ---- |
| v1.6 | no fix since v1.6 does not accept any cherry-pick |
| v1.7 | 1.7.14 |
| v1.8 | 1.8.9 |
| v1.9 | 1.9.5 |
| v1.10 | 1.10.0 |

### 2. disk unavailable after attach/detach a data disk on a node
**Issue details**:

From k8s v1.7, default host cache setting changed from `None` to `ReadWrite`, this change would lead to device name change after attach multiple disks on a node, finally lead to disk unavailable from pod. When access data disk inside a pod, will get following error:
```
[root@admin-0 /]# ls /datadisk
ls: reading directory .: Input/output error
```

In my testing on Ubuntu 16.04 D2_V2 VM, when attaching the 6th data disk will cause device name change on agent node, e.g. following lun0 disk should be `sdc` other than `sdk`.
```
azureuser@k8s-agentpool2-40588258-0:~$ tree /dev/disk/azure
...
â””â”€â”€ scsi1
    â”œâ”€â”€ lun0 -> ../../../sdk
    â”œâ”€â”€ lun1 -> ../../../sdj
    â”œâ”€â”€ lun2 -> ../../../sde
    â”œâ”€â”€ lun3 -> ../../../sdf
    â”œâ”€â”€ lun4 -> ../../../sdg
    â”œâ”€â”€ lun5 -> ../../../sdh
    â””â”€â”€ lun6 -> ../../../sdi
```
 
**Related issues**
 - [device name change due to azure disk host cache setting](https://github.com/kubernetes/kubernetes/issues/60344)
 - [unable to use azure disk in StatefulSet since /dev/sd* changed after detach/attach disk](https://github.com/kubernetes/kubernetes/issues/57444)
 - [Disk error when pods are mounting a certain amount of volumes on a node](https://github.com/Azure/AKS/issues/201)
 - [unable to use azure disk in StatefulSet since /dev/sd* changed after detach/attach disk](https://github.com/Azure/acs-engine/issues/1918)
 - [Input/output error when accessing PV](https://github.com/Azure/AKS/issues/297)

**Workaround**:
 - add `cachingmode: None` in azure disk storage class(default is `ReadWrite`), e.g.
```
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: hdd
provisioner: kubernetes.io/azure-disk
parameters:
  skuname: Standard_LRS
  kind: Managed
  cachingmode: None
```

**Fix**
 - PR [fix device name change issue for azure disk](https://github.com/kubernetes/kubernetes/pull/60346) could fix this issue too, it will change default `cachingmode` value from `ReadWrite` to `None`.
 
| k8s version | fixed version |
| ---- | ---- |
| v1.6 | no such issue as `cachingmode` is already `None` by default |
| v1.7 | 1.7.14 |
| v1.8 | 1.8.11 |
| v1.9 | 1.9.4 |
| v1.10 | 1.10.0 |

### 3. Azure disk support on Sovereign Cloud
[Azure disk on Sovereign Cloud](https://github.com/kubernetes/kubernetes/pull/50673) is supported from v1.7.9, v1.8.3

### 4. Time cost for Azure Disk PVC mount
Time cost for Azure Disk PVC mount on a standard node size(e.g. Standard_D2_V2) is around 1 minute, and there is a PR [using cache fix](https://github.com/kubernetes/kubernetes/pull/57432) to fix this issue, which could reduce the mount time cost to around 30s.

| k8s version | fixed version |
| ---- | ---- |
| v1.8 | no fix |
| v1.9 | 1.9.2 |
| v1.10 | 1.10.0 |

 > Note: for some smaller VM size which has only 1 CPU core, time cost would be much bigger(e.g. > 10min) since container is hard to get CPU slot.
 
### 5. Azure disk PVC `Multi-Attach error`, makes disk mount very slow or mount failure forever
**Issue details**:
When schedule a pod with azure disk volume from one node to another, total time cost of detach & attach is around 1 min from v1.9.2, while in v1.9.x, there is an [UnmountDevice failure issue in containerized kubelet](https://github.com/kubernetes/kubernetes/issues/62282) which makes disk mount very slow or mount failure forever, this issue only exists in v1.9.x due to PR [Refactor nsenter](https://github.com/kubernetes/kubernetes/pull/51771), v1.10.0 won't have this issue since `devicePath` is updated in [v1.10 code](https://github.com/kubernetes/kubernetes/blob/release-1.10/pkg/volume/util/operationexecutor/operation_generator.go#L1130-L1131)

**error logs**:
 - `kubectl describe po POD-NAME`
```
Events:
  Type     Reason                 Age   From                               Message
  ----     ------                 ----  ----                               -------
  Normal   Scheduled              3m    default-scheduler                  Successfully assigned deployment-azuredisk1-6cd8bc7945-kbkvz to k8s-agentpool-88970029-0
  Warning  FailedAttachVolume     3m    attachdetach-controller            Multi-Attach error for volume "pvc-6f2d0788-3b0b-11e8-a378-000d3afe2762" Volume is already exclusively attached to one node and can't be attached to another
  Normal   SuccessfulMountVolume  3m    kubelet, k8s-agentpool-88970029-0  MountVolume.SetUp succeeded for volume "default-token-qt7h6"
  Warning  FailedMount            1m    kubelet, k8s-agentpool-88970029-0  Unable to mount volumes for pod "deployment-azuredisk1-6cd8bc7945-kbkvz_default(5346c040-3e4c-11e8-a378-000d3afe2762)": timeout expired waiting for volumes to attach/mount for pod "default"/"deployment-azuredisk1-6cd8bc7945-kbkvz". list of unattached/unmounted volumes=[azuredisk]
```
 - kubelet logs from the new node
```
E0412 20:08:10.920284    7602 nestedpendingoperations.go:263] Operation for "\"kubernetes.io/azure-disk//subscriptions/xxx/resourceGroups/MC_xxx_eastus/providers/Microsoft.Compute/disks/kubernetes-dynamic-pvc-11035a31-3e8d-11e8-82ec-0a58ac1f04cf\"" failed. No retries permitted until 2018-04-12 20:08:12.920234762 +0000 UTC m=+1467.278612421 (durationBeforeRetry 2s). Error: "Volume has not been added to the list of VolumesInUse in the node's volume status for volume \"pvc-11035a31-3e8d-11e8-82ec-0a58ac1f04cf\" (UniqueName: \"kubernetes.io/azure-disk//subscriptions/xxx/resourceGroups/MC_xxx_eastus/providers/Microsoft.Compute/disks/kubernetes-dynamic-pvc-11035a31-3e8d-11e8-82ec-0a58ac1f04cf\") pod \"symbiont-node-consul-0\" (UID: \"11043b12-3e8d-11e8-82ec-0a58ac1f04cf\") "
```

**Mitigation**:

If azure disk PVC mount successfully in the end, there is no action, while if it could not be mounted for more than 20min, following actions could be taken:
 - check whether `volumesInUse` list has unmounted azure disks, run:
```
kubectl get no NODE-NAME -o yaml > node.log
```
all volumes in `volumesInUse` should be also in `volumesAttached`, otherwise there would be issue
 - restart kubelet on the original node would solve this issue: `sudo kubectl kubelet restart` 

**Fix**
 - PR [fix nsenter GetFileType issue in containerized kubelet](https://github.com/kubernetes/kubernetes/pull/62467) would fix this issue
 
| k8s version | fixed version |
| ---- | ---- |
| v1.8 | no such issue |
| v1.9 | v1.9.7 |
| v1.10 | no such issue |
