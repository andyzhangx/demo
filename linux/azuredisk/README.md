# Dynamic Provisioning for azure disk in Linux
## 1. create an azure disk storage class if `hdd` does not exist
 - If k8s agent pool is based on managed disk VM (by default)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azuredisk-managed.yaml
```

###### Note: 
 - AKS cluster use managed disk by default, there are already `managed-standard`, `managed-premium` built-in azure disk storage classes.

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

```sh
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
 > Note: static provisioning does not support disk that has partition, there could be [data loss if using existing azure disk with partitions in disk mount](https://github.com/andyzhangx/demo/blob/master/issues/azuredisk-issues.md#10-data-loss-if-using-existing-azure-disk-with-partitions-in-disk-mount), you could check the supported k8s version [here](https://github.com/andyzhangx/demo/blob/master/issues/azuredisk-issues.md#10-data-loss-if-using-existing-azure-disk-with-partitions-in-disk-mount)
#### Option#1 Ties an azure disk volume explicitly to a pod
 - managed disk
```sh
wget -O nginx-pod-azuredisk.yaml https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azuredisk/nginx-pod-azuredisk-static-mgrdisk.yaml
vi nginx-pod-azuredisk.yaml
kubectl create -f nginx-pod-azuredisk.yaml
```

#### Option#2 Create an azure disk PV & PVC and then create a pod based on PVC
 - download `pv-azuredisk-managed.yaml` file, modify `diskName`, `diskURI` fields and create an azure disk persistent volume(PV)
```sh
wget https://raw.githubusercontent.com/andyzhangx/demo/master/pv/pv-azuredisk-managed.yaml
vi pv-azuredisk-managed.yaml
kubectl create -f pv-azuredisk-managed.yaml
```

 - create an azure disk persistent volume claim(PVC)
```sh
 kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/pv/pvc-azuredisk-static.yaml
```

 - check status of PV & PVC until its Status changed from `Pending` to `Bound`
 ```sh
 kubectl get pv
 kubectl get pvc
 ```
 
 - create a pod with azure disk PVC
```sh
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azuredisk/nginx-pod-azuredisk.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-azuredisk```

#### enter the pod container to do validation
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
 - [Azure Disk Storage Class](https://kubernetes.io/docs/concepts/storage/storage-classes/#azure-disk)
 - [Persistent volumes with Azure disks](https://docs.microsoft.com/en-us/azure/aks/azure-disks-dynamic-pv)
 - [Azure Standard Disk Scalability and Performance Targets](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/standard-storage?toc=%2Fazure%2Fstorage%2Fblobs%2Ftoc.json#scalability-and-performance-targets)
 - [Azure Premium Disk Scalability and Performance Targets](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/premium-storage#premium-storage-disk-limits)
 - [Debug Azure disk attachment issue](https://github.com/andyzhangx/Demo/blob/master/linux/azuredisk/azuredisk-attachment-debugging.md)
 - [Exploring Windows Azure Drives, Disks, and Images](https://blogs.msdn.microsoft.com/windowsazurestorage/2012/06/27/exploring-windows-azure-drives-disks-and-images/)
 - [Kubernetes Persistent Volumes with Deployment and StatefulSet](https://akomljen.com/kubernetes-persistent-volumes-with-deployment-and-statefulset/)
 - [Troubleshoot Linux VM device name changes](https://learn.microsoft.com/en-us/troubleshoot/azure/virtual-machines/linux/troubleshoot-device-names-problems)
