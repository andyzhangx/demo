# NVME disk controller support

```console
# wget -O /etc/udev/rules.d/80-azure-nvme.rules https://raw.githubusercontent.com/Azure/azure-nvme-utils/main/udev/80-azure-nvme.rules.in
wget -O /etc/udev/rules.d/80-azure-nvme.rules https://raw.githubusercontent.com/Azure/SAP-on-Azure-Scripts-and-Utilities/main/NVMe-Preflight-Check/88-azure-nvme-data-disk.rules
cd /tmp/
wget https://download.copr.fedorainfracloud.org/results/cjp256/azure-nvme-utils/opensuse-leap-15.5-x86_64/07402358-azure-nvme-utils/azure-nvme-utils-0.1.3-1.x86_64.rpm
rpm -i azure-nvme-utils-0.1.3-1.x86_64.rpm
udevadm control --reload-rules && udevadm trigger
```

 - nvme disk
```
# ls -lt /dev/disk/azure/*
lrwxrwxrwx 1 root root 15 Jul 25 07:20 /dev/disk/azure/root-part1 -> ../../nvme0n1p1
lrwxrwxrwx 1 root root 15 Jul 25 07:20 /dev/disk/azure/root-part2 -> ../../nvme0n1p2
lrwxrwxrwx 1 root root 15 Jul 25 07:20 /dev/disk/azure/root-part3 -> ../../nvme0n1p3
lrwxrwxrwx 1 root root 15 Jul 25 07:20 /dev/disk/azure/root-part4 -> ../../nvme0n1p4
lrwxrwxrwx 1 root root 13 Jul 25 07:20 /dev/disk/azure/root -> ../../nvme0n1

/dev/disk/azure/data:
total 0
drwxr-xr-x 2 root root 80 Jul 25 07:20 by-lun
# ls -lt /dev/disk/azure/data/*
total 0
lrwxrwxrwx 1 root root 19 Jul 25 07:20 0 -> ../../../../nvme0n2
lrwxrwxrwx 1 root root 19 Jul 25 07:20 1 -> ../../../../nvme0n3
```

 - scsi disk
```
# ls -lt /dev/disk/azure/scsi1
total 0
lrwxrwxrwx 1 root root 12 Jul 25 23:37 lun1 -> ../../../sdd
lrwxrwxrwx 1 root root 12 Jul 24 15:51 lun5 -> ../../../sdh
lrwxrwxrwx 1 root root 12 Jul 24 14:38 lun2 -> ../../../sdf
lrwxrwxrwx 1 root root 12 Jul 24 14:38 lun0 -> ../../../sdc
```
