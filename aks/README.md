# Azure Container Service - AKS

## Steps to create an AKS cluster by [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
#### Prerequisite, define environment variables here:
```
RESOURCE_GROUP_NAME=
CLUSTER_NAME=
LOCATION=westus2
```

#### 1. Create a resource group
```
az group create -n $RESOURCE_GROUP_NAME -l $LOCATION
```

#### 2. Create an AKS cluster
```
az aks create -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --agent-count 2 --generate-ssh-keys --kubernetes-version 1.8.1
```

#### 3. get aks cluster credentials
```
az aks get-credentials -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME
```

#### 4. Get AKS nodes
```
kubectl get nodes
```

#### 5. scale up/down AKS cluster nodes
```
az aks scale -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --agent-count=2
```

#### 5. delete AKS cluster node
```
az aks delete -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME
```

#### known issues
 - Create azure file PVC error

you may get following error when set up an azure file PVC:
```
Events:
From                            SubObjectPath   Type            Reason                  Message
----                            -------------   --------        ------                  -------
persistentvolume-controller     Warning         ProvisioningFailed      Failed to provision volume with StorageClass "azurefile": failed to find a matc
hing storage account
```

Workaround is as following:
Create a `Standard_LRS` storage account in a `shadow resource group` which contains all resources of your aks cluster, naming as `MC_+{RESOUCE-GROUP-NAME}+{CLUSTER-NAME}+{REGION}`, e.g. if you create an aks cluster `andy-aks182` in resouce group `aks` in westus2 region, then `shadow resource group` would be `MC_aks_andy-aks182_westus2`, wait for a few seconds, azure file PVC will be created successfully.

#### Links
 - [Azure Container Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/)

 - [Deploy an Azure Container Service (AKS) cluster](https://docs.microsoft.com/en-us/azure/aks/kubernetes-walkthrough)

 - [Frequently asked questions about Azure Container Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/faq#are-security-updates-applied-to-aks-agent-nodes)
