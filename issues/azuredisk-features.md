# Azure disk new features and restrictions
## Azure disk new features
#### 1. disk volume size grow

available from `v1.11.0`, details: [Add azuredisk PV size grow feature](https://github.com/kubernetes/kubernetes/pull/64386)

example: 
 - [azuredisk storage class with size grow configuration](https://github.com/andyzhangx/demo/blob/master/pv/storageclass-azuredisk-sizegrow.yaml)
 - [How to use azure disk size grow feature](https://github.com/andyzhangx/demo/blob/master/linux/azuredisk/azuredisk-sizegrow.md)

related issues: [Resizing the persistent volume in Azure AKS doesn't reflect the change at pod level.](https://github.com/kubernetes/kubernetes/issues/68427)

Tips: [Expand virtual hard disks on a Linux VM with the Azure CLI](https://docs.microsoft.com/en-us/azure/virtual-machines/linux/expand-disks)

#### 2. raw block device support

available from `v1.11.0`

details: [Add raw block device support for azure disk](https://github.com/kubernetes/kubernetes/pull/63841)

#### 3. Enable dynamic azure disk volume limits

available from `v1.12.0`, details: [Enable dynamic azure disk volume limits](https://github.com/kubernetes/kubernetes/pull/67772)

Before v1.12.0, the maximum disk number of node is always set as 16 by default, so if it’s a little VM size that only supports 8 disk attachment, there would be error after attaching the 9th disk, while from v1.12.0, the 9th disk would not be scheduled to that node if it only accepts attaching 8 disks totally.

details: [Node-specific Volume Limits](https://kubernetes.io/docs/concepts/storage/storage-limits/)
> To workaround this in k8s v1.11, try setting [KUBE_MAX_PD_VOLS](https://github.com/kubernetes/kubernetes/blob/591ef236e04a515f1b582cb8d8a4ea29aaee98a3/pkg/scheduler/algorithm/predicates/predicates.go#L106)(default for azure disk is 16) env variable and restart k8s scheduler.

 - Check maximum disk number of node
```
kubectl describe no | grep attachable-volumes-azure-disk
```

 - related issues
   - [AKS can assign pods to nodes with insufficient disks to attach](https://github.com/kubernetes/kubernetes/issues/77225#issuecomment-582783869)

#### 4. More disk type support

new managed disk types [`StandardSSD_LRS`](https://aka.ms/StandardSSDBlog), `UltraSSD_LRS` are available from `v1.13.0`

all possible `skuname` values are `Standard_LRS`, `StandardSSD_LRS`, `Premium_LRS`, `UltraSSD_LRS`
> Note: `UltraSSD_LRS` is still in Preview, it's only avaiable in certain region and supports Availablity Zone only, while AKS does not support Availablity Zone yet, details about UltraSSD_LRS: [Ultra SSD (preview) Managed Disks for Azure Virtual Machine workloads](https://docs.microsoft.com/en-us/azure/virtual-machines/linux/disks-ultra-ssd)

details: [add azure UltraSSD, StandardSSD disk type support](https://github.com/kubernetes/kubernetes/pull/70477)
 > check most updated azure disk type from [azure-sdk-for-go](https://github.com/Azure/azure-sdk-for-go/blob/master/services/compute/mgmt/2019-03-01/compute/models.go#L322-L328)

#### 5. External resource group support for azure disk PV dynamic provisioning
> all resource groups should be in same subscription, we don’t support cross-subscription scenario

example: https://github.com/andyzhangx/demo/blob/master/pv/storageclass-azuredisk-external-rg.yaml

details: [fix azure disk creation issue when specifying external resource group](https://github.com/kubernetes/kubernetes/pull/65516)

| k8s version | fixed version |
| ---- | ---- |
| v1.7 | not supported |
| v1.8 | 1.8.15 |
| v1.9 | 1.9.11 |
| v1.10 | 1.10.6 |
| v1.11 | 1.11.0 |

#### 6. disk attach/detach self-healing

**Issue details**:
There could be disk detach failure due to many reasons(e.g. disk RP busy, controller manager crash, etc.), and it would fail when attach one disk to other node if that disk is still attached to the old node, user needs to manually detach disk in problem in the before, with this fix, azure cloud provider would check and detach this disk if it's already attached to the other node, that's like self-healing. This PR could fix lots of such disk attachment issue.

**Fix**

Following PR would first check whether current disk is already attached to other node, if so, it would trigger a dangling error and k8s controller would detach disk first, and then do the attach volume operation.

This PR would also fix a "disk not found" issue when detach azure disk due to disk URI case sensitive case, error logs are like following(without this PR):
```
azure_controller_standard.go:134] detach azure disk: disk  not found, diskURI: /subscriptions/xxx/resourceGroups/andy-mg1160alpha3/providers/Microsoft.Compute/disks/xxx-dynamic-pvc-41a31580-f5b9-4f08-b0ea-0adcba15b6db
```

 - Fix on VMAS
   - [fix: detach azure disk issue using dangling error](https://github.com/kubernetes/kubernetes/pull/81266)
   - [fix: azure disk name matching issue](https://github.com/kubernetes/kubernetes/pull/81720)

| k8s version | fixed version |
| ---- | ---- |
| v1.12 | no fix |
| v1.13 | 1.13.11 |
| v1.14 | 1.14.7 |
| v1.15 | 1.15.4 |
| v1.15 | 1.16.0 |

 - Fix on VMSS
   - [fix: azure disk dangling attach issue on VMSS which would cause API throttling](https://github.com/kubernetes/kubernetes/pull/90749)

| k8s version | fixed version |
| ---- | ---- |
| v1.14 | only hotfixed with image `mcr.microsoft.com/oss/kubernetes/hyperkube:v1.14.8-hotfix.20200529.1` |
| v1.15 | only hotfixed with image `mcr.microsoft.com/oss/kubernetes/hyperkube:v1.15.11-hotfix.20200529.1`, `mcr.microsoft.com/oss/kubernetes/hyperkube:v1.15.12-hotfix.20200603` |
| v1.16 | 1.16.10 (also hotfixed with image `mcr.microsoft.com/oss/kubernetes/hyperkube:v1.16.9-hotfix.20200529.1`) |
| v1.17 | 1.17.6 |
| v1.18 | 1.18.3 |
| v1.19 | 1.19.0 |

**Work around**:

manually detach disk in problem

#### 7. Write accelerator

- available from `v1.18.0`
- create a disk with [Write Accelerator Enabled](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/how-to-enable-write-accelerator):
```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: ssd
provisioner: kubernetes.io/azure-disk
parameters:
  skuname: Premium_LRS
  writeAcceleratorEnabled: "true"
```
 - details: [add azure disk WriteAccelerator support](https://github.com/kubernetes/kubernetes/pull/87945)

#### 8. Shared disk
- available from `v1.19.0`
- added a new field(`maxShares`) in azure disk storage class to support [Azure shared disk](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/disks-shared-enable):
```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: shared-disk
provisioner: kubernetes.io/azure-disk
parameters:
  skuname: Premium_LRS  # Currently only available with premium SSDs.
  cachingMode: None  # ReadOnly host caching is not available for premium SSDs with maxShares>1
  maxShares: "2"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-azuredisk
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: shared-disk
```
 - details: [feat: support Azure shared disk](https://github.com/kubernetes/kubernetes/pull/89328)

#### 9. tags support
- available from `v1.19.0`
- added a new field(`tags`) in azure disk storage class to support:
```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: ssd
provisioner: kubernetes.io/azure-disk
parameters:
  skuname: StandardSSD_LRS
  tags: "key1=val1,key2=val2"
```
- details: [add tags support for azure disk driver](https://github.com/kubernetes/kubernetes/pull/92356)

#### 10. force detach
- available from `v1.19.0`

use `toBeDetached=true` to detach a disk, we could permanently fix [VMSS detach disk issue](https://docs.microsoft.com/en-us/azure/virtual-machines/troubleshooting/troubleshoot-vm-deployment-detached)

   - [fix: use force detach for azure disk](https://github.com/kubernetes/kubernetes/pull/91948)

| k8s version | fixed version |
| ---- | ---- |
| v1.16 | 1.16.13 |
| v1.17 | 1.17.9 |
| v1.18 | 1.18.6 |
| v1.19 | 1.19.0 |

## Azure disk restrictions
### 1. cannot attach an azure disk from another subscription
Error would be like following:
```
Events:
  Type     Reason              Age                  From                               Message
  ----     ------              ----                 ----                               -------
  Warning  FailedMount         3m (x1912 over 3d)   kubelet, aks-nodepool1-20449952-1  Unable to mount volumes for pod "nginx-azuredisk3_default(116d527e-c84c-11e8-af0a-d2df8f315e11)": timeout expired waiting for volumes to attach or mount for pod "default"/"nginx-azuredisk3". list of unmounted volumes=[azure]. list of unattached volumes=[azure default-token-dw48n]
  Warning  FailedAttachVolume  28s (x2129 over 3d)  attachdetach-controller            AttachVolume.Attach failed for volume "azure" : Attach volume "andytest" to instance "/subscriptions/b9d2281e-dcd5-4dfd-9a97-xxx/resourceGroups/MC_andy-aks1112_andy-aks1112_westus2/providers/Microsoft.Compute/virtualMachines/aks-nodepool1-20449952-1" failed with compute.VirtualMachinesClient#CreateOrUpdate: Failure sending request: StatusCode=400 -- Original Error: Code="InvalidParameter" Message="Subscription b9d2281e-dcd5-4dfd-9a97-xxx of the request must match the subscription 4be8920b-2978-43d7-ab14-xxx contained in the managed disk id." Target="dataDisk.managedDisk.id"
```
