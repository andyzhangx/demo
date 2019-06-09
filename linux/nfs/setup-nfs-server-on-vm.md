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
