# How to create an EncryptionAtHost supported AKS cluster

This doc shows how to set up an EncryptionAtHost supported AKS cluster.

### About EncryptionAtHost feature (Preview)
EncryptionAtHost could encrypt temp disk, cache of OS and data disk at rest. 
Refer to [End to end encryption of VM/VMSS disks in preview](https://github.com/ramankumarlive/manageddisksendtoendencryptionpreview) for more details about EncryptionAtHost feature

### [EncryptionAtHost supported regions](https://docs.microsoft.com/en-us/azure/virtual-machines/disk-encryption#supported-regions-1)

### Prerequisite
 - install [azure cli extension](https://docs.microsoft.com/en-us/cli/azure/azure-cli-extensions-overview?view=azure-cli-latest)

```console
az extension add --name aks-preview
```

 - register `EncryptionAtHost` feature under `Microsoft.Compute`
```console
az feature register --name EncryptionAtHost --namespace Microsoft.Compute
az feature list -o table --query "[?contains(name, 'Microsoft.Compute/EncryptionAtHost')].{Name:name,State:properties.state}"
az provider register --namespace Microsoft.Compute
```

 - register `EncryptionAtHost` feature under `Microsoft.ContainerService`
```console
az feature register --name EnableEncryptionAtHostPreview --namespace Microsoft.ContainerService
az feature list -o table --query "[?contains(name, 'Microsoft.ContainerService/EnableEncryptionAtHostPreview')].{Name:name,State:properties.state}"
az provider register --namespace Microsoft.ContainerService
```

### 1. Create an AKS cluster with EncryptionAtHost enabled
> make sure `node-vm-size` is in the supported EncryptionAtHost SKU list
```console
RESOURCE_GROUP_NAME=
CLUSTER_NAME=
LOCATION=westus2

az group create -n $RESOURCE_GROUP_NAME -l $LOCATION
az aks create -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --node-count 2 --node-vm-size Standard_DS2_v2 --generate-ssh-keys --kubernetes-version 1.17.5 --aks-custom-headers EnableEncryptionAtHost=true

az aks get-credentials -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --overwrite-existing
kubectl get nodes
```

### 2. Add a new node pool with EncryptionAtHost enabled
```console
az aks nodepool add --name nodepool2 --cluster-name $CLUSTER_NAME --resource-group $RESOURCE_GROUP_NAME --aks-custom-headers EnableEncryptionAtHost=true
```

#### Verification
 - After EncryptionAtHost is enabled on the AKS cluster, there would be a new `securityProfile` in deployment template:
```json
                    "securityProfile": {
                        "encryptionAtHost": "true"
                    },
```
you could also check by Azure cli:
 - EncryptionAtHost is enabled on VMSS cluster
```console
rgName=
vmssName=
az vmss show -n $vmssName -g $rgName --query "[virtualMachineProfile.securityProfile.encryptionAtHost]"
[
  true
]
```
 - EncryptionAtHost is not enabled on VMSS cluster
```console
az vmss show -n $vmssName -g $rgName --query "[virtualMachineProfile.securityProfile.encryptionAtHost]"
[
  null
]
```


### Limitations
 - EncryptionAtHost is only supported on VMSS
 - EncryptionAtHost is only supported on new cluster creation
