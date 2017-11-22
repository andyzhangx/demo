## Current Status of Windows Server support for kubernetes on Windows
kubernetes on Windows is **under preview** status
Up to date 11/22/2017, k8s windows cluster could be created by two ways:

#### azure portal
Create "azure conatiner service" (not AKS) in azure portal, select `Windows` OS, if k8s cluster is created successfully, the master node would be still Ubuntu OS, agent node would be `Windows Server 2016 DataCenter`.
###### Note: azure disk & azure file mount feature is not enabled on this k8s cluster because it's using `Windows Server 2016 DataCenter` os.

#### acs-engine (https://github.com/Azure/acs-engine)
By acs-engine, you could deploy a `Windows Server version 1709` based k8s cluster which would support azure disk & azure file mount feature on Windows node. 
Up to date 11/22/2017, only latest master branch could deploy Windows 1709 k8s cluster.

#### azure disk & azure file mount feature on Windows node version supporting list
