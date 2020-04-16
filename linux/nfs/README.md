# Use NFS Server Provisioner on AKS
[NFS Server Provisioner](https://github.com/kubernetes-incubator/external-storage/tree/master/nfs) is an out-of-tree dynamic provisioner for Kubernetes. You can use it to quickly & easily deploy shared storage that works almost anywhere. This doc shows how to set NFS Server Provisioner on AKS using [NFS Server Provisioner helm chart](https://github.com/helm/charts/tree/master/stable/nfs-server-provisioner)
 
## 1. Install nfs-server-provisioner helm chart
 - following example would provision 100GB storage(one data disk) on an agent node, serving as a NFSv3 server
```console
helm repo add stable https://kubernetes-charts.storage.googleapis.com/
helm install stable/nfs-server-provisioner --generate-name --set=persistence.storageClass=default,persistence.enabled=true,persistence.size=100Gi
```

## 2. After installation successfully, a new storage class `nfs` created
```console
# kubectl describe sc nfs
Name:                  nfs
IsDefaultClass:        No
Annotations:           <none>
Provisioner:           cluster.local/nfs-server-provisioner-1587007822
Parameters:            <none>
AllowVolumeExpansion:  True
MountOptions:
  vers=3
ReclaimPolicy:      Delete
VolumeBindingMode:  Immediate
Events:             <none>
```

## 3. create a statefulset with NFS volume mount
```console
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/nfs/statefulset-nfs.yaml
```

## 4. enter the pod container to do validation
```console
# kubectl exec -it statefulset-nfs-0 bash
root@statefulset-nfs-0:/# df -h
Filesystem                                                    Size  Used Avail Use% Mounted on
overlay                                                        97G   11G   87G  11% /
tmpfs                                                          64M     0   64M   0% /dev
tmpfs                                                         3.4G     0  3.4G   0% /sys/fs/cgroup
10.0.212.68:/export/pvc-c08bb76e-6d45-452a-8333-53b13bd01000   99G   60M   99G   1% /mnt/nfs
/dev/sda1                                                      97G   11G   87G  11% /etc/hosts
...
```
