## 1. create a pod with subpath mount(use `subPath`)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/subpath/aspnet-subpath.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po aspnet-subpath

## 2. enter the pod container to do validation
kubectl exec -it aspnet-subpath -- cmd

```
C:\>cd mnt\azure

C:\mnt\azure>dir
 Volume in drive C has no label.
 Volume Serial Number is F878-8D74

 Directory of C:\mnt\azure

11/08/2017  03:20 AM    <DIR>          .
11/08/2017  03:20 AM    <DIR>          ..
09/29/2017  02:39 PM    <DIR>          ADFS
09/29/2017  12:28 PM    <DIR>          AppCompat
10/13/2017  09:04 PM    <DIR>          apppatch
10/04/2017  11:28 PM    <DIR>          assembly
09/29/2017  12:25 PM            65,536 bfsvc.exe
09/29/2017  12:28 PM    <DIR>          Boot
09/29/2017  12:28 PM    <DIR>          Branding
10/13/2017  09:02 PM    <DIR>          CbsTemp
10/03/2017  08:25 PM    <DIR>          debug

...
```
