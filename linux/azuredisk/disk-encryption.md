# How to enable disk encryption on AKS
 - Before following steps, if your agent VM is going to mount an azure disk PV, please insert a UDEV rule first on the target VM(under `/etc/udev/rules.d/66-azure-storage.rules`) manually and then reboot (related PR: [Add a UDEV rule in azure disk encryption on Linux](https://github.com/Azure/WALinuxAgent/pull/1287), fixed in WALinuxAgent-2.2.32), otherwise there would be disk mount failure(related issue details: [Failed to mount Azure Disk as a PV when ADE is enabled](https://github.com/kubernetes/kubernetes/issues/66443)).
```
ATTRS{device_id}=="?00000001-0001-*", ENV{fabric_name}="BEK", GOTO="azure_names"
```
 > Notes: details could be found [here](https://github.com/kubernetes/kubernetes/issues/66443#issuecomment-406765240)
 
 - Follow below steps when AKS cluster is newly created
```
RESOURCE_GROUP_NAME=<resource_group_of_created_VM> #for AKS, format is like MC_{RESOUCE-GROUP-NAME}{CLUSTER-NAME}{REGION}
ADE_VAULT_NAME=<unique_vault_name>
VM_NAME=<created_VM_name> #for AKS, it's under MC_{RESOUCE-GROUP-NAME}{CLUSTER-NAME}{REGION}

az ad sp create-for-rbac --role="Contributor"
#assign APP_ID and SP_PASSWORD from the above output
APP_ID=
SP_PASSWORD=

az keyvault create -n $ADE_VAULT_NAME -g $RESOURCE_GROUP_NAME --enabled-for-disk-encryption True
az keyvault set-policy --name $ADE_VAULT_NAME --spn $APP_ID --key-permissions wrapKey  --secret-permissions set
az keyvault key create --vault-name $ADE_VAULT_NAME --name aks-ade-node1-key --protection software
az vm encryption enable -g $RESOURCE_GROUP_NAME -n $VM_NAME --aad-client-id $APP_ID --aad-client-secret $SP_PASSWORD --disk-encryption-keyvault $ADE_VAULT_NAME --key-encryption-key aks-ade-node1-key --volume-type DATA
```
Note: 
 - Allowed values for `volume-type`: `ALL`, `DATA`, `OS`
 - More details steps could be found from [Azure Disk Encryption for Windows and Linux IaaS VMs](https://docs.microsoft.com/en-us/azure/security/azure-security-disk-encryption)
 - VM restart may be required in the Azure Disk Encryption process, please make sure there is not workload on the target VM before encryption

#### Related issues
 - [Failed to mount Azure Disk as a PV when ADE is enabled](https://github.com/kubernetes/kubernetes/issues/66443)
 - [AKS VM Disk Encryption issue](https://github.com/Azure/AKS/issues/629)
 - [VM Encryption does not support Ubuntu 16.04.0-LTS](https://github.com/Azure/azure-cli/issues/2507)
