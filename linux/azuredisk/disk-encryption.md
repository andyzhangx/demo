# How to enable disk encryption on AKS
 - Prerequisite
 
VM restart may be required in the Azure Disk Encryption process, please make sure there is no workload on the target VM before encryption: run `kubectl drain no <NODE-NAME>` to make sure there is not workload on that VM before encryption.

 - Follow below steps when AKS cluster is newly created
```
RESOURCE_GROUP_NAME=<resource_group_of_created_VM> #for AKS, format is like MC_{RESOUCE-GROUP-NAME}{CLUSTER-NAME}{REGION}
ADE_VAULT_NAME=<unique_vault_name>
VM_NAME=<created_VM_name> #for AKS, it's under MC_{RESOUCE-GROUP-NAME}{CLUSTER-NAME}{REGION}

az ad sp create-for-rbac --role="Contributor"  # or get sp directly from "/etc/kubernetes/azure.json"
#assign APP_ID and SP_PASSWORD from the above output
APP_ID=
SP_PASSWORD=

az keyvault create -n $ADE_VAULT_NAME -g $RESOURCE_GROUP_NAME --enabled-for-disk-encryption True
az keyvault set-policy --name $ADE_VAULT_NAME --spn $APP_ID --key-permissions wrapKey  --secret-permissions set
az keyvault key create --vault-name $ADE_VAULT_NAME --name aks-ade-node1-key --protection software
# this operation may cost 6 min and require VM restart
az vm encryption enable -g $RESOURCE_GROUP_NAME -n $VM_NAME --aad-client-id $APP_ID --aad-client-secret $SP_PASSWORD --disk-encryption-keyvault $ADE_VAULT_NAME --key-encryption-key aks-ade-node1-key --volume-type DATA
```

Note: 
 - For newly attached disk, it's not encrypted, need to run `az vm encryption enable` command to encrypt again
 - Allowed values for `volume-type`: `ALL`, `DATA`, `OS` (only encrypt `DATA` disk is more stable)
 - More details steps could be found from [Azure Disk Encryption for Windows and Linux IaaS VMs](https://docs.microsoft.com/en-us/azure/security/azure-security-disk-encryption)
 - 

#### Related issues
 - [Failed to mount Azure Disk as a PV when ADE is enabled](https://github.com/kubernetes/kubernetes/issues/66443)
 - [AKS VM Disk Encryption issue](https://github.com/Azure/AKS/issues/629)
 - [VM Encryption does not support Ubuntu 16.04.0-LTS](https://github.com/Azure/azure-cli/issues/2507)
 - [UDEV rule missing issue](https://github.com/kubernetes/kubernetes/issues/66443#issuecomment-406765240): already fixed in AKS and aks-engine by WALinuxAgent-2.2.32
