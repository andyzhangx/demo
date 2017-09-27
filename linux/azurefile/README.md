# Dynamic Provisioning for azure file (support from v1.7.0)
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
kubectl exec -it nginx-azurefile -- bash

```
```

# Static Provisioning for azure file (support from v1.5.0)
## create a secret for azure file
Create an azure file share in the Azure storage account, get the connection info of that azure file and then create a secret that contains the base64 encoded Azure Storage account name and key. In the secret file, base64-encode Azure Storage account name and pair it with name azurestorageaccountname, and base64-encode Azure Storage access key and pair it with name azurestorageaccountkey. For the base64-encode, you could leverage this site: https://www.base64encode.net/

#### use below config file as an example
https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/azure-secrect.yaml

#### use below command to create a secret for azure file
kubectl create -f azure-secrect.yaml

## create a pod with azure file
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azurefile/nginx-pod-azurefile-static.yaml

## enter the pod container to do validation
kubectl exec -it nginx-azurefile -- bash

```
```
