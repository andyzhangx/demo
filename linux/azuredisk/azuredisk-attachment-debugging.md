## Debug Azure disk attachment issue
There is some corner case in the before that k8s agent could not recognize the correct azure data disk.
### 1. Take Ubuntu 16.04 as an example, it has attached two datadisks, below is the debugging info need to collect:
#### `/dev/disk/azure/` contains all one OS disk(`sda`) and one resource disk(`sdb`)
```
# sudo ls -lt /dev/disk/azure/
total 0
lrwxrwxrwx 1 root root 10 Oct 10 02:59 root-part1 -> ../../sda1
lrwxrwxrwx 1 root root 10 Oct 10 02:59 resource-part1 -> ../../sdb1
lrwxrwxrwx 1 root root  9 Oct 10 02:59 resource -> ../../sdb
lrwxrwxrwx 1 root root  9 Oct 10 02:59 root -> ../../sda
```

#### `/sys/bus/scsi/devices` conatins all scsi devices including OS disk, resource disk and data disks
```
# ls -lt /sys/bus/scsi/devices
total 0
lrwxrwxrwx 1 root root 0 Dec 13 06:53 2:0:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0000-8899-0000-000000000000/host2/target2:0:0/2:0:0:0
lrwxrwxrwx 1 root root 0 Dec 13 06:53 3:0:1:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0001-8899-0000-000000000000/host3/target3:0:1/3:0:1:0
lrwxrwxrwx 1 root root 0 Dec 13 06:53 5:0:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781b-1e82-4818-a1c3-63d806ec15bb/host5/target5:0:0/5:0:0:0
lrwxrwxrwx 1 root root 0 Dec 13 06:53 5:0:0:1 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781b-1e82-4818-a1c3-63d806ec15bb/host5/target5:0:0/5:0:0:1
lrwxrwxrwx 1 root root 0 Dec 13 06:53 host0 -> ../../../devices/pci0000:00/0000:00:07.1/ata1/host0
lrwxrwxrwx 1 root root 0 Dec 13 06:53 host1 -> ../../../devices/pci0000:00/0000:00:07.1/ata2/host1
lrwxrwxrwx 1 root root 0 Dec 13 06:53 host2 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0000-8899-0000-000000000000/host2
lrwxrwxrwx 1 root root 0 Dec 13 06:53 host3 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0001-8899-0000-000000000000/host3
lrwxrwxrwx 1 root root 0 Dec 13 06:53 host4 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781a-1e82-4818-a1c3-63d806ec15bb/host4
lrwxrwxrwx 1 root root 0 Dec 13 06:53 host5 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781b-1e82-4818-a1c3-63d806ec15bb/host5
lrwxrwxrwx 1 root root 0 Dec 13 06:53 target2:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0000-8899-0000-000000000000/host2/target2:0:0
lrwxrwxrwx 1 root root 0 Dec 13 06:53 target3:0:1 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0001-8899-0000-000000000000/host3/target3:0:1
lrwxrwxrwx 1 root root 0 Dec 13 06:53 target5:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781b-1e82-4818-a1c3-63d806ec15bb/host5/target5:0:0
```

In the above example, `2:0:0:0` is os disk(`sda`), `3:0:1:0` is resource disk(`sdb`), `5:0:0:0`,`5:0:0:1` are data disks, see below check:
```
# sudo cat /sys/bus/scsi/devices/5\:0\:0\:0/vendor
Msft
# sudo cat /sys/bus/scsi/devices/5\:0\:0\:0/model
Virtual Disk
# sudo ls -lt /sys/bus/scsi/devices/5\:0\:0\:0/block/
total 0
drwxr-xr-x 9 root root 0 Dec  8 11:21 sdc

# sudo ls -lt /sys/bus/scsi/devices/2\:0\:0\:0/block/
total 0
drwxr-xr-x 9 root root 0 Dec  8 11:21 sda

# sudo ls -lt /sys/bus/scsi/devices/3\:0\:1\:0/block/
total 0
drwxr-xr-x 9 root root 0 Dec  8 11:21 sdb
``` 

The last number of data disk scsi device(`5:0:0:0`) is the LUN number which is consistent with the LUN number in azure portal.

