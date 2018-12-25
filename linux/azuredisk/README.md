# Dynamic Provisioning for azure disk in Linux
## 1. create an azure disk storage class if `hdd` does not exist
 - If k8s agent pool is based on managed disk VM (by default)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azuredisk-managed.yaml
```

 > - if k8s agent pool is based on blob based(unmanaged) disk VM
 > ```
 > kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azuredisk.yaml
 > ```

###### Note: 
 - managed disk mount feature is only supported from v1.7.2
 - AKS cluster use managed disk by default, there are already `managed-standard`, `managed-premium` built-in azure disk storage classes.

 > #### for k8s version < 1.7.2
 > download `storageclass-azuredisk-old.yaml` and modify `skuName`, `location` values
 > ```
 > wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azuredisk-old.yaml
 > vi storageclass-azuredisk-old.yaml
 > kubectl create -f storageclass-azuredisk-old.yaml
 > ```
> Note: for `storageclass-azuredisk-old.yaml`, k8s will find a suitable storage account that matches ```skuName``` and ```location``` in same resource group when provisioning azure disk

## 2. create an azure disk pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azuredisk.yaml```
#### make sure pvc is created successfully
```watch kubectl describe pvc pvc-azuredisk```

## 3. create a pod with azure disk pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azuredisk/nginx-pod-azuredisk.yaml```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-azuredisk```

## 4. enter the pod container to do validation
```kubectl exec -it nginx-azuredisk -- bash```

```
root@nginx-azuredisk:/# df -h
Filesystem      Size  Used Avail Use% Mounted on
overlay          30G  3.6G   26G  13% /
tmpfs           6.9G     0  6.9G   0% /dev
tmpfs           6.9G     0  6.9G   0% /sys/fs/cgroup
/dev/sda1        30G  3.6G   26G  13% /etc/hosts
/dev/sdc        4.8G   10M  4.6G   1% /mnt/disk
shm              64M     0   64M   0% /dev/shm
tmpfs           6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount
```
# Static Provisioning for azure disk
 > Note: static provisioning does not support disk that has partition, there could be [data loss if using existing azure disk with partitions in disk mount](https://github.com/andyzhangx/demo/blob/master/issues/azuredisk-issues.md#10-data-loss-if-using-existing-azure-disk-with-partitions-in-disk-mount)
#### 1. create an azure disk manually in the same resource group and modify `nginx-pod-azuredisk.yaml`
 - managed disk
```
wget -O nginx-pod-azuredisk.yaml https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azuredisk/nginx-pod-azuredisk-static-mgrdisk.yaml
vi nginx-pod-azuredisk.yaml
```

 - blob based(unmanaged) disk 
```
wget -O nginx-pod-azuredisk.yaml https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azuredisk/nginx-pod-azuredisk-static-blobdisk.yaml
vi nginx-pod-azuredisk.yaml
```

#### 2. create a pod with an azure disk mount
```kubectl create -f nginx-pod-azuredisk.yaml```

#### 3. watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-azuredisk```

## 4. enter the pod container to do validation
```kubectl exec -it nginx-azuredisk -- bash```

```
root@nginx-azuredisk:/# df -h
Filesystem      Size  Used Avail Use% Mounted on
overlay          30G  3.6G   26G  13% /
tmpfs           6.9G     0  6.9G   0% /dev
tmpfs           6.9G     0  6.9G   0% /sys/fs/cgroup
/dev/sda1        30G  3.6G   26G  13% /etc/hosts
/dev/sdc        4.8G   10M  4.6G   1% /mnt/disk
shm              64M     0   64M   0% /dev/shm
tmpfs           6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount
```

### [azure disk plugin known issues](https://github.com/andyzhangx/demo/blob/master/issues/azuredisk-issues.md)

#### Links
[Azure Disk Storage Class](https://kubernetes.io/docs/concepts/storage/storage-classes/#azure-disk)

[Persistent volumes with Azure disks](https://docs.microsoft.com/en-us/azure/aks/azure-disks-dynamic-pv)

[Azure Standard Disk Scalability and Performance Targets](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/standard-storage?toc=%2Fazure%2Fstorage%2Fblobs%2Ftoc.json#scalability-and-performance-targets)

[Azure Premium Disk Scalability and Performance Targets](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/premium-storage#premium-storage-disk-limits)

[Debug Azure disk attachment issue](https://github.com/andyzhangx/Demo/blob/master/linux/azuredisk/azuredisk-attachment-debugging.md)
