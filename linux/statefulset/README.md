## 1. create a stateful set with azure file mount
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/statefulset/statefulset-azurefile.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po statefulset-azurefile```

#### enter the pod container to do validation
```kubectl exec -it statefulset-azurefile-0 -- bash```

## 2. create a stateful set with azure disk mount
Prerequisite: 
[create a pvc-azuredisk](https://github.com/andyzhangx/Demo/tree/master/linux/azuredisk) first, and then run following command:

```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/statefulset/statefulset-azuredisk-pvc.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po statefulset-azuredisk```

#### enter the pod container to do validation
```kubectl exec -it statefulset-azuredisk-0 -- bash```

### Note:
1. azure disk only supports [RWO](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes), so only one replica is allowed for a stateful set with azure disk mount
2. azure file supports [RWX](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes), multiple replicas are allowed for a stateful set with azure file mount

#### Links
[Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
