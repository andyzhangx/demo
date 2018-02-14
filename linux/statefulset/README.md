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
3. For statefulset with azure disk mount, there will be `Multi-Attach error` when scheduling a pod from one node to another, it's by design since attach/detach disk in VM costs minutes. After around 3 min, disk mounting will be successful.

```
Events:
  Type     Reason                 Age               From                                Message
  ----     ------                 ----              ----                                -------
  Normal   Scheduled              3m                default-scheduler                   Successfully assigned deployment-azuredisk-b5f7b5d59-n5sj4 to k8s-agentpool2-40588258-0
  Normal   SuccessfulMountVolume  3m                kubelet, k8s-agentpool2-40588258-0  MountVolume.SetUp succeeded for volume "default-token-hqvc5"
  Warning  FailedAttachVolume     3m (x25 over 3m)  attachdetach                        Multi-Attach error for volume "pvc-c048abf5-1189-11e8-846f-000d3af71b87" Volume is already exclusively attached to one node and can't be attached to another
  Warning  FailedMount            1m                kubelet, k8s-agentpool2-40588258-0  Unable to mount volumes for pod "deployment-azuredisk-b5f7b5d59-n5sj4_default(f253659d-118a-11e8-846f-000d3af71b87)": timeout expired waiting for volumes to attach/mount for pod "default"/"deployment-azuredisk-b5f7b5d59-n5sj4". list of unattached/unmounted volumes=[blobdisk01]
  Warning  FailedSync             1m                kubelet, k8s-agentpool2-40588258-0  Error syncing pod
  Normal   SuccessfulMountVolume  57s               kubelet, k8s-agentpool2-40588258-0  MountVolume.SetUp succeeded for volume "pvc-c048abf5-1189-11e8-846f-000d3af71b87"
  Normal   Pulling                51s               kubelet, k8s-agentpool2-40588258-0  pulling image "nginx"
  Normal   Pulled                 44s               kubelet, k8s-agentpool2-40588258-0  Successfully pulled image "nginx"
  Normal   Created                44s               kubelet, k8s-agentpool2-40588258-0  Created container
  Normal   Started                44s               kubelet, k8s-agentpool2-40588258-0  Started container
```

#### Links
[StatefulSet](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
