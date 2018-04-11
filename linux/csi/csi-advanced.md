## CSI debugging
#### Get CSI driver logs
Take dysk CSI driver as an example:
 - Get `csi-dysk-provisioner` logs
```
kubectl logs csi-dysk-provisioner-0 --namespace=dysk > csi-dysk-provisioner-0.log
```
 - Get `csi-dysk` logs
locate `csi-dysk` pod according to node is invoked by CSI:
```
kubectl get po --namespace=dysk -o wide
```

Get `csi-dysk` logs
```
kubectl logs csi-dysk-pvn5s -c dysk-driver > dysk-driver.log
```

## CSI known issues
