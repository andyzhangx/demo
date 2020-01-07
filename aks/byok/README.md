# How to create a BYOK(SSE+CMK) enabled AKS cluster

### Prerequisite
[BYOK(SSE+CMK)](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/disk-encryption) feature requires api-version `v2020-01-01`.
Now user could add one new parameter `az ask create --node-osdisk-diskencryptionset-id` command to create a BYOK enabled AKS cluster.

 - install azure cli extension
```
# update to latest azure-cli version
sudo apt-get update
sudo apt-get install azure-cli

az extension remove --name aks-preview
az extension add --source https://raw.githubusercontent.com/andyzhangx/demo/master/aks/byok/aks_preview-0.4.25-py2.py3-none-any.whl -y
az aks create -h
```
 
### 1. Create a DiskEncryptionSet
 - [azure cli command steps](./create-diskencryptionset.sh)
 - [powershell command steps](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/disk-encryption) 

### 2. Create an AKS cluster with BYOK(SSE+CMK) enabled
```console
RESOURCE_GROUP_NAME=
CLUSTER_NAME=
LOCATION=northeurope  #`northeurope`, `eastus2euap` regions are BYOK available

az group create -n $RESOURCE_GROUP_NAME -l $LOCATION
az aks create -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --node-count 1 --generate-ssh-keys --kubernetes-version 1.17.0 --node-osdisk-diskencryptionset-id 
/subscriptions/{subs-id}/resourceGroups/{rg-name}/providers/Microsoft.Compute/diskEncryptionSets/{diskEncryptionSet-name}

az aks get-credentials -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --overwrite-existing
kubectl get nodes
```
> `diskEncryptionSetID` format is like `/subscriptions/{subs-id}/resourceGroups/{rg-name}/providers/Microsoft.Compute/diskEncryptionSets/{diskEncryptionSet-name}`

### 3. Verify BYOK feature is working
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
