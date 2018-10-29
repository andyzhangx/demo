# Azure disk new features and restrictions
## Azure disk new features
 - Azure disk size grow

available from `v1.11.0`, details: [Add azuredisk PV size grow feature](https://github.com/kubernetes/kubernetes/pull/64386)

## Azure disk restrictions
### 1. cannot attach an azure disk from another subscription
Error would be like following:
```
Events:
  Type     Reason              Age                  From                               Message
  ----     ------              ----                 ----                               -------
  Warning  FailedMount         3m (x1912 over 3d)   kubelet, aks-nodepool1-20449952-1  Unable to mount volumes for pod "nginx-azuredisk3_default(116d527e-c84c-11e8-af0a-d2df8f315e11)": timeout expired waiting for volumes to attach or mount for pod "default"/"nginx-azuredisk3". list of unmounted volumes=[azure]. list of unattached volumes=[azure default-token-dw48n]
  Warning  FailedAttachVolume  28s (x2129 over 3d)  attachdetach-controller            AttachVolume.Attach failed for volume "azure" : Attach volume "andytest" to instance "/subscriptions/b9d2281e-dcd5-4dfd-9a97-xxx/resourceGroups/MC_andy-aks1112_andy-aks1112_westus2/providers/Microsoft.Compute/virtualMachines/aks-nodepool1-20449952-1" failed with compute.VirtualMachinesClient#CreateOrUpdate: Failure sending request: StatusCode=400 -- Original Error: Code="InvalidParameter" Message="Subscription b9d2281e-dcd5-4dfd-9a97-xxx of the request must match the subscription 4be8920b-2978-43d7-ab14-xxx contained in the managed disk id." Target="dataDisk.managedDisk.id"
```
