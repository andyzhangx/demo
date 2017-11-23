# Azure Container Service - AKS

#### get aks credentials
```
az aks get-credentials -g RESOURCE_GROUP_NAME -n CLUSTER_NAME
```

#### known issues
1. default storage class is not set by default in AKS cluster: https://github.com/Azure/AKS/issues/48
woraround:
```
kubectl patch storageclass default -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```
