# Azure file new features and restrictions
## Azure file new features
#### 1. Azure file size grow

available from `v1.11.0`

example: [azurefile storage class with size grow configuration](https://github.com/andyzhangx/demo/blob/master/pv/storageclass-azurefile-sizegrow.yaml)

#### 2. Azure Premium file dynamic provision support

available from `v1.13.0`

details: [support Azure premium file dynamic provision in azure file plugin](https://github.com/kubernetes/kubernetes/pull/69718)

example: [azurefile storage class with premium file configuration](https://github.com/andyzhangx/demo/blob/master/pv/storageclass-azurefile-premium.yaml)

Even with old k8s version, e.g. 1.12.x, user still could use azure premium file by static provisioning: create an azure premium file in advance by user, and then use that azure file in k8s.
refer to https://docs.microsoft.com/en-us/azure/aks/azure-files-volume, the only difference in the doc is create a `Premium_LRS` storage account:
```
# Create the storage account
az storage account create -n $AKS_PERS_STORAGE_ACCOUNT_NAME -g $AKS_PERS_RESOURCE_GROUP -l $AKS_PERS_LOCATION --sku Premium_LRS
```
 
Kubernetes 1.13.0 has dynamic provisioning support for azure premium file(create a premium file by k8s), it’s more user friendly, refer to: https://docs.microsoft.com/en-us/azure/aks/azure-files-dynamic-pv
