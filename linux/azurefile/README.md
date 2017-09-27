## create a storage class for azure file first
### There are two kinds of configuration of storage class for azure file
#### Method#1: find a suitable storage account that matches skuName and location in same resource group when provisioning azure file
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile.yaml

#### Method#2: use specified storage account  when provisioning azure file
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile-account.yaml


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



