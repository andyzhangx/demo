## Azure disk attach/detach stress test with StatefulSet
#### Prerequisite
 - [create an azure disk storage class if hdd does not exist](https://github.com/andyzhangx/demo/tree/master/linux/azuredisk#1-create-an-azure-disk-storage-class-if-hdd-does-not-exist)

### 1. Let k8s schedule all pods on one node by `kubectl cordon NODE-NAME`

### 2. Set up a few StatefulSets with azure disk mount on a node#1 (each pod mount with 10 disks)
```
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk1.yaml
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk2.yaml
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk3.yaml
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk4.yaml
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk5.yaml
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk6.yaml
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk7.yaml
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk8.yaml
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk9.yaml
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azuredisk/attach-stress-test/statefulset/60disks/statefulset-azuredisk10.yaml
```

### 3. Let k8s schedule all pods on node#2
```
kubectl cordon node#2
kubectl drain node#1 --ignore-daemonsets --delete-local-data
```

### 4. Watch the pod scheduling process
```
watch kubectl get po -o wide
```

#### clean up
```
kubectl delete sts --all
kubectl delete pvc --all
```
