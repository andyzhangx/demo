# How to create a BYOK(SSE+CMK) enabled AKS cluster

### Prerequisite
BYOK(SSE+CMK) feature requires api-version 'v2020-01-01', azure-cli AKS command is not ready for this api-version, need to leverage [armclient](https://github.com/yangl900/armclient-go) tool to create a BYOK enabled AKS cluster.

 - install armclient
```
curl -sL https://github.com/yangl900/armclient-go/releases/download/v0.2.3/armclient-go_linux_64-bit.tar.gz | tar xz
```

 - how to configure armclient
 
 refer to https://github.com/yangl900/armclient-go#how-to-use-it
 
### 1. Create a DiskEncryptionSet

### 2. Write an AKS cluster creation file with BYOK(SSE+CMK) enabled

### 3. Create an AKS cluster with api-version 'v2020-01-01'

 - Canary region
```sh
armclient put https://eastus2euap.management.azure.com/subscriptions/{subs-id}/resourceGroups/{rg}/providers/Microsoft.ContainerService/managedClusters/{cluster-name}?api-version=2020-01-01 @./create-cluster.json
```

 - Producition region (not ready yet)
```sh
armclient put https://management.azure.com/subscriptions/{subs-id}/resourceGroups/{rg}/providers/Microsoft.ContainerService/managedClusters/{cluster-name}?api-version=2020-01-01 @./create-cluster.json
```
