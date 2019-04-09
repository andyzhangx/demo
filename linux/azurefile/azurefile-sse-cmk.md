## Azure File plugin on kubernetes: using Storage Service Encryption(SSE) with customer-managed keys(CMK)
SSE+CMK is now available for Azure Files, this page shows how to use this feature on azure file plugin

### Prerequisite:
#### Follow below guide to enable SSE+CMK on an existing storage account
[Storage Service Encryption using customer-managed keys in Azure Key Vault](https://docs.microsoft.com/en-us/azure/storage/common/storage-service-encryption-customer-managed-keys?toc=%2fazure%2fstorage%2fblobs%2ftoc.json)

 > Note: In AKS, the specified storage account should be under a `shadow resource group`(naming as `MC_+{RESOUCE-GROUP-NAME}+{CLUSTER-NAME}+{REGION}`) which contains all resources of your aks cluster.

### Azure File Dynamic Provisioning
#### 1. Create an azure file storage class which would provision azure file PVC under that the above storage account with SSE+CMK enabled
```
wget https://raw.githubusercontent.com/andyzhangx/demo/master/pv/storageclass-azurefile-cmk.yaml
# edit storageAccount and skuName fields
vi storageclass-azurefile-sse-cmk.yaml
```

#### 2. create an azure file PVC
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azurefile-cmk.yaml```

> make sure pvc is created successfully
```watch kubectl describe pvc pvc-azurefile```


#### 3. create a pod with azure file pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azurefile/nginx-pod-azurefile.yaml```

 > watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-azurefile```

#### 4. enter the pod container to do validation
```kubectl exec -it nginx-azurefile -- bash```

### Azure File Static Provisioning
refer to [Manually create and use a volume with Azure Files share in Azure Kubernetes Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/azure-files-volume)
