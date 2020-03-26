# Shared disk(Multi-node ReadWrite)

Azure shared disk feature is already supported on [Azure Disk CSI driver](https://github.com/andyzhangx/azuredisk-csi-driver/tree/sharedisk-doc/deploy/example/sharedisk)

### Prerequisite
 - Make sure Azure shared disk is already registered with your subscription

Due to following [shared disk feature limitations](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/disks-shared-enable#limitations):
 - Availability sets and virtual machine scale sets can only be used with FaultDomainCount set to 1
 - All virtual machines sharing a disk must be deployed in the same proximity placement groups

AKS is not supported with `FaultDomainCount set to 1`, instead we could set up a Kubernetes cluster by aks-engine and manually configure `FaultDomainCount` to 1 and set proximity placement groups, here are the steps:
 - [install aks-engine](https://github.com/Azure/aks-engine/blob/master/docs/tutorials/quickstart.md)
 - modify aks-engine cluster definition file, below is an [example](https://github.com/andyzhangx/demo/blob/master/linux/azuredisk/sharedisk/aks-engine-sharedisk.json):
```console
wget https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/sharedisk/aks-engine-sharedisk.json
# edit all empty fields
```
  - generate aks-engine template
```console
./aks-engine generate ./aks-engine-sharedisk.json
```

 - configure `platformFaultDomainCount`, `platformUpdateDomainCount` to `1` in aks-engine template
```console
vi _output/xxx/azuredeploy.json
```
      "apiVersion": "[variables('apiVersionCompute')]",
      "location": "[variables('location')]",
      "name": "[variables('agentpoolAvailabilitySet')]",
      "properties": {
        "platformFaultDomainCount": **1**,
        "platformUpdateDomainCount": **1**
      },

 - create a kubernetes cluster on `westcentralus` region
```console
CLUSTER_NAME=andy-11174
RESOURCE_GROUP_NAME=$CLUSTER_NAME
az group create -l westcentralus -n $RESOURCE_GROUP_NAME
az group deployment create \
    --name="$CLUSTER_NAME" \
    --resource-group=$RESOURCE_GROUP_NAME \
    --template-file="./_output/$CLUSTER_NAME/azuredeploy.json" \
    --parameters "@./_output/$CLUSTER_NAME/azuredeploy.parameters.json"
```

 - Go to the resource group of the Kubernetes cluster in Azure portal
   - create a new proximity placement group in same region
   - stop all agent VMs
   - set proximity placement group in agent VM availability set or scaleset
   - start all agent VMs

### Install Azure Disk CSI driver on Kubernetes cluster

After Kubernetes cluster set up successfully, ssh to master node and [install Azure Disk CSI driver](https://github.com/andyzhangx/azuredisk-csi-driver/blob/sharedisk-doc/docs/install-csi-driver-master.md):
```console
curl -skSL https://raw.githubusercontent.com/kubernetes-sigs/azuredisk-csi-driver/master/deploy/install-driver-standalone.sh | bash -s --
```

### Try with shared disk feature

follow guide here: https://github.com/andyzhangx/azuredisk-csi-driver/tree/sharedisk-doc/deploy/example/sharedisk
