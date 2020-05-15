## Current Status of Windows Server support for kubernetes on Azure
> kubernetes on Windows is in **GA** stage.

## k8s windows cluster could be created by two ways:
### 1. azure portal
Create "Azure Conatiner Service" (**not** AKS) in azure portal, select `Windows` OS, if k8s cluster is created successfully, the master node would be still Ubuntu OS, agent node would be `Windows Server 2016 DataCenter`.
> Note: 
azure disk & azure file mount feature is **not** enabled on this because it's using `Windows Server 2016 DataCenter` OS, only `Windows Server version 1803` is supported for these two features.

### 2. [acs-engine](https://github.com/Azure/acs-engine)
By latest acs-engine **v0.9.2 or above**, you could deploy a `Windows Server version 1803` (codename `RS3`) based k8s cluster which would support azure disk & azure file mount feature on Windows node. 

You could check Windows version by following command, below is an example using `Windows Server version 1803`:
```
kubectl exec -it WINDOWS-PODNAME -- cmd
C:\Users\azureuser>ver
Microsoft Windows [Version 10.0.17134.48]  (or above)
```

Find more details about [Supported Windows versions](https://github.com/Azure/acs-engine/blob/master/docs/kubernetes/windows.md#supported-windows-versions)

## k8s volume support on Windows Server 1803
> Note: value of `Support on Windows` is empty means I don't have a chance to validate it on Windows

| Volume | Support on Windows | Example | Notes |
| ---- | ---- | ---- | ---- |
| azure disk | Yes | [azuredisk](./azuredisk) | Available from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1) |
| azure file | Yes | [azurefile](./azurefile) | Available from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1) |
| cephfs | No |  | No official support for cephfs support on windows, could use NFS instead |
| csi | on progress | [csi](./csi) | details could be found in [Enable CSI hostpath example on windows](https://github.com/kubernetes-csi/drivers/issues/79) |
| downwardAPI | Yes | [downwardapi](./downwardapi) |  |
| emptyDir | Yes | [emptydir](./emptydir) | tmpfs is not supported on Windows Server |
| fc (fibre channel) |  |  |  |
| flexvolume | Yes | [flexvolume](./flexvolume) | available from v1.8.6, v1.9.1 |
| flocker |  |  |  |
| gitRepo | No | [gitrepo](./gitrepo) | git is not built-in on Windows host now: [Enable gitRepo Volume on Windows](https://github.com/kubernetes/kubernetes/issues/57546) |
| glusterfs | No |  | Windows doesn't have a native GlusterFS client, could use NFS instead |
| hostpath | Yes | [hostpath](./hostpath) |  |
| iscsi | No |  | Windows container does not support iSCSI symbolic link: [Enable iSCSI volume on Windows](https://github.com/kubernetes/kubernetes/issues/57548) |
| local | Yes | [local](./local) | Available from 1.10.3 |
| nfs | No | | Pending: there is no NFSv4 client support on Windows now, see: [add NFS volume support for windows](https://github.com/kubernetes/kubernetes/issues/56188)  |
| PortworxVolume |  |  |  |
| projected |  |  |  |
| Quobyte |  |  |  |
| rbd | No |  |  |
| ScaleIO |  |  |  |
| secret | Yes | [secret](./secret) |  |
| StorageOS |  |  |  |
| subPath | Yes | [subpath](./subpath) |  |

## other k8s feature support on Windows Server 1803
| Feature | Support on Windows | Example | Notes |
| ---- | ---- | ---- | ---- |
| ConfigMap | Yes | [configmap](./configmap) |  |
| cAdvisor | Yes | [cadvisor](./cadvisor) | from [Azure/kubernetes](https://github.com/Azure/kubernetes) v1.8.6 and k8s upstream v1.9.0 |

##### Note
1. **breaking change** for Windows container running on `Windows Server version 1803`, only image tag with `1803` keyword could run on `Windows Server version 1803`, e.g.
```
microsoft/aspnet:4.7.2-windowsservercore-1803
microsoft/windowsservercore:1803
microsoft/iis:windowsservercore-1803
```

You may get following error if you try to run a legacy image on `Windows Server version 1803`
```
C:\k>docker run -d --name iis microsoft/iis
b08d4e031b8203446aedf7cc81ea110ac55009293ded373dfab2271505f6ee75
docker: Error response from daemon: container b08d4e031b8203446aedf7cc81ea110ac55009293ded373dfab2271505f6ee75 encountered an error during CreateContainer: failure in a Windows system call: The operating system of the container does not match the operating system of the host. (0xc0370101) extra info:
...
```

2. "Azure Conatiner Service - AKS" does not support Windows yet.

3. About k8s version on Windows node (deployed by acs-engine).

Windows agent node set up by acs-engine uses https://github.com/Azure/kubernetes, which contains more features than [upstream](https://github.com/kubernetes/kubernetes), e.g. azure disk & file on Windows features are available from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1), while these two features are avaiable from v1.9.0 in [upstream](https://github.com/kubernetes/kubernetes), while all Linux nodes(including master) use  [upstream](https://github.com/kubernetes/kubernetes).

4. How to check windows version in acs-engine template

open file _output/`dnsPrefix`/azuredeploy.json under acs-engine:
```
              "agentWindowsPublisher": "MicrosoftWindowsServer",
              "agentWindowsOffer": "WindowsServerSemiAnnual",
              "agentWindowsSku": "Datacenter-Core-1803-with-Containers-smalldisk"
```

##### Known bugs
 - [Symlink are broken on windows containers](https://github.com/kubernetes/kubernetes/issues/52419)

Fixed in Windows Server 1809

##### mountPath translation for Windows pod
 - [MakeAbsolutePath](https://github.com/kubernetes/kubernetes/blob/71277de4d62012631f54dfee606e72eb3eb35ab9/pkg/volume/util/util.go#L486-L502)
 - [kubelet_pods.go](https://github.com/kubernetes/kubernetes/blob/71277de4d62012631f54dfee606e72eb3eb35ab9/pkg/kubelet/kubelet_pods.go#L227-L236)

##### Links
 - [Using Windows Server Containers in Kubernetes](https://kubernetes.io/docs/getting-started-guides/windows/)
 - [Microsoft Azure Container Service Engine - Kubernetes Windows Walkthrough](https://github.com/Azure/acs-engine/blob/master/docs/kubernetes/windows.md#supported-windows-versions)
 - [Windows Server version 1709](https://docs.microsoft.com/en-us/windows-server/get-started/whats-new-in-windows-server-1709)
 - [Windows Container Version Compatibility](https://docs.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/version-compatibility)
 - [Windows Containers Documentation](https://docs.microsoft.com/en-us/virtualization/windowscontainers/)
 - [PowerShell equivalents for common Linux/bash commands](https://mathieubuisson.github.io/powershell-linux-bash/)

