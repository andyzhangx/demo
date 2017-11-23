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
1. default storage class is not set by default in AKS cluster, see issue: https://github.com/Azure/AKS/issues/48
you may get following error when set up a pvc with a default storage class
```
Events:
  FirstSeen     LastSeen        Count   From                            SubObjectPath   Type            Reason          Message
  ---------     --------        -----   ----                            -------------   --------        ------          -------
  13m           3m              42      persistentvolume-controller                     Normal          FailedBinding   no persistent volumes available for this claim and no storage class is set
```
Workaround is as following:
```
kubectl patch storageclass default -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```
