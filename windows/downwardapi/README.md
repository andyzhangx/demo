# downwardAPI on Windows

## 1. create a pod with downwardAPI mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/downwardapi/aspnet-downwardapi.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po aspnet-downwardapi

## 2. enter the pod container to do validation
kubectl exec -it aspnet-downwardapi -- cmd

```
Microsoft Windows [Version 10.0.17134.48]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\>cd mnt

C:\mnt>dir
 Volume in drive C has no label.
 Volume Serial Number is E06C-0519

 Directory of C:\mnt

05/18/2018  08:37 AM    <DIR>          .
05/18/2018  08:37 AM    <DIR>          ..
05/18/2018  08:37 AM    <DIR>          azure
               0 File(s)          4,096 bytes
               3 Dir(s)  21,257,465,856 bytes free

C:\mnt>cd azure

C:\mnt\azure>dir
 Volume in drive C has no label.
 Volume Serial Number is E06C-0519

 Directory of C:\mnt\azure

05/18/2018  08:37 AM    <DIR>          .
05/18/2018  08:37 AM    <DIR>          ..
05/18/2018  08:37 AM    <DIR>          ..2018_05_18_08_37_28.968522372
05/18/2018  08:37 AM    <SYMLINKD>     ..data [..2018_05_18_08_37_28.968522372]
05/18/2018  08:37 AM    <SYMLINK>      annotations [..data\annotations]
05/18/2018  08:37 AM    <SYMLINK>      labels [..data\labels]
               2 File(s)              0 bytes
               4 Dir(s)   9,768,927,232 bytes free

C:\mnt\azure>powershell
Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

PS C:\mnt\azure> Get-Content .\annotations
build="two"
builder="john-doe"
kubernetes.io/config.seen="2018-05-18T08:37:18.0035378Z"
kubernetes.io/config.source="api"
```
