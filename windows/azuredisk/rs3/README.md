## Support from k8s version 1.7.x on Windows 2016 DataCenter
## 1. create an azure disk storage class if `hdd` does not exist
#### option#1: k8s agent pool is based on blob disk VM
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azuredisk.yaml```

#### option#2: k8s agent pool is based on managed disk VM
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azuredisk-managed.yaml```

## 2. create an azure disk pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azuredisk.yaml```

#### make sure pvc is created successfully
```watch kubectl describe pvc pvc-azuredisk```

## 3. create a pod with azure disk pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/azuredisk/rs3/aspnet-pod-azuredisk.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po aspnet-azuredisk```

## 4. enter the pod container to do validation
```kubectl exec -it aspnet-azuredisk -- cmd```

```
C:\>d:
D:\>mkdir test
D:\>cd test
D:\test>dir
 Volume in drive D has no label.
 Volume Serial Number is 50C1-AE52

 Directory of D:\test

09/20/2017  12:40 AM    <DIR>          .
09/20/2017  12:40 AM    <DIR>          ..
               0 File(s)              0 bytes
               2 Dir(s)   5,334,327,296 bytes free
```



