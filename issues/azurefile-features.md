# Azure file new features and restrictions
## Azure file new features
#### 1. Azure file size grow

available from `v1.11.0`

only supported in dynamic provision, `allowVolumeExpansion: true` must be specified in azure file storage class, example: [azurefile storage class with size grow configuration](https://github.com/andyzhangx/demo/blob/master/pv/storageclass-azurefile-sizegrow.yaml)

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

#### 3. External resource group support for azure file PV dynamic provisioning
> all resource groups should be in same subscription, we don’t support cross-subscription scenario

example: https://github.com/andyzhangx/demo/blob/master/pv/storageclass-azurefile-external-rg.yaml

details: [support cross resource group for azure file](https://github.com/kubernetes/kubernetes/pull/68117)

| k8s version | fixed version |
| ---- | ---- |
| v1.8 | not supported |
| v1.9 | 1.9.11 |
| v1.10 | 1.10.9 |
| v1.11 | 1.11.4 |
| v1.12 | 1.12.0 |

#### 4. Use existing file share in azure file storage class
With PR [specify azure file share name in azure file plugin](https://github.com/kubernetes/kubernetes/pull/76988), user could specify azure file share name in azure file plugin, azure file plugin will create a new one if the specified file share name does not exist.

```
---
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: azurefile
provisioner: kubernetes.io/azure-file
parameters:
  skuName: Standard_LRS
  resourceGroup: EXISTING_RESOURCE_GROUP_NAME
  storageAccount: EXISTING_STORAGE_ACCOUNT_NAME
  shareName: SHARE_NAME
```

 - supported version
 
| k8s version | fixed version |
| ---- | ---- |
| v1.11 | not supported |
| v1.12 | 1.12.9 |
| v1.13 | 1.13.6 |
| v1.14 | 1.14.2 |
| v1.15 | 1.15.0 |
