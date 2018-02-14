## Attention: 
azure disk & azure file volume mounts in k8s Deployment may cause inconsistent race condition error since a new pod is being recreated when the old pod is being deleted on same node. So we would stongly suggest **using StatefulSet instead of Deployment** when there are azure disk & azure file volume mounts. Here is the [StatefulSet example](https://github.com/andyzhangx/Demo/blob/master/linux/statefulset/README.md)

Below are only POC Deployment examples with azure disk & file mount, should **not** use Deployment with azure disk & azure file volume mounts in production.

## 1. create a deployment with azure file mount
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/deployment/deployment-azurefile.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po deployment-azurefile```

#### enter the pod container to do validation
```kubectl exec -it deployment-azurefile-0 -- bash```

## 2. create a deployment with azure disk mount
Prerequisite: [create a pvc-azuredisk](https://github.com/andyzhangx/Demo/tree/master/linux/azuredisk) first, and then run following command:

```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/deployment/deployment-disk.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po deployment-azurefile```

#### enter the pod container to do validation
```kubectl exec -it deployment-azuredisk-0 -- bash```

### Note:
1. azure disk only supports [RWO](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes), so only one replica is allowed for a deployment with azure disk mount
2. azure file supports [RWX](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes), multiple replicas are allowed for a deployment with azure file mount

#### Links
[Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
