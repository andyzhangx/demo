## Debug Azure disk attachment issue
There is some corner case in the before that k8s agent could not recognize the correct azure data disk.
### 1. Take `Windows Version 1709` as an example, it has attached two datadisks, below is the debugging info need to collect:
#### Run PowerShell command `Get-Disk` in admin mode
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

#### Show detaled info of one data disk
```
$disks = Get-Disk
$disks[3] | select *
```

```
DiskNumber            : 5
PartitionStyle        : MBR
ProvisioningType      : Thin
OperationalStatus     : Online
HealthStatus          : Healthy
BusType               : SAS
UniqueIdFormat        : Vendor Id
OfflineReason         :
ObjectId              : {1}\\77890K8S9010\root/Microsoft/Windows/Storage/Providers_v2\WSP_Disk.ObjectId="{aa117a5a-e3b6
                        -11e7-8f78-806e6f6e6963}:DI:\\?\scsi#disk&ven_msft&prod_virtual_disk#000001#{53f56307-b6bf-11d0
                        -94f2-00a0c91efb8b}"
PassThroughClass      :
PassThroughIds        :
PassThroughNamespace  :
PassThroughServer     :
UniqueId              : 4D534654202020209C8E3C77A846CD4AA6B8901C0E8E917D
AdapterSerialNumber   :
AllocatedSize         : 5368709120
BootFromDisk          : False
FirmwareVersion       : 1.0
FriendlyName          : Msft Virtual Disk
Guid                  :
IsBoot                : False
IsClustered           : False
IsHighlyAvailable     : False
IsOffline             : False
IsReadOnly            : False
IsScaleOut            : False
IsSystem              : False
LargestFreeExtent     : 0
Location              : Integrated : Adapter 3 : Port 0 : Target 0 : LUN 1
LogicalSectorSize     : 512
Manufacturer          : Msft
Model                 : Virtual Disk
Number                : 5
NumberOfPartitions    : 1
Path                  : \\?\scsi#disk&ven_msft&prod_virtual_disk#000001#{53f56307-b6bf-11d0-94f2-00a0c91efb8b}
PhysicalSectorSize    : 512
SerialNumber          :
Signature             : 2134170139
Size                  : 5368709120
PSComputerName        :
CimClass              : ROOT/Microsoft/Windows/Storage:MSFT_Disk
CimInstanceProperties : {ObjectId, PassThroughClass, PassThroughIds, PassThroughNamespace...}
CimSystemProperties   : Microsoft.Management.Infrastructure.CimSystemProperties
```

