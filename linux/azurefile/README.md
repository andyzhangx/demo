## create a storage class for azure file first
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile.yaml

## create a pvc for azure file first
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azurefile.yaml
#### make sure pvc is created successfully
kubectl describe pvc pvc-azurefile

## create a pod with azure disk pvc
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azurefile/nginx-pod-azurefile.yaml
#### watch the status of pod until its Status changed from Pending to Running
watch kubectl describe po nginx-azurefile

## enter the pod container to do validation
kubectl exec -it nginx-azurefile -- cmd

```
```



