## create a pod with emptydir mount on windows
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/emptydir/aspnet-emptydir.yaml
#### watch the status of pod until its Status changed from Pending to Running
watch kubectl describe po aspnet

## enter the pod container to do validation
kubectl exec -it aspnet -- cmd
