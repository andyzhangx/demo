# Azure Container Service - AKS

#### get aks cluster credentials
```
az aks get-credentials -g RESOURCE_GROUP_NAME -n CLUSTER_NAME
```

#### scale up/down aks cluster nodes
```
az aks scale -g RESOURCE_GROUP_NAME -n CLUSTER_NAME --agent-count=2
```

#### known issues
1. default storage class is not set by default in AKS cluster: https://github.com/Azure/AKS/issues/48
Woraround is as following:
```
kubectl patch storageclass default -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```
