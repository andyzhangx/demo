# Azure Container Service - AKS

## Steps to create an AKS cluster by [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
#### 1. Create a resource group
```
az group create -n RESOURCE_GROUP_NAME -l LOCATION
```

#### 2. Create an AKS cluster
```
az aks create -g RESOURCE_GROUP_NAME -n CLUSTER_NAME --agent-count 2 --generate-ssh-keys
```

#### 3. get aks cluster credentials
```
az aks get-credentials -g RESOURCE_GROUP_NAME -n CLUSTER_NAME
```

#### 4. Get AKS nodes
```
kubectl get nodes
```

#### 5. scale up/down AKS cluster nodes
```
az aks scale -g RESOURCE_GROUP_NAME -n CLUSTER_NAME --agent-count=2
```

#### known issues
1. default storage class is not set by default in AKS cluster, see issue: https://github.com/Azure/AKS/issues/48
you may get following error when set up a PVC with a default storage class:
```
Events:
From                            SubObjectPath   Type            Reason          Message
----                            -------------   --------        ------          -------
 persistentvolume-controller    Normal          FailedBinding   no persistent volumes available for this claim and no storage class is set
```
Workaround is as following:
```
kubectl patch storageclass default -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

2. Create azure file PVC error
you may get following error when set up an azure file PVC:
```
Events:
From                            SubObjectPath   Type            Reason                  Message
----                            -------------   --------        ------                  -------
persistentvolume-controller     Warning         ProvisioningFailed      Failed to provision volume with StorageClass "azurefile": failed to find a matc
hing storage account
```

Workaround is as following:
Create a `Standard_LRS` storage account in the same resource group with AKS cluster and wait for a few seconds, azure file PVC will be created successfully.

#### Links
[Deploy an Azure Container Service (AKS) cluster](https://docs.microsoft.com/en-us/azure/aks/kubernetes-walkthrough)
