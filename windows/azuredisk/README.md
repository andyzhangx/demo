## Dynamic Provisioning for Azure disk mount on Windows
### 1. create an azure disk storage class if `hdd` does not exist
 - k8s agent pool is based on managed disk VM
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azuredisk-managed.yaml
```

 - k8s agent pool is based on blob based(unmanaged) disk VM
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azuredisk.yaml
```

###### Note: 
 - managed disk mount feature is only supported from v1.7.2
 - AKS cluster use managed disk by default, there are already `managed-standard`, `managed-premium` built-in azure disk storage classes.

### 2. create an azure disk pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azuredisk.yaml```

#### make sure pvc is created successfully
```watch kubectl describe pvc pvc-azuredisk```

### 3. create a pod with azure disk pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/azuredisk/aspnet-pod-azuredisk.yaml```

## Static Provisioning for azure disk
### 1. create an azure disk manually in the same resource group and modify `aspnet-pod-azuredisk.yaml`
 - managed disk
```
wget -O aspnet-pod-azuredisk.yaml https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/azuredisk/aspnet-pod-azuredisk-static-blobdisk.yaml
vi aspnet-pod-azuredisk-static-blobdisk.yaml
```

 - blob based(unmanaged) disk 
```
wget -O aspnet-pod-azuredisk.yaml https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/azuredisk/aspnet-pod-azuredisk-static-mgrdisk.yaml
vi aspnet-pod-azuredisk-static-mgrdisk.yaml
```

### 2. create a pod with an azure disk mount
```kubectl create -f aspnet-pod-azuredisk.yaml```

## Check pod status
 - watch the status of pod until its `Status` changed from `Pending` to `Running`
```
watch kubectl describe po aspnet-azuredisk
```

 - enter the pod container to do validation
```
kubectl exec -it aspnet-azuredisk -- cmd
```

```
C:\>d:
D:\>mkdir test
D:\>cd test
D:\test>dir
 Volume in drive D has no label.
 Volume Serial Number is 50C1-AE52

 Directory of D:\test

09/20/2017  12:40 AM    <DIR>          .
09/20/2017  12:40 AM    <DIR>          ..
               0 File(s)              0 bytes
               2 Dir(s)   5,334,327,296 bytes free
```

### known issues of Azure disk on Windows feature
 - [Allow windows mount path on windows](https://github.com/kubernetes/kubernetes/pull/51240) is available from v1.7.x, v1.8.3 or above.

 - Only drive letter(e.g. `D:`) as `mountPath` works for azure disk on Windows feature due to [volume mapping would fail when hostPath is a symbolic link to a drive and containerPath is a dir path on Windows](https://github.com/moby/moby/issues/35436)
 
 - [other azure disk plugin known issues](https://github.com/andyzhangx/demo/blob/master/issues/azuredisk-issues.md)

#### Links
[Azure Disk Storage Class](https://kubernetes.io/docs/concepts/storage/storage-classes/#azure-disk)

[Azure Disk Scalability and Performance Targets](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/standard-storage?toc=%2Fazure%2Fstorage%2Fblobs%2Ftoc.json#scalability-and-performance-targets)

[Debug Azure disk attachment issue](https://github.com/andyzhangx/Demo/blob/master/windows/azuredisk/azuredisk-attachment-debugging.md)

