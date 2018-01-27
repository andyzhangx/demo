## Attention: 
azure disk & azure file volume mounts in k8s Deployment may cause inconsistent race condition error since a new pod will be recreated when the old pod is deleted on same node. So we would stongly suggest **using StatefulSet instead of Deployment** when there are azure disk & azure file volume mounts. You could reach StatefulSet example [here](https://github.com/andyzhangx/Demo/blob/master/linux/statefulset/README.md)

Below are POC examples, should **not** use Deployment with azure disk & azure file volume mounts in production.

## create a deployment with azure file mount
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/deployment/deployment-azurefile.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po deployment-azurefile```

#### enter the pod container to do validation
```kubectl exec -it deployment-azurefile-0 -- bash```

