## CSI debugging
### Get CSI driver logs
Take dysk CSI driver as an example:
#### 1. Get `csi-dysk-provisioner` logs
```
kubectl logs csi-dysk-provisioner-0 --namespace=dysk > csi-dysk-provisioner-0.log
```
#### 2. Get `csi-dysk` logs
 - locate `csi-dysk` pod according to node name
```
kubectl get po --namespace=dysk -o wide
```

 - Get `csi-dysk` logs
```
kubectl logs csi-dysk-pvn5s -c dysk-driver > dysk-driver.log
```

## CSI known issues
