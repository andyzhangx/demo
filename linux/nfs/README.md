## 1. create a nfs persistent volume (pv)
 - download `pv-nfs.yaml`, change `nfs` config and then create a nfs persistent volume (pv)
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pv-nfs.yaml
vi pv-nfs.yaml
kubectl create -f pv-nfs.yaml
```

make sure pv is in `Available` status
```
kubectl describe pv pv-nfs
```

## 2. create a nfs persistent volume claim (pvc)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-nfs.yaml
```

make sure pvc is in `Bound` status
```
kubectl describe pvc pvc-nfs
```

## 3. create a pod with nfs mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/nfs/nginx-nfs.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-nfs

## 4. enter the pod container to do validation
kubectl exec -it nginx-nfs -- bash

```
root@nginx-nfs:/mnt/azure# df -h
Filesystem                            Size  Used Avail Use% Mounted on
overlay                                30G  3.9G   26G  14% /
tmpfs                                 6.9G     0  6.9G   0% /dev
tmpfs                                 6.9G     0  6.9G   0% /sys/fs/cgroup
nfstest.eastus2.cloudapp.azure.com:/   30G  1.3G   28G   5% /mnt/azure
/dev/sda1                              30G  3.9G   26G  14% /etc/hosts
shm                                    64M     0   64M   0% /dev/shm
tmpfs                                 6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount
```

#### Note
 - Set up a NFS server on an Azure Ubuntu VM (refer to [SettingUpNFSHowTo](https://help.ubuntu.com/community/SettingUpNFSHowTo))
```
apt-get update
apt-get install nfs-kernel-server -y

mkdir /home/azureuser/nfs
chmod 0777 /home/azureuser/nfs

vi /etc/exports
/home/azureuser/nfs        *(rw,sync,fsid=0,crossmnt,no_subtree_check)

service nfs-kernel-server restart
#open port 2049 in VM  Inbound Rules on Azure portal

#Set up a NFS client
sudo apt-get install nfs-common  -y
sudo mkdir /nfs
sudo mount -t nfs -o proto=tcp,port=2049 SERVER-NAME.eastus2.cloudapp.azure.com:/ /nfs

```
