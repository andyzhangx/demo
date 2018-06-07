## Azure disk attach/detach stress test with StatefulSet
#### Prerequisite
 - [create an azure disk storage class if hdd does not exist](https://github.com/andyzhangx/demo/tree/master/linux/azuredisk#1-create-an-azure-disk-storage-class-if-hdd-does-not-exist)

### 1. Let k8s schedule all pods on one node by `kubectl cordon NODE-NAME`

### 2. Set up a few StatefulSet with azure disk mount on a node#1
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/statefulset-azuredisk1.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/statefulset-azuredisk2.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/statefulset-azuredisk3.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/statefulset-azuredisk4.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/statefulset-azuredisk5.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/statefulset-azuredisk6.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/statefulset-azuredisk7.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/statefulset-azuredisk8.yaml
```

### 3. Let k8s schedule all pods on node#2
```
kubectl cordon node#2
kubectl drain node#1 --ignore-daemonsets --delete-local-data
```

### 4. Watch the pod scheduling process
```
watch kubectl get po -o wide
```

#### clean up
```
kubectl delete sts statefulset-azuredisk1
kubectl delete sts statefulset-azuredisk2
kubectl delete sts statefulset-azuredisk3
kubectl delete sts statefulset-azuredisk4
kubectl delete sts statefulset-azuredisk5
kubectl delete sts statefulset-azuredisk6
kubectl delete sts statefulset-azuredisk7
kubectl delete sts statefulset-azuredisk8

kubectl delete pvc persistent-storage-statefulset-azuredisk1-0
kubectl delete pvc persistent-storage-statefulset-azuredisk2-0
kubectl delete pvc persistent-storage-statefulset-azuredisk3-0
kubectl delete pvc persistent-storage-statefulset-azuredisk4-0
kubectl delete pvc persistent-storage-statefulset-azuredisk5-0
kubectl delete pvc persistent-storage-statefulset-azuredisk6-0
kubectl delete pvc persistent-storage-statefulset-azuredisk7-0
kubectl delete pvc persistent-storage-statefulset-azuredisk8-0
```

#### expected behavior on agent node
```
azureuser@aks-nodepool1-26705064-2:~$ sudo tree /dev/disk/azure
...
â””â”€â”€ scsi1
    â”œâ”€â”€ lun0 -> ../../../sdc
    â”œâ”€â”€ lun1 -> ../../../sdd
    â”œâ”€â”€ lun2 -> ../../../sde
    â”œâ”€â”€ lun3 -> ../../../sdf
    â”œâ”€â”€ lun4 -> ../../../sdg
    â”œâ”€â”€ lun5 -> ../../../sdh
    â”œâ”€â”€ lun6 -> ../../../sdi
    â””â”€â”€ lun7 -> ../../../sdj
    
azureuser@aks-nodepool1-26705064-2:~$ sudo df -aTH | grep dev
udev           devtmpfs     17G     0   17G   0% /dev
devpts         devpts         0     0     0    - /dev/pts
/dev/sda1      ext4         32G  3.7G   28G  12% /
tmpfs          tmpfs        17G     0   17G   0% /dev/shm
cgroup         cgroup         0     0     0    - /sys/fs/cgroup/devices
mqueue         mqueue         0     0     0    - /dev/mqueue
hugetlbfs      hugetlbfs      0     0     0    - /dev/hugepages
/dev/sdb1      ext4         68G   55M   64G   1% /mnt
/dev/sda1      ext4         32G  3.7G   28G  12% /var/lib/docker/overlay2
/dev/sda1      ext4         32G  3.7G   28G  12% /var/lib/kubelet
/dev/sdc       ext4        1.1G  1.4M  952M   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3727541750
/dev/sdc       ext4        1.1G  1.4M  952M   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3727541750
/dev/sdc       ext4        1.1G  1.4M  952M   1% /var/lib/kubelet/pods/0decc7a9-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0dec1804-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdc       ext4        1.1G  1.4M  952M   1% /var/lib/kubelet/pods/0decc7a9-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0dec1804-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdd       ext4        2.1G  3.2M  2.0G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1240331186
/dev/sdd       ext4        2.1G  3.2M  2.0G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1240331186
/dev/sdd       ext4        2.1G  3.2M  2.0G   1% /var/lib/kubelet/pods/0e5b1526-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0e5a8cfb-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdd       ext4        2.1G  3.2M  2.0G   1% /var/lib/kubelet/pods/0e5b1526-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0e5a8cfb-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sde       ext4        3.2G  4.8M  3.0G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m722087109
/dev/sde       ext4        3.2G  4.8M  3.0G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m722087109
/dev/sde       ext4        3.2G  4.8M  3.0G   1% /var/lib/kubelet/pods/0edb8e7b-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0edafb9f-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sde       ext4        3.2G  4.8M  3.0G   1% /var/lib/kubelet/pods/0edb8e7b-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0edafb9f-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdf       ext4        4.1G  8.4M  3.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3156456093
/dev/sdf       ext4        4.1G  8.4M  3.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m3156456093
/dev/sdf       ext4        4.1G  8.4M  3.9G   1% /var/lib/kubelet/pods/0f3c1825-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0f3b5ef9-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdf       ext4        4.1G  8.4M  3.9G   1% /var/lib/kubelet/pods/0f3c1825-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0f3b5ef9-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdg       ext4        5.2G   11M  4.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1551146641
/dev/sdg       ext4        5.2G   11M  4.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1551146641
/dev/sdg       ext4        5.2G   11M  4.9G   1% /var/lib/kubelet/pods/0f9fd9cd-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0f9e9ad3-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdg       ext4        5.2G   11M  4.9G   1% /var/lib/kubelet/pods/0f9fd9cd-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0f9e9ad3-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdh       ext4        6.3G   13M  5.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1598626075
/dev/sdh       ext4        6.3G   13M  5.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1598626075
/dev/sdh       ext4        6.3G   13M  5.9G   1% /var/lib/kubelet/pods/10006a43-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0ffe5581-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdh       ext4        6.3G   13M  5.9G   1% /var/lib/kubelet/pods/10006a43-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-0ffe5581-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdi       ext4        7.3G   17M  6.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1746791072
/dev/sdi       ext4        7.3G   17M  6.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m1746791072
/dev/sdi       ext4        7.3G   17M  6.9G   1% /var/lib/kubelet/pods/1068fd0f-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-106879b9-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdi       ext4        7.3G   17M  6.9G   1% /var/lib/kubelet/pods/1068fd0f-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-106879b9-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdj       ext4        8.4G   19M  7.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m4088980381
/dev/sdj       ext4        8.4G   19M  7.9G   1% /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m4088980381
/dev/sdj       ext4        8.4G   19M  7.9G   1% /var/lib/kubelet/pods/116d39c1-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-116cb513-6a25-11e8-ad70-0a58ac1f0c4a
/dev/sdj       ext4        8.4G   19M  7.9G   1% /var/lib/kubelet/pods/116d39c1-6a25-11e8-ad70-0a58ac1f0c4a/volumes/kubernetes.io~azure-disk/pvc-116cb513-6a25-11e8-ad70-0a58ac1f0c4a
```
