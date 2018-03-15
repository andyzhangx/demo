# known k8s on azure issues and fixes

## azure disk plugin known issues
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

**Workaround**:
 - option#1: Update every agent node that has this issue on Azure cloud shell:
```
$vm = Get-AzureRMVM -ResourceGroupName $rg -Name $vmname  
Update-AzureRmVM -ResourceGroupName $rg -VM $vm -verbose -debug
```
 > Note: in Azure cli, run
```
az vm update -g <group> -n <name>
```

 - option#2: 
1) kubectl cordon node
2) delete any pods on node with stateful sets
3) kubectl drain node
4) restart the Azure VM for node via the API or portal, wait untli VM is "Running"
5) kubectl uncordon node
 
**Fix**
 - PR [fix race condition issue when detaching azure disk](https://github.com/kubernetes/kubernetes/pull/60183) has fixed this issue by add a lock before DetachDisk

| k8s version | fixed version |
| ---- | ---- |
| v1.6 | no fix since v1.6 does not accept any cherry-pick |
| v1.7 | 1.7.14 |
| v1.8 | 1.8.9 |
| v1.9 | in cherry-pick |
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
| v1.7 | in cherry-pick |
| v1.8 | in cherry-pick |
| v1.9 | in cherry-pick |
| v1.10 | fixed in v1.10.0 |

### 3. Azure disk support on Sovereign Cloud
[Azure disk on Sovereign Cloud](https://github.com/kubernetes/kubernetes/pull/50673) is supported from v1.7.9, v1.8.3

### 4. Time cost for Azure Disk PVC mount
Time cost for Azure Disk PVC mount on a pod is around 1 minute, and there is a [using cache fix](https://github.com/kubernetes/kubernetes/pull/57432) for this issue, which could reduce the mount time cost to around 30s.

## azure file plugin known issues
### 1. azure file file/dir mode setting issue
**Issue details**:

`fileMode`, `dirMode` value would be different in different versions, to set a different value, follow this [mount options support of azure file](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/azurefile-mountoptions.md) (available from v1.8.5). For version v1.8.0-v1.8.4, since [mount options support of azure file](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/azurefile-mountoptions.md) is not available, as a workaround, specify a [securityContext](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) for the container with: `runAsUser: 0`, here is an [example](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/demo-azurefile-securitycontext.yaml)

| version | `fileMode`, `dirMode` value |
| ---- | ---- |
| v1.6.x, v1.7.x | 0777 |
| v1.8.0-v1.8.5 | 0700 |
| v1.8.6 or above | 0755 |
| v1.9.0 | 0700 |
| v1.9.1 or above | 0755 |

### 2. permission issue of azure file dynamic provision in acs-engine
**Issue details**:

From acs-engine v0.12.0, RBAC is enabled, azure file dynamic provision does not work from this version

**error logs**:
```
Events:
  Type     Reason              Age   From                         Message
  ----     ------              ----  ----                         -------
  Warning  ProvisioningFailed  8s    persistentvolume-controller  Failed to provision volume with StorageClass "azurefile": Couldn't create secret secrets is forbidden: User "system:serviceaccount:kube-syste
m:persistent-volume-binder" cannot create secrets in the namespace "default"
  Warning  ProvisioningFailed  8s    persistentvolume-controller  Failed to provision volume with StorageClass "azurefile": failed to find a matching storage account
```

**Related issues**
 - [azure file PVC need secrets create permission for persistent-volume-binder](https://github.com/kubernetes/kubernetes/issues/59543)

**Workaround**:
 - Add a ClusterRole and ClusterRoleBinding for [azure file dynamic privision](https://github.com/andyzhangx/Demo/tree/master/linux/azurefile#dynamic-provisioning-for-azure-file-in-linux-support-from-v170)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/rbac/azure-cloud-provider-deployment.yaml
```

**Fix**
 - PR in acs-engine: [fix azure file dynamic provision permission issue](https://github.com/Azure/acs-engine/pull/2238)
 
### 3. Azure file support on Sovereign Cloud
[Azure file on Sovereign Cloud](https://github.com/kubernetes/kubernetes/pull/48460) is supported from v1.7.11, v1.8.0

### 4. azure file dynamic provision failed due to cluster name length issue
**Issue details**:

There is a [bug](https://github.com/kubernetes/kubernetes/pull/48326) of azure file dynamic provision in [v1.7.0, v1.7.10] (fixed in v1.7.11, v1.8.0): cluster name length must be less than 16 characters, otherwise following error will be received when creating dynamic privisioning azure file pvc:
```
persistentvolume-controller    Warning    ProvisioningFailed Failed to provision volume with StorageClass "azurefile": failed to find a matching storage account
```

### 5. azure file dynamic provision failed due to no storage account in current resource group
**Issue details**:

**Related issues**

**Workaround**:

**Fix**

### 6. azure file plugin on Windows does not work after node restart
**Issue details**:
azure file plugin on Windows does not work after node restart, this is due to `New-SmbGlobalMapping` cmdlet has lost account name/key after reboot

**Related issues**
 - [azure file plugin on Windows does not work after node restart](https://github.com/kubernetes/kubernetes/issues/60624)

**Workaround**:
 - delete the original pod with azure file mount
 - create the pod again

**Fix**
 - PR [fix azure file plugin failure issue on Windows after node restart](https://github.com/kubernetes/kubernetes/pull/60625)

| k8s version | fixed version |
| ---- | ---- |
| v1.7 |  |
| v1.8 |  |
| v1.9 |  |
| v1.10 | code review in v1.10.0 |

### 7. file permission could not be changed using azure file, e.g. postgresql
**error logs** when running postgresql on azure file plugin:
```
initdb: could not change permissions of directory "/var/lib/postgresql/data": Operation not permitted
fixing permissions on existing directory /var/lib/postgresql/data 
```

**Issue details**:
azure file plugin is using cifs/SMB protocol, file/dir permission could not be changed after mounting

**Workaround**:
Use subPath together with azure disk plugin

**Related issues**
[Persistent Volume Claim permissions](https://github.com/Azure/AKS/issues/225)

## azure network known issues
### 1. network interface failed
**Workaround**:
```
az network nic update -g RG-NAME -n NIC-NAME
```

## Other issues
### 1. `GET/VirtualMachine` has too many ARM api calls
**Issue details**:
There could be ARM api throttling due to too many ARM api calls in a time period.

**error logs**:
```
"OperationNotAllowed",\r\n    "message": "The server rejected the request because too many requests have been received for this subscription.
```

**Workaround**:
 - Make sure that instance metadata is used. (set true in azure.json) on all nodes (require restarting kubelet+ all master roles on masters and kubelet on nodes).
 - There is a large # of put against ROUTES, was that a multiple scale events, or multiple cluster creation? If that is not the case or they operate large # of clusters in the same subscription then increase "--route-reconciliation-period" on controller-manager (require restart of controller manager). 

**Fix**
 - we have used cache in GET/VirtualMachine in v1.9.2: [Add cache for VirtualMachinesClient.Get in azure cloud provider](https://github.com/kubernetes/kubernetes/pull/57432)

| k8s version | fixed version |
| ---- | ---- |
| v1.9 | fixed in v1.9.2 |
| v1.10 | fixed |
