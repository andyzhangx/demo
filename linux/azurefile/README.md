# Dynamic Provisioning for azure file in Linux (support from v1.7.0)
## 1. create a storage class for azure file
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
/dev/sdc        4.8G   12M  4.6G   1% /mnt/blobfile
shm              64M     0   64M   0% /dev/shm
tmpfs           6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount
```
### Note
There is a bug of azure file mount feature in v1.7.x (fixed in v1.8.0), cluster name length must be less than 16 characters, otherwise following error will be received when creating dynamic privisioning azure file pvc:
```
persistentvolume-controller    Warning    ProvisioningFailed Failed to provision volume with StorageClass "azurefile": failed to find a matching storage account
```
A fix for this is in progress: https://github.com/kubernetes/kubernetes/pull/53172


# Static Provisioning for azure file in Linux (support from v1.5.0)
kubernetes v1.5, v1.6 does not support dynamic provisioning for azure file, only static provisioning is supported for azure file which means a storage account should be created before using azure file mount feature.

## 1. create a secret for azure file
Create an azure file share in the Azure storage account, get the connection info of that azure file and then create a k8s secret that contains base64 encoded Azure Storage account name and key. 
In the secret file, base64-encode Azure Storage account name and pair it with name azurestorageaccountname, and base64-encode Azure Storage access key and pair it with name azurestorageaccountkey. 
For how to base64-encode, you could leverage this site: https://www.base64encode.net/

#### 2. download `azure-secrect.yaml` file and modify `azurestorageaccountname`, `azurestorageaccountkey` values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/azure-secrect.yaml
vi azure-secrect.yaml
kubectl create -f azure-secrect.yaml
```

## 3. create a pod with azure file
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azurefile/nginx-pod-azurefile-static.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
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
/dev/sdc        4.8G   12M  4.6G   1% /mnt/blobfile
shm              64M     0   64M   0% /dev/shm
tmpfs           6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount
root@nginx-azurefile:/# mount | grep cifs
//pvc3329812692002.file.core.windows.net/andy-mgwin1710-dynamic-pvc-7b5346be-d577-11e7-bc95-000d3a041274 on /mnt/blobfile type cifs (rw,relatime,vers=3.0,cache=strict,username=pvc3329812692002,domain=,uid=0,noforceuid,gid=0,noforcegid,addr=52.239.184.8,file_mode=0777,dir_mode=0777,persistenthandles,nounix,serverino,mapposix,rsize=1048576,wsize=1048576,echo_interval=60,actimeo=1)
```

### Note
1. `fileMode`, `dirMode` would be set to `0700` and gid, uid would be set as `0` by default, you could override this mountOptions by following this guide:
https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/azurefile-mountoptions.md

2. `Premium` storage type is not supported for azure file

#### Links
[Azure file introduction](https://docs.microsoft.com/en-us/azure/storage/files/storage-files-introduction)

[Azure Files scale targets](https://docs.microsoft.com/en-us/azure/storage/common/storage-scalability-targets#azure-files-scale-targets)
