# Azure file Dynamic Provisioning in Linux 
> available from v1.7.0
## 1. create a storage class for azure file
#### Option#1: find a suitable storage account that matches ```skuName``` in same resource group when provisioning azure file
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile.yaml
```

#### Option#2: use existing storage account when provisioning azure file
 - download `storageclass-azurefile-account.yaml` file and modify `storageAccount` values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile-account.yaml
vi storageclass-azurefile-account.yaml
kubectl create -f storageclass-azurefile-account.yaml
```
 > Note: make sure the specified storage account is in the same resource group as your k8s cluster

## 2. create a pvc for azure file first
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azurefile.yaml```

#### make sure pvc is created successfully
```watch kubectl describe pvc pvc-azurefile```

## 3. create a pod with azure file pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azurefile/nginx-pod-azurefile.yaml```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-azurefile```

## 4. enter the pod container to do validation
```kubectl exec -it nginx-azurefile -- bash```

```
root@nginx-azurefile:/# df -h
Filesystem      Size  Used Avail Use% Mounted on
overlay          30G  3.6G   26G  13% /
tmpfs           6.9G     0  6.9G   0% /dev
tmpfs           6.9G     0  6.9G   0% /sys/fs/cgroup
/dev/sda1        30G  3.6G   26G  13% /etc/hosts
/dev/sdc        4.8G   12M  4.6G   1% /mnt/azurefile
shm              64M     0   64M   0% /dev/shm
tmpfs           6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount
```
### Known issues of azure file dynamic provision
 - To specify a storage account in azure file dynamic provision, you should make sure the specified storage account is in the same resource group as your k8s cluster. In AKS, the specified storage account should be in `shadow resource group`(naming as `MC_+{RESOUCE-GROUP-NAME}+{CLUSTER-NAME}+{REGION}`) which contains all resources of your aks cluster. 

# Azure file Static Provisioning in Linux 
>  - available from v1.5.0
>  - static provisioning: user must create an azure file before using azure file mount feature.
>  - kubernetes v1.5, v1.6 does not support azure file dynamic provisioning, only static provisioning is available 

## Prerequisite
 - create an azure file share in Azure storage account in the same resource group with k8s cluster
 - get `azurestorageaccountname`, `azurestorageaccountkey` and `shareName` of that azure file
 
## 1. create a secret for azure file
#### Option#1: Use `kubectl create secret` to create `azure-secret`
```
kubectl create secret generic azure-secret --from-literal azurestorageaccountname=NAME --from-literal azurestorageaccountkey="KEY" --type=Opaque
```
 
#### Option#2: create a `azure-secrect.yaml` file that contains base64 encoded Azure Storage account name and key
 - base64-encode azurestorageaccountname and azurestorageaccountkey. You could leverage this [site](https://www.base64encode.net/)

 - download `azure-secrect.yaml` file and modify `azurestorageaccountname`, `azurestorageaccountkey` base64-encoded values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/azure-secrect.yaml
vi azure-secrect.yaml
```

 - create `azure-secrect` for azure file
```
kubectl create -f azure-secrect.yaml
```

## 2. create a pod with azure file
download `nginx-pod-azurefile-static.yaml` file and modify `shareName` value
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azurefile/nginx-pod-azurefile-static.yaml
vi nginx-pod-azurefile-static.yaml
kubectl create -f nginx-pod-azurefile-static.yaml
```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po nginx-azurefile```

## 3. enter the pod container to do validation
```kubectl exec -it nginx-azurefile -- bash```

```
root@nginx-azurefile:/# df -h
Filesystem      Size  Used Avail Use% Mounted on
overlay          30G  3.6G   26G  13% /
tmpfs           6.9G     0  6.9G   0% /dev
tmpfs           6.9G     0  6.9G   0% /sys/fs/cgroup
/dev/sda1        30G  3.6G   26G  13% /etc/hosts
/dev/sdc        4.8G   12M  4.6G   1% /mnt/azurefile
shm              64M     0   64M   0% /dev/shm
tmpfs           6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount
root@nginx-azurefile:/# mount | grep cifs
//pvc3329812692002.file.core.windows.net/andy-mgwin1710-dynamic-pvc-7b5346be-d577-11e7-bc95-000d3a041274 on /mnt/azurefile type cifs (rw,relatime,vers=3.0,cache=strict,username=pvc3329812692002,domain=,uid=0,noforceuid,gid=0,noforcegid,addr=52.239.184.8,file_mode=0777,dir_mode=0777,persistenthandles,nounix,serverino,mapposix,rsize=1048576,wsize=1048576,echo_interval=60,actimeo=1)
```

### Other known issues of Azure file feature
 - `Premium` storage type is not supported for azure file currently
 - `fileMode`, `dirMode` value would be different in different versions, in latest master branch, it's `0755` by default, to set a different value, follow this [mount options support of azure file](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/azurefile-mountoptions.md) (available from v1.8.5). 
   - For version v1.8.0-v1.8.4, since [mount options support of azure file](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/azurefile-mountoptions.md) is not available, as a workaround, [securityContext](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) could be specified for the pod, [detailed pod example](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/demo-azurefile-securitycontext.yaml)
```
  securityContext:
    runAsUser: XXX
    fsGroup: XXX
```

| version | `fileMode`, `dirMode` value |
| ---- | ---- |
| v1.6.x, v1.7.x | 0777 |
| v1.8.0-v1.8.5 | 0700 |
| v1.8.6 or above | 0755 |
| v1.9.0 | 0700 |
| v1.9.1 or above | 0755 |

 - [other azure file plugin known issues](https://github.com/andyzhangx/demo/blob/master/issues/azurefile-issues.md)
 
#### default mountOptions of azure file on Linux
```
//ACCOUNT-NAME.file.core.windows.net/sharename on /var/lib/kubelet/pods/dd141c4f-501c-11e8-8c6d-0a58ac1f078e/volumes/kubernetes.io~azure-file/azure type cifs (rw,relatime,vers=3.0,cache=strict,username=ACCOUNT-NAME,domain=,uid=0,noforceuid,gid=0,noforcegid,addr=52.239.152.8,file_mode=0755,dir_mode=0755,persistenthandles,nounix,serverino,mapposix,rsize=1048576,wsize=1048576,echo_interval=60,actimeo=1)
```

#### Troubleshooting azure file issues
 - [Toubleshoot CIFS share mount errors](https://superuser.com/questions/430163/cifs-share-mount-errors)
 - [Troubleshoot Azure Files problems in Linux](https://docs.microsoft.com/en-us/azure/storage/files/storage-troubleshoot-linux-file-connection-problems)
 - [Troubleshooting tool for Azure Files mounting errors on Linux](https://gallery.technet.microsoft.com/Troubleshooting-tool-for-02184089)

#### Links
 - [Azure File Storage Class](https://kubernetes.io/docs/concepts/storage/storage-classes/#azure-file)
 - [Azure file introduction](https://docs.microsoft.com/en-us/azure/storage/files/storage-files-introduction)
 - [Azure Files scale targets](https://docs.microsoft.com/en-us/azure/storage/common/storage-scalability-targets#azure-files-scale-targets)
 - [Persistent volumes with Azure files - dynamic provisioning](https://docs.microsoft.com/en-us/azure/aks/azure-files-dynamic-pv)
 - [Using Azure Files with Kubernetes](https://docs.microsoft.com/en-us/azure/aks/azure-files)

