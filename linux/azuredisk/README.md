## create a azure disk storage class if sharehdd does not exist
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azuredisk.yaml

## create a azure disk pvc
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azuredisk.yaml
#### make sure pvc is created successfully
kubectl describe pvc pvc-azuredisk

## create a pod with azure disk pvc
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azuredisk/nginx-pod-azuredisk.yaml
#### watch the status of pod until its Status changed from Pending to Running
watch kubectl describe po nginx-azuredisk

## enter the pod container to do validation
kubectl exec -it nginx-azuredisk -- bash

```
```



