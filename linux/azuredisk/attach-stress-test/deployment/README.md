## Azure disk attach/detach stress test with Deployment
#### Prerequisite
 - [create an azure disk storage class if hdd does not exist](https://github.com/andyzhangx/demo/tree/master/linux/azuredisk#1-create-an-azure-disk-storage-class-if-hdd-does-not-exist)

### 1. Let k8s schedule all pods on one node by `kubectl cordon NODE-NAME`

### 2. Set up a few Deployments with azure disk mount on a node#1
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk1.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk2.yaml
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/deployment/deployment-azuredisk3.yaml
```

### 3. Let k8s schedule all pods on node#2
```
kubectl cordon node#2
kubectl drain node#1 --ignore-daemonsets --delete-local-data
```

### 4. Watch the pod scheduling process
```
watch kubectl get po
```

#### Note
In my testing, I scheduled three pods with azure disk mount on one node , it took around 3 min for scheduling all three pods from node#1 to node#2 (it took about 1 min for an azure disk to schedule from one node to another)
```
Events:
  Type     Reason                 Age   From                               Message
  ----     ------                 ----  ----                               -------
  Normal   Scheduled              3m    default-scheduler                  Successfully assigned deployment-azuredisk1-6cd8bc7945-kbkvz to k8s-agentpool-88970029-0
  Warning  FailedAttachVolume     3m    attachdetach-controller            Multi-Attach error for volume "pvc-6f2d0788-3b0b-11e8-a378-000d3afe2762" Volume is already exclusively attached to one node and can't be attached to another
  Normal   SuccessfulMountVolume  3m    kubelet, k8s-agentpool-88970029-0  MountVolume.SetUp succeeded for volume "default-token-qt7h6"
  Warning  FailedMount            1m    kubelet, k8s-agentpool-88970029-0  Unable to mount volumes for pod "deployment-azuredisk1-6cd8bc7945-kbkvz_default(5346c040-3e4c-11e8-a378-000d3afe2762)": timeout expired waiting for volumes to attach/mount for pod "default"/"deployment-azuredisk1-6cd8bc7945-kbkvz". list of unattached/unmounted volumes=[azuredisk]
  Normal   SuccessfulMountVolume  1m    kubelet, k8s-agentpool-88970029-0  MountVolume.SetUp succeeded for volume "pvc-6f2d0788-3b0b-11e8-a378-000d3afe2762"
  Normal   Pulling                45s   kubelet, k8s-agentpool-88970029-0  pulling image "nginx"
  Normal   Pulled                 44s   kubelet, k8s-agentpool-88970029-0  Successfully pulled image "nginx"
  Normal   Created                44s   kubelet, k8s-agentpool-88970029-0  Created container
  Normal   Started                42s   kubelet, k8s-agentpool-88970029-0  Started container
```
