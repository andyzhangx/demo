# Azure Container Service - AKS

## Steps to create an AKS cluster by [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
#### Prerequisite, define environment variables here:
```console
RESOURCE_GROUP_NAME=
CLUSTER_NAME=
LOCATION=westus2
```

#### 1. Create a resource group
```console
az group create -n $RESOURCE_GROUP_NAME -l $LOCATION
```

#### 2. Create an AKS cluster
```console
az aks create -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --node-count 2 --generate-ssh-keys --disable-rbac --kubernetes-version 1.8.1
```

#### 3. get aks cluster credentials
```console
az aks get-credentials -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME
```

#### 4. Get AKS nodes
```console
kubectl get nodes
```

#### 5. scale up/down AKS cluster nodes
```console
az aks scale -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --agent-count=2
```

#### 6. delete AKS cluster node
```console
az aks delete -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME
```

### Tips:
#### Get all avaialbe k8s verions on AKS cluster
```console
az aks get-versions -l $LOCATION -o table
```


### known issues
#### Create azure file PVC error

you may get following error when set up an azure file PVC:
```
Events:
From                            SubObjectPath   Type            Reason                  Message
----                            -------------   --------        ------                  -------
persistentvolume-controller     Warning         ProvisioningFailed      Failed to provision volume with StorageClass "azurefile": failed to find a matc
hing storage account
```

 - Workaround:
Create a `Standard_LRS` storage account in a `shadow resource group` which contains all resources of your aks cluster, naming as `MC_{RESOUCE-GROUP-NAME}{CLUSTER-NAME}{REGION}`, e.g. if you create an aks cluster `andy-aks182` in resouce group `aks` in westus2 region, then `shadow resource group` would be `MC_aks_andy-aks182_westus2`, wait for a few seconds, azure file PVC will be created successfully.

#### Image garbage collection

Current AKS kubelet default setting:
```
/usr/local/bin/kubelet
--image-gc-high-threshold=85
--image-gc-low-threshold=80
```

Kubernetes manages lifecycle of all images through imageManager, with the cooperation of cadvisor.

The policy for garbage collecting images takes two factors into consideration: `HighThresholdPercent` and `LowThresholdPercent`. Disk usage above the high threshold will trigger garbage collection. The garbage collection will delete least recently used images until the low threshold has been met.

https://kubernetes.io/docs/concepts/cluster-administration/kubelet-garbage-collection/#image-collection

to fasten the docker image cleanup, user could use following daemonset as workaround:
```console
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/dev/docker-image-cleanup.yaml
```

#### Kubernetes dashboard error due to RBAC enabled
please refer to https://docs.microsoft.com/en-us/azure/aks/kubernetes-dashboard#for-rbac-enabled-clusters

#### Issues
 - [Cannot set a different default storage class](https://github.com/Azure/AKS/issues/118#issuecomment-627860179)
 - [kubelet port 10255/10250](https://github.com/Azure/AKS/issues/1601#issuecomment-627922947)

#### Links
 - [Azure Container Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/)
 - [Deploy an Azure Container Service (AKS) cluster](https://docs.microsoft.com/en-us/azure/aks/kubernetes-walkthrough)
 - [Frequently asked questions about Azure Container Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/faq#are-security-updates-applied-to-aks-agent-nodes)
