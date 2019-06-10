# Azure NetApp Files (ANF) integration with AKS
[Azure NetApp Files](https://azure.microsoft.com/en-us/services/netapp/) is a managed NFS service on Azure, this article will show you how to create and Azure NetApp File and then give your AKS containers access to this shared file system.

## Limitations
 - Azure NetApp Files (ANF) is only available in a few Azure regions, including: US East, US West2, US South Central, US Central, EU West, and EU North. Customer needs to apply for whitelisting before using using this service. Find more details from [here](https://azure.microsoft.com/en-us/services/netapp/)
 - NFS data path in ANF does not go over the Internet, ANF must be created in the same virtual network with AKS
 - Currently only static provisioning(create ANF in advance) is supported on AKS
 
## Prerequisite
 - [Set up Azure NetApp Files and create an NFS volume](https://docs.microsoft.com/en-us/azure/azure-netapp-files/azure-netapp-files-quickstart-set-up-account-create-volumes), including following steps:
   - Create a NetApp account in the `nodeResourceGroup`(started with `MC_` by default)
   - Create a capacity pool
   - Create a volume, and select the same virtual network with AKS in volume setup, after volume is created, write down the NFS mount path in the `mount instructions` 

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
root@nginx-nfs:/# df -h
Filesystem      Size  Used Avail Use% Mounted on
...
10.0.0.5:/test  100T  320K  100T   1% /mnt/azure
...
```

### Links
 - [Manually create and use an NFS (Network File System) Linux Server volume with Azure Kubernetes Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/azure-nfs-volume)
 - [Set up Azure NetApp Files and create an NFS volume](https://docs.microsoft.com/en-us/azure/azure-netapp-files/azure-netapp-files-quickstart-set-up-account-create-volumes)
