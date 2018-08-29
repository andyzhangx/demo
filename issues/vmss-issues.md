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
