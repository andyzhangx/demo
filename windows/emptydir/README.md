## create a pod with emptydir mount on windows
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/emptydir/aspnet-emptydir.yaml
#### watch the status of pod until its Status changed from Pending to Running
watch kubectl describe po aspnet

## enter the pod container to do validation
kubectl exec -it aspnet -- cmd

```
C:\>d:

D:\>dir

 Directory of D:\

09/25/2017  06:29 AM    <DIR>          .
09/25/2017  06:29 AM    <DIR>          ..
               0 File(s)              0 bytes
               2 Dir(s)  97,325,273,088 bytes free

```
