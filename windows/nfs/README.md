# Attention: nfs mount on windows does not work now, this feature is working in progress
## 1. download `pv-nfs.yaml`, change `nfs` config and then create a nfs persistent volume (pv)
```console
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pv-nfs.yaml
vi pv-nfs.yaml
kubectl create -f pv-nfs.yaml
```

make sure pv is in `Available` status
```console
kubectl describe pv pv-nfs
```

## 2. create a nfs persistent volume claim (pvc)
```console
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-nfs.yaml
```

make sure pvc is in `Bound` status
```console
kubectl describe pvc pvc-nfs
```

## 3. create a pod with nfs mount
```console
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/nfs/aspnet-nfs.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```console
watch kubectl describe po aspnet-nfs
```

## 4. enter the pod container to do validation
```console
kubectl exec -it aspnet-nfs -- cmd
```

### Instructions for using NFS on Windows Server

 - With the default options you will only have read permissions when mounting a UNIX share using the anonymous user. We can give the anonymous user write permissions by changing the UID and GID that it uses to mount the share. The image below shows the a share mounted using the default settings, refer to https://graspingtech.com/mount-nfs-share-windows-10/

```
C:\Users\azureuser>powershell
Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

PS C:\Users\azureuser> Install-WindowsFeature NFS-Client
PS C:\Users\azureuser> New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\ClientForNFS\CurrentVersion\Default\" -Name AnonymousUid -Value 0 -PropertyType DWORD
PS C:\Users\azureuser> New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\ClientForNFS\CurrentVersion\Default\" -Name AnonymousGid -Value 0 -PropertyType DWORD
PS C:\Users\azureuser> nfsadmin client stop
PS C:\Users\azureuser> nfsadmin client start
PS C:\Users\azureuser> exit
```
 - [`net use`](https://www.windowscommandline.com/net-use/) command
```
# net use /PERSISTENT:YES \\accountname.blob.core.windows.net\andyblobnfs\pvc-80e0b096-a126-4a05-a100-b957c2335e2e
The command completed successfully.

# mklink /D blobnfs \\accountname.blob.core.windows.net\andyblobnfs\pvc-80e0b096-a126-4a05-a100-b957c2335e2e
symbolic link created for blobnfs <<===>> \\andyblobnfs.blob.core.windows.net\andyblobnfs\pvc-80e0b096-a126-4a05-a100-b957c2335e2e

# docker run -v C:\Users\azureuser\blobnfs:C:\mnt --name busybox e2eteam/busybox:1.29 "mkdir C:\mnt\test2"
# docker rm busybox

# dir blobnfs
```

 - `mount` command
```
C:\Users\azureuser>mount \\{NFS-share} G:
G: is now successfully connected to \\{NFS-share}
The command completed successfully.

azureuser@4820k8s000 C:\Users\azureuser>mount

Local    Remote                                 Properties
-------------------------------------------------------------------------------
x:       \\storageacco.blob.core.windows.net\a~ UID=-2, GID=-2
                                                rsize=1048576, wsize=1048576
                                                mount=soft, timeout=0.8
                                                retry=1, locking=no
                                                fileaccess=755, lang=ANSI
                                                casesensitive=no
                                                sec=sys

```
For details about NFS `mount` command, please refer to: https://technet.microsoft.com/en-us/library/cc754350(v=ws.11).aspx

 - How to check nfs mount error code
 ```console
 >NET HELPMSG 53
The network path was not found.

 ```

 - [add NFS volume support for windows](https://github.com/kubernetes/kubernetes/issues/56188#issuecomment-459194116)