### 2. Now take coreos stable as an example, it has attached two datadisks, below is the debugging info need to collect:
```
# sudo ls -lt /dev/disk/azure/
total 0
drwxr-xr-x. 2 root root 60 Dec 13 06:46 scsi1
lrwxrwxrwx. 1 root root 10 Dec 13 04:42 root-part1 -> ../../sda1
lrwxrwxrwx. 1 root root 10 Dec 13 04:42 root-part7 -> ../../sda7
lrwxrwxrwx. 1 root root 10 Dec 13 04:42 root-part4 -> ../../sda4
lrwxrwxrwx. 1 root root 10 Dec 13 04:42 root-part2 -> ../../sda2
lrwxrwxrwx. 1 root root 10 Dec 13 04:42 root-part6 -> ../../sda6
lrwxrwxrwx. 1 root root 10 Dec 13 04:42 root-part3 -> ../../sda3
lrwxrwxrwx. 1 root root 10 Dec 13 04:42 root-part9 -> ../../sda9
lrwxrwxrwx. 1 root root  9 Dec 13 04:42 root -> ../../sda
lrwxrwxrwx. 1 root root 10 Dec 13 04:42 resource-part1 -> ../../sdb1
lrwxrwxrwx. 1 root root  9 Dec 13 04:42 resource -> ../../sdb

# ls -lt /sys/bus/scsi/devices
total 0
lrwxrwxrwx. 1 root root 0 Dec 13 06:59 5:0:0:1 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781b-1e82-4818-a1c3-63d806ec15bb/host5/target5:0:0/5:0:0:1
lrwxrwxrwx. 1 root root 0 Dec 13 06:50 target5:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781b-1e82-4818-a1c3-63d806ec15bb/host5/target5:0:0
lrwxrwxrwx. 1 root root 0 Dec 13 06:46 5:0:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781b-1e82-4818-a1c3-63d806ec15bb/host5/target5:0:0/5:0:0:0
lrwxrwxrwx. 1 root root 0 Dec 13 04:42 target0:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0000-8899-0000-000000000000/host0/target0:0:0
lrwxrwxrwx. 1 root root 0 Dec 13 04:42 target2:0:1 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0001-8899-0000-000000000000/host2/target2:0:1
lrwxrwxrwx. 1 root root 0 Dec 13 04:42 target3:0:0 -> ../../../devices/pci0000:00/0000:00:07.1/ata2/host3/target3:0:0
lrwxrwxrwx. 1 root root 0 Dec 13 04:41 2:0:1:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0001-8899-0000-000000000000/host2/target2:0:1/2:0:1:0
lrwxrwxrwx. 1 root root 0 Dec 13 04:41 3:0:0:0 -> ../../../devices/pci0000:00/0000:00:07.1/ata2/host3/target3:0:0/3:0:0:0
lrwxrwxrwx. 1 root root 0 Dec 13 04:41 host2 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0001-8899-0000-000000000000/host2
lrwxrwxrwx. 1 root root 0 Dec 13 04:41 host3 -> ../../../devices/pci0000:00/0000:00:07.1/ata2/host3
lrwxrwxrwx. 1 root root 0 Dec 13 04:41 host4 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781a-1e82-4818-a1c3-63d806ec15bb/host4
lrwxrwxrwx. 1 root root 0 Dec 13 04:41 host5 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/f8b3781b-1e82-4818-a1c3-63d806ec15bb/host5
lrwxrwxrwx. 1 root root 0 Dec 13 04:41 0:0:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0000-8899-0000-000000000000/host0/target0:0:0/0:0:0:0
lrwxrwxrwx. 1 root root 0 Dec 13 04:41 host0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBUS:01/00000000-0000-8899-0000-000000000000/host0
lrwxrwxrwx. 1 root root 0 Dec 13 04:41 host1 -> ../../../devices/pci0000:00/0000:00:07.1/ata1/host1

# sudo cat /sys/bus/scsi/devices/5\:0\:0\:0/vendor
Msft

# sudo cat /sys/bus/scsi/devices/5\:0\:0\:0/model
Virtual Disk

# sudo ls -lt /sys/bus/scsi/devices/5\:0\:0\:0/block/
total 0
drwxr-xr-x. 8 root root 0 Dec 13 06:46 sdc
```

In the above example, `0:0:0:0` is os disk(`sda`), `2:0:1:0` is resource disk(`sdb`), `5:0:0:0`,`5:0:0:1` are data disks, `3:0:0:0` is CDROM device.

### 3. Now take CentOS 6.8 as an example, it has attached one datadisks, below is the debugging info need to collect:
```
$ ls -lt /sys/bus/scsi/devices
total 0
lrwxrwxrwx 1 root root 0 Dec 13 07:11 0:0:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_2/host0/target0:0:0/0:0:0:0
lrwxrwxrwx 1 root root 0 Dec 13 07:11 1:0:1:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_3/host1/target1:0:1/1:0:1:0
lrwxrwxrwx 1 root root 0 Dec 13 07:11 3:0:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_17/host3/target3:0:0/3:0:0:0
lrwxrwxrwx 1 root root 0 Dec 13 07:11 5:0:0:0 -> ../../../devices/pci0000:00/0000:00:07.1/host5/target5:0:0/5:0:0:0
lrwxrwxrwx 1 root root 0 Dec 13 07:11 host0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_2/host0
lrwxrwxrwx 1 root root 0 Dec 13 07:11 host1 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_3/host1
lrwxrwxrwx 1 root root 0 Dec 13 07:11 host2 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_16/host2
lrwxrwxrwx 1 root root 0 Dec 13 07:11 host3 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_17/host3
lrwxrwxrwx 1 root root 0 Dec 13 07:11 host4 -> ../../../devices/pci0000:00/0000:00:07.1/host4
lrwxrwxrwx 1 root root 0 Dec 13 07:11 host5 -> ../../../devices/pci0000:00/0000:00:07.1/host5
lrwxrwxrwx 1 root root 0 Dec 13 07:11 target0:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_2/host0/target0:0:0
lrwxrwxrwx 1 root root 0 Dec 13 07:11 target1:0:1 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_3/host1/target1:0:1
lrwxrwxrwx 1 root root 0 Dec 13 07:11 target3:0:0 -> ../../../devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A03:00/device:07/VMBus:00/vmbus_17/host3/target3:0:0
lrwxrwxrwx 1 root root 0 Dec 13 07:11 target5:0:0 -> ../../../devices/pci0000:00/0000:00:07.1/host5/target5:0:0

# sudo cat /sys/bus/scsi/devices/3\:0\:0\:0/vendor
Msft
# sudo cat /sys/bus/scsi/devices/3\:0\:0\:0/model
Virtual Disk
# sudo ls -lt /sys/bus/scsi/devices/3\:0\:0\:0/block/
total 0
drwxr-xr-x. 8 root root 0 Dec 13 06:46 sdc
```

In the above example, `0:0:0:0` is os disk(`sda`), `1:0:1:0` is resource disk(`sdb`), `3:0:0:0` is data disk, `5:0:0:0` is CDROM device.
