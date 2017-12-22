## Debug Azure disk attachment issue
There is some corner case in the before that k8s agent could not recognize the correct azure data disk.
### 1. Take Ubuntu 16.04 as an example, it has attached 3 data disks, below is the debugging info need to collect:
#### `/dev/disk/azure/` contains one OS disk(`sda`), one resource disk(`sdb`), 3 data disks(`sdc`, `sdd`, `sde`)
```
sudo apt install tree -y
tree /dev/disk/azure
/dev/disk/azure
├── resource -> ../../sdb
├── resource-part1 -> ../../sdb1
├── root -> ../../sda
├── root-part1 -> ../../sda1
└── scsi1
    ├── lun0 -> ../../../sdc
    ├── lun1 -> ../../../sdd
    └── lun2 -> ../../../sde
    
sudo apt install tree lsscsi -y
$ sudo lsscsi
[0:0:0:0]    disk    Msft     Virtual Disk     1.0   /dev/sda
[1:0:1:0]    disk    Msft     Virtual Disk     1.0   /dev/sdb
[3:0:0:0]    disk    Msft     Virtual Disk     1.0   /dev/sdc
[3:0:0:1]    disk    Msft     Virtual Disk     1.0   /dev/sdd
[3:0:0:2]    disk    Msft     Virtual Disk     1.0   /dev/sde
```

#### Run `sudo df -aTH` to get all mounting info
```
$ sudo df -aTH
Filesystem     Type        Size  Used Avail Use% Mounted on
...
/dev/sdd       ext4         53G  867M   50G   2% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/b3022915953
/dev/sdd       ext4         53G  867M   50G   2% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/b3022915953
/dev/sdd       ext4         53G  867M   50G   2% /var/lib/kubelet/pods/1f430fc0-e668-11e7-ba11-0017fa009264/volumes/kubernetes.io~azure-disk/pvc-1f3d090f-e668-11e7-ba11-0017fa009264
/dev/sdd       ext4         53G  867M   50G   2% /var/lib/kubelet/pods/1f430fc0-e668-11e7-ba11-0017fa009264/volumes/kubernetes.io~azure-disk/pvc-1f3d090f-e668-11e7-ba11-0017fa009264
...
/dev/sde       ext4         53G  885M   50G   2% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/b93031267
/dev/sde       ext4         53G  885M   50G   2% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/b93031267
/dev/sde       ext4         53G  885M   50G   2% /var/lib/kubelet/pods/24be56e5-e668-11e7-ba11-0017fa009264/volumes/kubernetes.io~azure-disk/pvc-24ba0511-e668-11e7-ba11-0017fa009264
/dev/sde       ext4         53G  885M   50G   2% /var/lib/kubelet/pods/24be56e5-e668-11e7-ba11-0017fa009264/volumes/kubernetes.io~azure-disk/pvc-24ba0511-e668-11e7-ba11-0017fa009264
shm            tmpfs        68M     0   68M   0% /var/lib/docker/containers/b151fc7937f431170b354b623340a2061731079755d370618d90ffa4932b091d/shm
nsfs           nsfs           0     0     0    - /run/docker/netns/740e7ce74c3f
tmpfs          tmpfs       7.4G   13k  7.4G   1% /var/lib/kubelet/pods/8bfbf06f-e6bb-11e7-ba11-0017fa009264/volumes/kubernetes.io~secret/default-token-k1j4t
tmpfs          tmpfs       7.4G   13k  7.4G   1% /var/lib/kubelet/pods/8bfbf06f-e6bb-11e7-ba11-0017fa009264/volumes/kubernetes.io~secret/default-token-k1j4t
/dev/sdc       ext4         53G  908M   50G   2% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/b576880976
/dev/sdc       ext4         53G  908M   50G   2% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/b576880976
/dev/sdc       ext4         53G  908M   50G   2% /var/lib/kubelet/pods/8bfbf06f-e6bb-11e7-ba11-0017fa009264/volumes/kubernetes.io~azure-disk/pvc-8b5934ff-e665-11e7-ba11-0017fa009264
/dev/sdc       ext4         53G  908M   50G   2% /var/lib/kubelet/pods/8bfbf06f-e6bb-11e7-ba11-0017fa009264/volumes/kubernetes.io~azure-disk/pvc-8b5934ff-e665-11e7-ba11-0017fa009264
shm            tmpfs        68M     0   68M   0% /var/lib/docker/containers/dadc0d8e2883135268cd2e2f894efe68b1be428bbba0fb50091858c830f9bd30/shm
nsfs           nsfs           0     0     0    - /run/docker/netns/628465d8db02
tmpfs          tmpfs       1.5G     0  1.5G   0% /run/user/1000
```

#### Links
[Troubleshoot Linux VM device name change](https://docs.microsoft.com/en-us/azure/virtual-machines/linux/troubleshoot-device-names-problems)
