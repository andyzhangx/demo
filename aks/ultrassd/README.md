# How to create an UltraSSD enabled AKS cluster

This doc shows how to set up an UltraSSD enabled AKS cluster.

### About UltraSSD feature (Preview)
Azure ultra disks offer high throughput, high IOPS, and consistent low latency disk storage for your stateful applications. Refer to [End to end encryption of VM/VMSS disks in preview](https://docs.microsoft.com/en-us/azure/virtual-machines/disks-enable-ultra-ssd) for more details about UltraSSD feature

### [UltraSSD supported regions and vm skus](https://docs.microsoft.com/en-us/azure/virtual-machines/disks-enable-ultra-ssd?tabs=azure-portal#ga-scope-and-limitations)

### Prerequisite
 - install [azure cli extension](https://docs.microsoft.com/en-us/cli/azure/azure-cli-extensions-overview?view=azure-cli-latest) `0.5.17` or later version

```console
az extension remove --name aks-preview
az extension add -y -n aks-preview
az version
{
  "azure-cli": "2.18.0",
  "azure-cli-core": "2.18.0",
  "azure-cli-telemetry": "1.0.6",
  "extensions": {
    "aks-preview": "0.5.17",
    "hack": "0.1.0"
  }
}
```

### 1. Create an AKS cluster with UltraSSD enabled
> make sure `node-vm-size` is in the supported UltraSSD SKU list
```console
RESOURCE_GROUP_NAME=
CLUSTER_NAME=
LOCATION=eastus2

az group create -n $RESOURCE_GROUP_NAME -l $LOCATION
az aks create -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --node-count 2 --generate-ssh-keys --kubernetes-version 1.20.5 --node-vm-size Standard_D2s_v3 --zones 1 2 3 --enable-ultra-ssd

az aks get-credentials -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --overwrite-existing
kubectl get nodes
```

### 2. Add a new node pool with UltraSSD enabled
```console
az aks nodepool add --name nodepool2 --cluster-name $CLUSTER_NAME --resource-group $RESOURCE_GROUP_NAME  --node-vm-size Standard_D2s_v3 --zones 1 2 3 --enable-ultra-ssd
```

#### Verification
 - After UltraSSD is enabled on the AKS cluster, there would be a new `additionalCapabilities` in deployment template:
```json
  "additionalCapabilities": {
    "ultraSsdEnabled": true
  }
```
you could also check by Azure cli:
 - UltraSSD is enabled on VMSS cluster
```console
rgName=
vmssName=
az vmss show -n $vmssName -g $rgName --query "[additionalCapabilities]"
[
  {
    "ultraSsdEnabled": true
  }
]
```
