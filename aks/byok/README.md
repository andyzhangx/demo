# How to create a BYOK(SSE+CMK) enabled AKS cluster

### Prerequisite
BYOK(SSE+CMK) feature requires api-version 'v2020-01-01', azure-cli AKS command is not ready for this api-version, need to leverage [armclient](https://github.com/yangl900/armclient-go) tool to create a BYOK enabled AKS cluster.
Currently region `eastus2euap` is available with both BYOK and api-version 'v2020-01-01' supported.

 - install armclient
```
curl -sL https://github.com/yangl900/armclient-go/releases/download/v0.2.3/armclient-go_linux_64-bit.tar.gz | tar xz
```

 - how to configure armclient
 
 refer to https://github.com/yangl900/armclient-go#how-to-use-it
 
### 1. Create a DiskEncryptionSet
 - [azure cli command steps](./byok.md)
 - [powershell command steps](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/disk-encryption) 

### 2. Write an AKS cluster creation file with BYOK(SSE+CMK) enabled
```
wget -O create-cluster.json https://raw.githubusercontent.com/andyzhangx/demo/master/aks/byok/create-cluster.json
# fill in following fields
dnsPrefix, clientId, secret, diskEncryptionSetID
```
> `diskEncryptionSetID` format is like `/subscriptions/{subs-id}/resourceGroups/{rg-name}/providers/Microsoft.Compute/diskEncryptionSets/{diskEncryptionSet-name}`

### 3. Create an AKS cluster with api-version 'v2020-01-01'

 - Canary region
```sh
armclient put https://eastus2euap.management.azure.com/subscriptions/{subs-id}/resourceGroups/{rg}/providers/Microsoft.ContainerService/managedClusters/{cluster-name}?api-version=2020-01-01 @./create-cluster.json
```

 - Producition region (not ready yet)
```sh
armclient put https://management.azure.com/subscriptions/{subs-id}/resourceGroups/{rg}/providers/Microsoft.ContainerService/managedClusters/{cluster-name}?api-version=2020-01-01 @./create-cluster.json
```

### 4. Verify BYOK feature is working
 - Make sure all agent nodes are up
```sh
kubectl get no
```
 - Revoke DiskEncryptionSet access to azure key vault

In azure portal: remove DiskEncryptionSet in "Azure Key Vault"\"Access policies" and click "Save"
 - After a few minutes, make sure all agent nodes are down
 - Grant DiskEncryptionSet access to azure key vault

In azure portal: go to DiskEncryptionSet page, there is a hint to add access to "Azure Key Vault" automatically
 - After a few minutes, make sure all agent nodes are up
