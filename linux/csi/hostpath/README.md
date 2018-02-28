## hostpath csi driver example

### 1. Set up [External Attacher](https://github.com/kubernetes-csi/external-attacher), [External Provisioner](https://github.com/kubernetes-csi/external-provisioner), [Driver Registrar](https://github.com/kubernetes-csi/driver-registrar), and ClusterRole permissions 
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/csi/hostpath/csi-hostpath.yaml
```

 - watch the status of all component pods until its `Status` changed from `Pending` to `Running`
```
#kubectl get po
NAME                    READY     STATUS    RESTARTS   AGE
csi-hostpath-driver-0   4/4       Running   0          22m
web-server              1/1       Running   0          21m
```
### 2. create the pod based on hostpath csi driver
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/csi/hostpath/nginx-csi-hostpath.yaml
```

### 3. enter the pod container to do validation
```
azureuser@k8s-master-87187153-0:~$ kubectl exec -it  nginx-csi-hostpath -- bash
root@nginx-csi-hostpath:/# df -h
Filesystem      Size  Used Avail Use% Mounted on
overlay          30G  8.9G   21G  31% /
tmpfs           3.4G     0  3.4G   0% /dev
tmpfs           3.4G     0  3.4G   0% /sys/fs/cgroup
overlay          30G  8.9G   21G  31% /data
/dev/sda1        30G  8.9G   21G  31% /etc/hosts
shm              64M     0   64M   0% /dev/shm
tmpfs           3.4G   12K  3.4G   1% /run/secrets/kubernetes.io/serviceaccount
```

#### Note
 - CSI hostpath driver would mkdir under `/var/lib/kubelet/pods/5a6d98a3-1c57-11e8-a48d-000d3afdbef1/volumes/kubernetes.io~csi/kubernetes-dynamic-pvc-5a7519c9-1c57-11e8-99dd-bab516dca496/mount`, mount to `/data` dir in the above example

#### Links
[Kubernetes CSI Documentation](https://kubernetes-csi.github.io/docs/Home.html)
