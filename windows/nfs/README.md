# Attention: nfs mount on windows does not work now, this feature is working in progress
## 1. download `pv-nfs.yaml`, change `nfs` config and then create a nfs persistent volume (pv)
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
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/nfs/aspnet-nfs.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po aspnet-nfs

## 4. enter the pod container to do validation
kubectl exec -it aspnet-nfs -- cmd

```

```

### Instructions for using NFS on Windows Server
```
C:\Users\azureuser>powershell
Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

PS C:\Users\azureuser> Install-WindowsFeature NFS-Client
PS C:\Users\azureuser> exit

C:\Users\azureuser>mount \\{NFS-share} G:
G: is now successfully connected to \\andynfs.eastus2.cloudapp.azure.com\home\
The command completed successfully.
```
For details about NFS `mount` command, please refer to:
https://technet.microsoft.com/en-us/library/cc754350(v=ws.11).aspx


