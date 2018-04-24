# hostpath CSI driver on Windows example 
# CSI on Windows does not work due to [Symlink for ca.crt & token files are broken on windows containers](https://github.com/kubernetes/kubernetes/issues/52419), details could be found in [Enable CSI hostpath example on windows](https://github.com/kubernetes-csi/drivers/issues/79)

## Install hostpath CSI driver on a kubernetes cluster 
 - Set up [External Attacher](https://github.com/kubernetes-csi/external-attacher), [External Provisioner](https://github.com/kubernetes-csi/external-provisioner), [Driver Registrar](https://github.com/kubernetes-csi/driver-registrar), [hostpath driver](https://github.com/kubernetes-csi/drivers/tree/master/pkg/hostpath) and ClusterRole permissions 
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/windows/csi/hostpath/deployment/csi-hostpath-driver-windows.yaml
```

 - watch the status of all component pods until its `Status` changed from `Pending` to `Running`
```
azureuser@k8s-master-15282161-0:~$ kubectl get po -o wide --namespace=hostpath
NAME                         READY     STATUS             RESTARTS   AGE       IP             NODE
csi-hostpath-attacher-0      1/1       Running            0          5d        10.240.0.10    k8s-master-15282161-0
csi-hostpath-linux-ftzhr     2/2       Running            0          5d        10.255.255.5   k8s-master-15282161-0
csi-hostpath-provisioner-0   1/1       Running            0          5d        10.240.0.19    k8s-master-15282161-0
csi-hostpath-windows-lpzqb   1/2       Running   	        0          20h       10.240.0.84    15282k8s9010
```

## Basic Usage
### 1. Create a hostpath CSI storage class
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/windows/csi/hostpath/storageclass-csi-hostpath.yaml
```

### 2. Create a hostpath CSI PVC
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/windows/csi/hostpath/pvc-csi-hostpath.yaml
```
make sure pvc is created successfully
```
watch kubectl describe pvc pvc-csi-hostpath
```

### 3. create a pod with hostpath CSI PVC
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/windows/csi/hostpath/aspnet-pod-csi-hostpath.yaml
```

### 4. enter the pod container to do validation
```
azureuser@k8s-master-87187153-0:~$ kubectl exec -it  aspnet-csi-hostpath cmd

```

#### Note
 - CSI hostpath driver would mkdir under `c:/var/lib/kubelet/pods/5a6d98a3-1c57-11e8-a48d-000d3afdbef1/volumes/kubernetes.io~csi/kubernetes-dynamic-pvc-5a7519c9-1c57-11e8-99dd-bab516dca496/mount`, mount to `/data` dir in the above example
 - clean up all clusterroles & clusterrolebindings:
```
kubectl delete namespace hostpath
kubectl delete clusterrole hostpath:external-provisioner-runner
kubectl delete clusterrole hostpath:external-attacher-runner
kubectl delete clusterrole csi-hostpath
kubectl delete clusterrolebinding csi-hostpath-provisioner-role
kubectl delete clusterrolebinding csi-hostpath-attacher-role
kubectl delete clusterrolebinding csi-hostpath
```

#### Links
[Introducing Container Storage Interface (CSI) Alpha for Kubernetes](http://blog.kubernetes.io/2018/01/introducing-container-storage-interface.html)

[Kubernetes CSI Documentation](https://kubernetes-csi.github.io/docs/Home.html)

[CSI Volume Plugins in Kubernetes Design Doc](https://github.com/kubernetes/community/blob/master/contributors/design-proposals/storage/container-storage-interface.md)
