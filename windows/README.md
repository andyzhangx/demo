## Current Status of Windows Server support for kubernetes on Windows
kubernetes on Windows is **under preview** status.

k8s windows cluster could be created by two ways:

#### azure portal
Create "azure conatiner service" (not AKS) in azure portal, select `Windows` OS, if k8s cluster is created successfully, the master node would be still Ubuntu OS, agent node would be `Windows Server 2016 DataCenter`.
###### Note: azure disk & azure file mount feature is not enabled on this k8s cluster because it's using `Windows Server 2016 DataCenter` os.

#### acs-engine (https://github.com/Azure/acs-engine)
By acs-engine **v0.9.2 or above**, you could deploy a `Windows Server version 1709` (also called `RS3`) based k8s cluster which would support azure disk & azure file mount feature on Windows node. 

#### azure disk & azure file mount feature on Windows node version supporting list
