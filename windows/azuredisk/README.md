## Dynamic Provisioning for Azure disk mount on Windows
 - Supported Windows Version: Windows Server version 1709 or above
 - Supported kubernetes version: [Azure/kubernetes v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1), upstream v1.9.0
 
#### Note:
 - Windows agent node set up by acs-engine uses https://github.com/Azure/kubernetes, which contains more features than [upstream](https://github.com/kubernetes/kubernetes), e.g. azure disk & file on Windows features are available from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1), while these two features are avaiable from v1.9.0 in [upstream](https://github.com/kubernetes/kubernetes)

 - Azure disk mount feature on Windows is avalable from version >= [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1), with the exception for **v1.8.0, v1.8.1, v1.8.2**. And this feature is only supported on `Windows Server version 1709` (`"agentWindowsSku": "Datacenter-Core-1709-with-Containers-smalldisk"`), please note that there is a **breaking change** for Windows container running on 1709, only container tag with `1709` keyword could run on 1709, e.g. 
```
microsoft/aspnet:4.7.1-windowsservercore-1709
microsoft/windowsservercore:1709
microsoft/iis:windowsservercore-1709
```

## 1. create an azure disk storage class if `hdd` does not exist
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

## 2. create an azure disk pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azuredisk.yaml```

#### make sure pvc is created successfully
```watch kubectl describe pvc pvc-azuredisk```

## 3. create a pod with azure disk pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/azuredisk/aspnet-pod-azuredisk.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po aspnet-azuredisk```

## 4. enter the pod container to do validation
```kubectl exec -it aspnet-azuredisk -- cmd```

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

