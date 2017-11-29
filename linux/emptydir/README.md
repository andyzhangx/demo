## 1. create a pod with emptydir mount on linux
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/emptydir/nginx-emptydir.yaml
#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-emptydir

## 2. enter the pod container to do validation
kubectl exec -it nginx-emptydir -- cmd

```
C:\>d:

D:\>dir

 Directory of D:\

09/25/2017  06:29 AM    <DIR>          .
09/25/2017  06:29 AM    <DIR>          ..
               0 File(s)              0 bytes
               2 Dir(s)  97,325,273,088 bytes free

```
