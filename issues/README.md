# known k8s on azure issues and fixes

## azure disk plugin known issues
### 1. disk attach error
**Issue description**:

In some corner case, when scheduling a pod with azure disk mount from one node to another, there could be lots of disk attach error due to the disk not being released in time from the previous node. This issue is due to lack of lock before DetachDisk operation, actually there should be a central lock for both AttachDisk and DetachDisk opertions, only one AttachDisk or DetachDisk operation is allowed at one time.

The disk attach error could be like following:
```
Cannot attach data disk 'cdb-dynamic-pvc-92972088-11b9-11e8-888f-000d3a018174' to VM 'kn-edge-0' because the disk is currently being detached or the last detach operation failed. Please wait until the disk is completely detached and then try again or delete/detach the disk explicitly again.
```


| Related issue list |
| ---- |
| [Azure Disk Detach are not working with multiple disk detach on the same Node](https://github.com/kubernetes/kubernetes/issues/60101) |
| [Since Intel CPU Azure update, new Azure Disks are not mounting, very critical... ](https://github.com/Azure/acs-engine/issues/2002) |
| [Busy azure-disk regularly fail to mount causing K8S Pod deployments to halt](https://github.com/Azure/ACS/issues/12) |

**Fix or workaround**:
 - Following workarounds could mitigate this issue
 
option#1: Update every agent node has on Azure cloud shell:
 ```
$vm = Get-AzureRMVM -ResourceGroupName $rg -Name $vmname  
Update-AzureRmVM -ResourceGroupName $rg -VM $vm -verbose -debug
 ```
option#2: 
1) kubectl cordon node
2) delete any pods on node with stateful sets
3) kubectl drain node
4) restart the Azure VM for node via the API or portal, wait untli VM is "Running"
5) kubectl uncordon node
 
 - PR [fix race condition issue when detaching azure disk](https://github.com/kubernetes/kubernetes/pull/60183) has fixed this issue by add a lock before DetachDisk

 | k8s version | fixed version |
| ---- | ---- |
| v1.6 | could not fix since no cherry-pick is allowed for v1.6 |
| v1.8 | in cherry-pick |
| v1.8 | in cherry-pick |
| v1.9 | in cherry-pick |
| v1.10 | fixed in v1.10.0 |

## 2. disk unavailable after attach/detach a data disk on a node
**Issue description**:

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
 
| Related issue list |
| ---- |
| [device name change due to azure disk host cache setting](https://github.com/kubernetes/kubernetes/issues/60344) | 
| [unable to use azure disk in StatefulSet since /dev/sd* changed after detach/attach disk](https://github.com/kubernetes/kubernetes/issues/57444) |
| [Disk error when pods are mounting a certain amount of volumes on a node](https://github.com/Azure/AKS/issues/201) |
| [unable to use azure disk in StatefulSet since /dev/sd* changed after detach/attach disk](https://github.com/Azure/acs-engine/issues/1918) |

**Fix or workaround**:

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

 - PR [fix device name change issue for azure disk](https://github.com/kubernetes/kubernetes/pull/60346) could fix this issue too, it will change default `cachingmode` value from `ReadWrite` to `None`.
 
 | k8s version | fixed version |
| ---- | ---- |
| v1.6 | no such issue as default `cachingmode` is `None` |
| v1.8 | in cherry-pick |
| v1.8 | in cherry-pick |
| v1.9 | in cherry-pick |
| v1.10 | fixed in v1.10.0 |

## azure file plugin known issues


## azure network known issues
