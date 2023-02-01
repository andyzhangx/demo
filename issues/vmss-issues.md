# VM Scale Set(VMSS) related issues
### 1. VMSS instance is in a failed state
 - Check VMSS instance first by running following command
```
az vmss show -g <RESOURCE_GROUP_NAME> --name <VMSS_NAME> --instance-id <ID(number)>
```

 - fix it manully by running following command
```
az vmss update-instances -g <RESOURCE_GROUP_NAME> --name <VMSS_NAME> --instance-id <ID(number)>
```

#### Tips
 - detach a disk from a VMSS instance
```
az vmss disk detach -g <RESOURCE_GROUP_NAME> --name <VMSS_NAME> --instance-id <ID(number)> --lun number
```

 - attach a disk to a VMSS instance
```
az vmss disk attach -g <RESOURCE_GROUP_NAME> --name <VMSS_NAME> --instance-id <ID(number)> --lun number --disk <diskid>
```

 - change `osDisk.caching` on VMSS
```
az vmss update --name vmss-name --resource-group rg --set virtualMachineProfile.storageProfile.osDisk.caching="ReadOnly"
```
after running the above command successfully, click on the `Upgrade` button to update all VMSS instances to latest model

### 2. AttachDiskWhileBeingDetached issue
follow steps [Troubleshoot virtual machine deployment due to detached disks](https://docs.microsoft.com/en-us/azure/virtual-machines/troubleshooting/troubleshoot-vm-deployment-detached)
