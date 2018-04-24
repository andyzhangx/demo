## Current Status of Windows Server support for kubernetes on Azure
> kubernetes on Windows is **under preview** status.

## k8s windows cluster could be created by two ways:
### 1. azure portal
Create "Azure Conatiner Service" (**not** AKS) in azure portal, select `Windows` OS, if k8s cluster is created successfully, the master node would be still Ubuntu OS, agent node would be `Windows Server 2016 DataCenter`.
> Note: 
azure disk & azure file mount feature is **not** enabled on this because it's using `Windows Server 2016 DataCenter` OS, only `Windows Server version 1709` is supported for these two features.

### 2. [acs-engine](https://github.com/Azure/acs-engine)
By acs-engine **v0.9.2 or above**, you could deploy a `Windows Server version 1709` (codename `RS3`) based k8s cluster which would support azure disk & azure file mount feature on Windows node. 

You could check Windows version by following command, below is an example using `Windows Server version 1709`:
```
kubectl exec -it WINDOWS-PODNAME -- cmd
C:\Users\azureuser>ver
Microsoft Windows [Version 10.0.16299.19]  (or above)
```

Find more details about [Supported Windows versions](https://github.com/Azure/acs-engine/blob/master/docs/kubernetes/windows.md#supported-windows-versions)

## k8s volume support on Windows Server 1709
> Note: value of `Support on Windows` is empty means I don't have a chance to validate it on Windows

| Volume | Support on Windows | Example | Notes |
| ---- | ---- | ---- | ---- |
| azure disk | Yes | [azuredisk](./azuredisk) | Support from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1) |
| azure file | Yes | [azurefile](./azurefile) | Support from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1) |
| cephfs | No |  | No official support for cephfs support on windows, could use NFS instead |
| csi | No | [csi](./csi) | CSI on Windows does not work due to [Symlink for ca.crt & token files are broken on windows containers](https://github.com/kubernetes/kubernetes/issues/52419), details could be found in [Enable CSI hostpath example on windows](https://github.com/kubernetes-csi/drivers/issues/79) |
| downwardAPI | No |  | Same issue with secret, due to a [windows docker bug](https://github.com/kubernetes/kubernetes/issues/52419) |
| emptyDir | Yes | [emptydir](./emptydir) | tmpfs is not supported on Windows Server |
| fc (fibre channel) |  |  |  |
| flexvolume | Yes | [flexvolume](./flexvolume) | available from v1.8.6, v1.9.1 |
| flocker |  |  |  |
| gitRepo | No | [gitrepo](./gitrepo) | git is not built-in on Windows host now: [Enable gitRepo Volume on Windows](https://github.com/kubernetes/kubernetes/issues/57546) |
| glusterfs | No |  | Windows doesn't have a native GlusterFS client, could use NFS instead |
| hostpath | Yes | [hostpath](./hostpath) |  |
| iscsi | No |  | Windows container does not support iSCSI symbolic link: [Enable iSCSI volume on Windows](https://github.com/kubernetes/kubernetes/issues/57548) |
| local | Yes | [local](./local) | Beta in k8s v1.10, bug fix: [fix local volume issue on Windows](https://github.com/kubernetes/kubernetes/pull/62012) |
| nfs | No | | Pending: there is no NFSv4 client support on Windows now, see: [add NFS volume support for windows](https://github.com/kubernetes/kubernetes/issues/56188)  |
| PortworxVolume |  |  |  |
| projected |  |  |  |
| Quobyte |  |  |  |
| rbd | No |  |  |
| ScaleIO |  |  |  |
| secret | Partially | [secret](./secret) | text type works, while file type(e.g. “service-account-token”) does not work due to a [docker container on Windows bug](https://github.com/kubernetes/kubernetes/issues/52419)  |
| StorageOS |  |  |  |
| subPath | Yes | [subpath](./subpath) |  |

## other k8s feature support on Windows Server 1709
| Feature | Support on Windows | Example | Notes |
| ---- | ---- | ---- | ---- |
| ConfigMap | Partially | [configmap](./configmap) | Only support environment variables, volume mount does not work due to a [docker container on Windows bug](https://github.com/kubernetes/kubernetes/issues/52419) |
| cAdvisor | Yes | [cadvisor](./cadvisor) | from [Azure/kubernetes](https://github.com/Azure/kubernetes) v1.8.6 and k8s upstream v1.9.0 |

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

Windows agent node set up by acs-engine uses https://github.com/Azure/kubernetes, which contains more features than [upstream](https://github.com/kubernetes/kubernetes), e.g. azure disk & file on Windows features are available from [v1.7.2](https://github.com/Azure/kubernetes/tree/acs-v1.7.2-1), while these two features are avaiable from v1.9.0 in [upstream](https://github.com/kubernetes/kubernetes), while all Linux nodes(including master) use  [upstream](https://github.com/kubernetes/kubernetes).

4. How to check windows version in acs-engine template

open file _output/`dnsPrefix`/azuredeploy.json under acs-engine:
```
              "agentWindowsPublisher": "MicrosoftWindowsServer",
              "agentWindowsOffer": "WindowsServerSemiAnnual",
              "agentWindowsSku": "Datacenter-Core-1709-with-Containers-smalldisk"
```

##### Links
[Using Windows Server Containers in Kubernetes](https://kubernetes.io/docs/getting-started-guides/windows/)

[Microsoft Azure Container Service Engine - Kubernetes Windows Walkthrough](https://github.com/Azure/acs-engine/blob/master/docs/kubernetes/windows.md#supported-windows-versions)

[Windows Server version 1709](https://docs.microsoft.com/en-us/windows-server/get-started/whats-new-in-windows-server-1709)

[Windows Container Version Compatibility](https://docs.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/version-compatibility)

[Windows Containers Documentation](https://docs.microsoft.com/en-us/virtualization/windowscontainers/)


