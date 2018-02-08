# Dynamic Provisioning for azure file on Windows Server version 1709 (support from v1.7.2)
#### Note:
1. Windows agent node set up by acs-engine uses https://github.com/Azure/kubernetes, which contains more features than [upstream](https://github.com/kubernetes/kubernetes), e.g. azure disk & file on Windows features are available from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1), while these two features are avaiable from v1.9.0 in [upstream](https://github.com/kubernetes/kubernetes)

2. Azure file mount feature on Windows is avalable from version >= [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1). And this feature is only supported on `Windows Server version 1709` (`"agentWindowsSku": "Datacenter-Core-1709-with-Containers-smalldisk"`), please note that there is a **breaking change** for Windows container running on 1709, only container tag with `1709` keyword could run on 1709, e.g. 
```
microsoft/aspnet:4.7.1-windowsservercore-1709
microsoft/windowsservercore:1709
microsoft/iis:windowsservercore-1709
```

## 1. create an azure file storage class
There are two options for creating azure file storage class
#### Option#1: find a suitable storage account that matches ```skuName``` in same resource group when provisioning azure file
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile.yaml
```

#### Option#2: use existing storage account when provisioning azure file
download `storageclass-azurefile-account.yaml` file and modify `storageAccount` values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile-account.yaml
vi storageclass-azurefile-account.yaml
kubectl create -f storageclass-azurefile-account.yaml
```

## 2. create a pvc for azure file first
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azurefile.yaml```

#### make sure pvc is created successfully
```watch kubectl describe pvc pvc-azurefile```

## 3. create a pod with azure file pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/azurefile/aspnet-pod-azurefile.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po aspnet-azurefile```

## 4. enter the pod container to do validation
```kubectl exec -it aspnet-azurefile -- cmd```

```
C:\>cd mnt\azure
C:\mnt\azure>dir
 Volume in drive C has no label.
 Volume Serial Number is F878-8D74

 Directory of C:\mnt\azure

11/08/2017  06:03 AM    <DIR>          .
11/08/2017  06:03 AM    <DIR>          ..
               0 File(s)              0 bytes
               2 Dir(s)   5,368,709,120 bytes free
```
### Known issues of azure file dynamic provision
1. There is a [bug](https://github.com/kubernetes/kubernetes/pull/48326) of azure file dynamic provision in [v1.7.0, v1.7.10] (fixed in v1.7.11 or above, v1.8.0): cluster name length must be less than 16 characters, otherwise following error will be received when creating dynamic privisioning azure file pvc:
```
persistentvolume-controller    Warning    ProvisioningFailed Failed to provision volume with StorageClass "azurefile": failed to find a matching storage account
```

2. To specify a storage account in azure file dynamic provision, you should make sure the specified storage account is in the same resource group as your k8s cluster, if you are using AKS, the specified storage account should be in `shadow resource group`(naming as `MC_+{RESOUCE-GROUP-NAME}+{CLUSTER-NAME}+{REGION}`) which contains all resources of your aks cluster. 

# Static Provisioning for azure file on Windows Server version 1709(support from v1.7.x)
## 1. create a secret for azure file
1) create an azure file share in Azure storage account in the same resource group with k8s cluster, get connection info of that azure file
2) create a `azure-secrect.yaml` file that contains base64 encoded Azure Storage account name and key.

download `azure-secrect.yaml` file and modify `azurestorageaccountname`, `azurestorageaccountkey` values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/azure-secrect.yaml
vi azure-secrect.yaml
```

In the secret file, base64-encode azurestorageaccountname and azurestorageaccountkey. 
For the base64-encode, you could leverage this site: https://www.base64encode.net/
3. create the secret for azure file
```
kubectl create -f azure-secrect.yaml
```

## 2. create a pod with azure file
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/azurefile/aspnet-azurefile-static.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po aspnet-azurefile```

## 3. enter the pod container to do validation
```kubectl exec -it aspnet-azurefile -- cmd```

```
C:\>cd mnt\azure
C:\mnt\azure>dir
 Volume in drive C has no label.
 Volume Serial Number is F878-8D74

 Directory of C:\mnt\azure

11/08/2017  06:03 AM    <DIR>          .
11/08/2017  06:03 AM    <DIR>          ..
               0 File(s)              0 bytes
               2 Dir(s)   5,368,709,120 bytes free
```

### known issues of Azure file on Windows feature
1. [Allow windows mount path on windows](https://github.com/kubernetes/kubernetes/pull/51240) is available from v1.7.x, v1.8.3 or above, as a workaround, you could use linux style `mountPath`, e.g. `/mnt/`, this path will be converted into `c:/mnt/`

#### Links
[Azure File Storage Class](https://kubernetes.io/docs/concepts/storage/storage-classes/#azure-file)

[Azure file introduction](https://docs.microsoft.com/en-us/azure/storage/files/storage-files-introduction)

[Azure Files scale targets](https://docs.microsoft.com/en-us/azure/storage/common/storage-scalability-targets#azure-files-scale-targets)

[Windows Server version 1709](https://docs.microsoft.com/en-us/windows-server/get-started/whats-new-in-windows-server-1709)
