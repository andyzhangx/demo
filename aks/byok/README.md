# How to create a BYOK(SSE+CMK) enabled AKS cluster

### Prerequisite
[BYOK(SSE+CMK)](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/disk-encryption) feature requires api-version `v2020-01-01`.
Now user could use `az ask create --node-osdisk-diskencryptionset-id` command to create a BYOK enabled AKS cluster.

Make sure your subscription is whitelisted by azure disk team, otherwise you may get following error when create a BYOK enabled AKS cluster:
```console
# az aks create ... --kubernetes-version 1.17.0 --node-osdisk-diskencryptionset-id /subscriptions/{subs-id}/resourceGroups/{rg-name}/providers/Microsoft.Compute/diskEncryptionSets/{diskEncryptionSet-name}
Deployment failed. Correlation ID: efeb8ef5-aa92-45e9-b5b3-7c62ee1b5411. VMSSAgentPoolReconciler retry failed: deployment operations failed with error messages: {
  "code": "InvalidParameter",
  "message": "Parameter 'diskEncryptionSets' is not allowed.",
  "target": "diskEncryptionSets"
 }
```

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
> make sure current user role is `Owner` in the subscription, otherwise you may get key vault access assignment error

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
 - `diskEncryptionSetID` format is like `/subscriptions/{subs-id}/resourceGroups/{rg-name}/providers/Microsoft.Compute/diskEncryptionSets/{diskEncryptionSet-name}`


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

### 4. Data disk(disk volume) BYOK supported since 1.17.0
User could use this azure disk storage class: https://github.com/andyzhangx/demo/blob/master/pv/storageclass-azuredisk-byok.yaml, the above E2E BYOK scenario also applies to data disk.

From k8s v1.17.1, azure data disk would use same encryption key as os disk if key is not provided by user.
