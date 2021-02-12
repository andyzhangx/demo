# azure network known issues
### 1. network interface failed
**Workaround**:
```
az network nic update -g RG-NAME -n NIC-NAME
```

### 2. azure cni `Failed to allocate address`
**Issue details**:
There are about 31 internal network addresses allocated for each node, when pod keeps failing and restarts multiple times in a short period, the addresses will be exhausted in the end.

**Error logs**:
```
Events:
  Type     Reason                  Age                 From                               Message
  ----     ------                  ----                ----                               -------
  Normal   Scheduled               45m                 default-scheduler                  Successfully assigned deployment-azuredisk6-56d8dcb746-487td to k8s-agentpool-66825246-0
  Warning  FailedAttachVolume      45m                 attachdetach-controller            Multi-Attach error for volume "pvc-0db5d49f-3f1c-11e8-ab6b-000d3af9f967" Volume is already exclusively attached to one node and can't be attached to another
  Normal   SuccessfulMountVolume   45m                 kubelet, k8s-agentpool-66825246-0  MountVolume.SetUp succeeded for volume "default-token-cxk4v"
  Normal   SuccessfulAttachVolume  36m                 attachdetach-controller            AttachVolume.Attach succeeded for volume "pvc-0db5d49f-3f1c-11e8-ab6b-000d3af9f967"
  Warning  FailedMount             12m (x16 over 43m)  kubelet, k8s-agentpool-66825246-0  MountVolume.MountDevice failed for volume "pvc-0db5d49f-3f1c-11e8-ab6b-000d3af9f967" : azureDisk - mountDevice:FormatAndMount failed with exit status 1
  Warning  FailedMount             9m (x16 over 43m)   kubelet, k8s-agentpool-66825246-0  Unable to mount volumes for pod "deployment-azuredisk6-56d8dcb746-487td_default(6b243960-411e-11e8-ab6b-000d3af9f967)": timeout expired waiting for volumes to attach or mount for pod "default"/"deployment-azuredisk6-56d8dcb746-487td". list of unmounted volumes=[azuredisk]. list of unattached volumes=[azuredisk default-token-cxk4v]
  Normal   SandboxChanged          5m (x74 over 8m)    kubelet, k8s-agentpool-66825246-0  Pod sandbox changed, it will be killed and re-created.
  Warning  FailedCreatePodSandBox  21s (x204 over 8m)  kubelet, k8s-agentpool-66825246-0  Failed create pod sandbox: rpc error: code = Unknown desc = NetworkPlugin cni failed to set up pod "deployment-azuredisk6-56d8dcb746-487td_default" network: Failed to allocate address: Failed to delegate: Failed to allocate address: No available addresses
```

**Mitigation**:
 - Append `--minimum-container-ttl-duration=5s --maximum-dead-containers-per-container=1  --maximum-dead-containers=60` into kubelet parameters(`KUBELET_CONFIG`):
```
sudo vi /etc/default/kubelet
#edit
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```
 - Delete failing deployments first, and redeploy pods

### 3. failed to delete service due to LinkedAuthorizationFailed
**Error logs**:
```
  Code="LinkedAuthorizationFailed" Message="The client
  '6244dd6c-640f-4a87-9781-ef828ac2e4a6' with object id
  '6244dd6c-640f-4a87-9781-ef828ac2e4a6' has permission to perform action
  'Microsoft.Network/loadBalancers/write' on scope
  '/subscriptions/xxx/resourceGroups/mc_rg_eu2_c001_aks_dev_01_akseu2c010aksdev01_eastus2/providers/Microsoft.Network/loadBalancers/kubernetes';
  however, it does not have permission to perform action
  'Microsoft.Network/publicIPAddresses/join/action' on the linked scope(s)
  '/subscriptions/xxx/resourceGroups/RG_EU2_C011_INTE_DEV_01/providers/Microsoft.Network/publicIPAddresses/ipconfig2borrar'
  or the linked scope(s) are invalid."
```

**Mitigation**:
 - get `appDisplayName` of cluster identity using object id
```console
az ad sp show --id 6244dd6c-640f-4a87-9781-ef828ac2e4a6
```

 - assign permission to cluster identity
   - go to page `/subscriptions/xxx/resourceGroups/RG_EU2_C011_INTE_DEV_01/providers/Microsoft.Network/publicIPAddresses/ipconfig2borrar` on Azure portal
   - under `Access Control`, click `Role Assignment`, add `Contributor` role to cluster identity using `appDisplayName`
