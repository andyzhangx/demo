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

### 2. AttachDiskWhileBeingDetached issue
follow steps [Troubleshoot virtual machine deployment due to detached disks](https://docs.microsoft.com/en-us/azure/virtual-machines/troubleshooting/troubleshoot-vm-deployment-detached)
