# known k8s on azure issues and corresponding fix/workaround

## azure disk plugin known issues
### 1. Multi-Attach disk error
**Issue description**:

when scheduling a pod with azure disk mount from one node to another, there could be lots of `Multi-Attach` error. This issue is because there is lock before detaching azure disk, actually there should be a global lock for both AttachDisk and DetachDisk functions, that is there could only be one AttachDisk or DetachDisk at one time.

| Related issue list |
| ---- |
| [Azure Disk Detach are not working with multiple disk detach on the same Node](https://github.com/kubernetes/kubernetes/issues/60101) |


**Fix or workaround**:

[fix race condition issue when detaching azure disk](https://github.com/kubernetes/kubernetes/pull/60183)

### 2. disk unavailable after attach/detach a data disk on a node
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

## azure file plugin known issues


## azure network known issues
