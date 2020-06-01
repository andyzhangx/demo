## Debug Azure disk attach/detach/mount/read/write issue
Below are the steps about how to debug azure disk issues on Kubernetes.

 - Note: 
   - Step#1, #2 are needed if there is disk attach/detach issue 
   - Step#3 is needed if there is disk mount/read/write issue

### 1. Get disk info by azure cli
```console
az disk show -g <resource-group-name> -n <disk-name>
```

### 2. Get `volumesAttached` info by `kubectl get no NODE-NAME -o yaml`, e.g.
```console
# kubectl get no -o yaml | grep volumesAttached -A 10
volumesAttached:
  - devicePath: "0"
    name: kubernetes.io/azure-disk//subscriptions/.../resourceGroups/MC_nozzle-central_nzcentral_centralus/providers/Microsoft.Compute/disks/kubernetes-dynamic-pvc-e684185c-b3ea-11e8-bf5c-0a58ac1f0f2f
  - devicePath: "1"
    name: kubernetes.io/azure-disk//subscriptions/.../resourceGroups/MC_nozzle-central_nzcentral_centralus/providers/Microsoft.Compute/disks/kubernetes-dynamic-pvc-96f3060b-b3ec-11e8-bf5c-0a58ac1f0f2f
  - devicePath: "2"
    name: kubernetes.io/azure-disk//subscriptions/.../resourceGroups/MC_nozzle-central_nzcentral_centralus/providers/Microsoft.Compute/disks/kubernetes-dynamic-pvc-936d310f-0357-11e9-be1f-0a58ac1f147d    
```

### 3. Log on agent node and check device info on Windows
 - Run PowerShell command `Get-Disk` in admin mode
```
PS C:\k> Get-Disk | select number, location
number location
------ --------
     0 PCI Slot 0 : Adapter 0 : Channel 0 : Device 0
     1 PCI Slot 1 : Adapter 0 : Channel 1 : Device 0
     2 Integrated : Adapter 3 : Port 0 : Target 0 : LUN 0
     5 Integrated : Adapter 3 : Port 0 : Target 0 : LUN 1
     3 C:\ProgramData\docker\windowsfilter\e99aca58861e7a7cc0cea8e214391d74065b4f66b31a4b5a47989266cb41923b\sandbox....
     6 C:\ProgramData\docker\windowsfilter\d92cb8c7d4bd2e076b112f359a91ca1f98b5b85eb2d82d2c1e7a1a3a75bac80a\sandbox....
     4 C:\ProgramData\docker\windowsfilter\001fcb9cd5e73161a51230d286de1d20cccec54eb9086607e8b17d1c40469378\sandbox....
     7 C:\ProgramData\docker\windowsfilter\b806ef220ad6c82e4f3027ac0348cd2f935be07c1d030f58e30616c1dc805a29\sandbox....
```
In above example, there are two data disks which contain `LUN`, OS disk is `PCI Slot 0 : Adapter 0 : Channel 0 : Device 0`, resource disk is `PCI Slot 1 : Adapter 0 : Channel 1 : Device 0`

 - Show detaled info of one data disk
```
Get-Disk -Number 2 | Format-list
```

 - All disk mounts are under `c:\var\lib\kubelet\plugins\kubernetes.io\azure-disk\mounts\` on Windows
