# Azure NetApp Files (ANF) integration with AKS
[Azure NetApp Files](https://azure.microsoft.com/en-us/services/netapp/) is a managed NFS service on Azure, this article will show you how to create and Azure NetApp File and then give your AKS containers access to this shared file system.

## Limitations
 - Azure NetApp Files (ANF) is available in a few Azure regions
 - NFS data path in ANF does not go over the Internet, ANF must be created in the same virtual network with AKS
 - Currently only static provisioning(users create ANF in advance) is supported on AKS
 
## Prerequisite
 - [Set up Azure NetApp Files and create an NFS volume](https://docs.microsoft.com/en-us/azure/azure-netapp-files/azure-netapp-files-quickstart-set-up-account-create-volumes)
 > select the same virtual network with AKS in ANF setup and write down the NFS mount path in the `mount instructions` after set up completed

## 1. create a nfs persistent volume (pv)
 - download `pv-nfs.yaml`, change `nfs` config and then create a nfs persistent volume (pv)
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pv-nfs.yaml
vi pv-nfs.yaml
kubectl create -f pv-nfs.yaml
```

make sure pv is in `Available` status
```
kubectl describe pv pv-nfs
```

## 2. create a nfs persistent volume claim (pvc)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-nfs.yaml
```

make sure pvc is in `Bound` status
```
kubectl describe pvc pvc-nfs
```

## 3. create a pod with nfs mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/nfs/nginx-nfs.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```
watch kubectl describe po nginx-nfs
```

## 4. enter the pod container to do validation
```
kubectl exec -it nginx-nfs -- bash
root@nginx-nfs:/mnt/azure# df -h
Filesystem                            Size  Used Avail Use% Mounted on
overlay                                30G  3.9G   26G  14% /
tmpfs                                 6.9G     0  6.9G   0% /dev
tmpfs                                 6.9G     0  6.9G   0% /sys/fs/cgroup
nfstest.eastus2.cloudapp.azure.com:/   30G  1.3G   28G   5% /mnt/azure
/dev/sda1                              30G  3.9G   26G  14% /etc/hosts
shm                                    64M     0   64M   0% /dev/shm
tmpfs                                 6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount
```
