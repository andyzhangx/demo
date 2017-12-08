## Current Status of Windows Server support for kubernetes on Azure
### kubernetes on Windows is **under preview** status.

## k8s windows cluster could be created by two ways:
### 1. azure portal
Create "Azure Conatiner Service" (**not** AKS) in azure portal, select `Windows` OS, if k8s cluster is created successfully, the master node would be still Ubuntu OS, agent node would be `Windows Server 2016 DataCenter`.
##### Note: 
azure disk & azure file mount feature is **not** enabled on this because it's using `Windows Server 2016 DataCenter` OS, only `Windows Server version 1709` is supported for these two features.

### 2. [acs-engine](https://github.com/Azure/acs-engine)
By acs-engine **v0.9.2 or above**, you could deploy a `Windows Server version 1709` (codename `RS3`) based k8s cluster which would support azure disk & azure file mount feature on Windows node. 

You could check Windows version by following command, below is an example using `Windows Server version 1709`:
```
kubectl exec -it WINDOWS-PODNAME -- cmd
C:\Users\azureuser>ver
Microsoft Windows [Version 10.0.16299.19]
```

## k8s volume support on Windows Server 1709
| Volume | Support on Windows | Example | Notes |
| ---- | ---- | ---- | ---- |
| azure disk | Yes | [azuredisk](https://github.com/andyzhangx/Demo/tree/master/windows/azuredisk) | Support from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1) |
| azure file | Yes | [azurefile](https://github.com/andyzhangx/Demo/tree/master/windows/azurefile) | Support from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1) |
| cephfs | No |  | No official support for cephfs support on windows, could use NFS instead |
| downwardAPI | No |  | Same issue with secret, due to a [windows docker bug](https://github.com/kubernetes/kubernetes/issues/52419) |
| emptyDir | Yes | [emptydir](https://github.com/andyzhangx/Demo/tree/master/windows/emptydir) | tmpfs is not supported on Windows Server |
| fc (fibre channel) |  |  |  |
| flexvolume | Yes | [flexvolume](https://github.com/andyzhangx/Demo/tree/master/windows/flexvolume) | working on this [feature](https://github.com/kubernetes/kubernetes/issues/56875) [PR#56921](https://github.com/kubernetes/kubernetes/pull/56921) (code in review) |
| flocker |  |  |  |
| gitRepo |  |  | git is not built-in on Windows host now |
| glusterfs | No |  | Windows doesn't have a native GlusterFS client, could use NFS instead |
| hostpath | Yes | [hostpath](https://github.com/andyzhangx/Demo/tree/master/windows/hostpath) |  |
| iscsi | No |  | Windows container does not support iSCSI symbolic link |
| local |  |  | It's alpha in k8s v1.9 |
| nfs | No |  |  |
| PortworxVolume |  |  |  |
| projected |  |  |  |
| Quobyte |  |  |  |
| rbd | No |  |  |
| ScaleIO |  |  |  |
| secret | Partially | [secret](https://github.com/andyzhangx/Demo/tree/master/windows/secret) | text type works, while file type(e.g. “service-account-token”) does not work due to a [windows docker bug](https://github.com/kubernetes/kubernetes/issues/52419)  |
| StorageOS |  |  |  |
| subPath | Yes | [subpath](https://github.com/andyzhangx/Demo/tree/master/windows/subpath) |  |

## other k8s feature support on Windows Server 1709
| Feature | Support on Windows | Example | Notes |
| ---- | ---- | ---- | ---- |
| ConfigMap | Yes | [configmap](https://github.com/andyzhangx/Demo/tree/master/windows/configmap) |  |

##### Note
1. **breaking change** for Windows container running on `Windows Server version 1709`, only image tag with `1709` keyword could run on `Windows Server version 1709`, e.g.
```
microsoft/aspnet:4.7.1-windowsservercore-1709
microsoft/windowsservercore:1709
microsoft/iis:windowsservercore-1709
```

You may get following error if you try to run a legacy image on `Windows Server version 1709`
```
C:\k>docker run -d --name iis microsoft/iis
b08d4e031b8203446aedf7cc81ea110ac55009293ded373dfab2271505f6ee75
docker: Error response from daemon: container b08d4e031b8203446aedf7cc81ea110ac55009293ded373dfab2271505f6ee75 encountered an error during CreateContainer: failure in a Windows system call: The operating system of the container does not match the operating system of the host. (0xc0370101) extra info:
...
```

2. "Azure Conatiner Service - AKS" does not support Windows yet.

3. About k8s version on Windows node (deployed by acs-engine).

k8s version on Windows node use https://github.com/Azure/kubernetes, while all Linux nodes(including master) use https://github.com/kubernetes/kubernetes.

###### Links
About `Windows Server version 1709`: https://docs.microsoft.com/en-us/windows-server/get-started/whats-new-in-windows-server-1709

Windows Container Version Compatibility:
https://docs.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/version-compatibility
