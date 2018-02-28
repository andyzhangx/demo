## hostpath csi driver example

### 1. Set up [External Attacher](https://github.com/kubernetes-csi/external-attacher), [External Provisioner](https://github.com/kubernetes-csi/external-provisioner), [Driver Registrar](https://github.com/kubernetes-csi/driver-registrar), and ClusterRole permissions 
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/csi/hostpath/hostPath.yaml
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
kubectl create -f https://raw.githubusercontent.com/lpabon/csi-workspace/master/demo/pod.yaml
```

### 3. enter the pod container to do validation
```kubectl exec -it nginx -- bash```

#### Links
[https://kubernetes-csi.github.io/docs/Home.html](https://kubernetes-csi.github.io/docs/Home.html)
