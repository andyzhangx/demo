##  1. create a simple pod on windows
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/basic/aspnet-pod.yaml

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po aspnet

## 2. enter the pod container to do validation
kubectl exec -it aspnet -- cmd
