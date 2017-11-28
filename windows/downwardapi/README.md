## 1. create a pod with downwardAPI mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/downwardapi/aspnet-downwardapi.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po aspnet-downwardapi

## 2. enter the pod container to do validation
kubectl exec -it aspnet-downwardapi -- cmd

```
C:\>cd mnt

C:\mnt>dir
 Volume in drive C has no label.

 Directory of C:\mnt

11/28/2017  07:46 AM    <DIR>          .
11/28/2017  07:46 AM    <SYMLINKD>     azure [\\?\ContainerMappedDirectories\4A3EA4F6-FF3C-4DF6-9078-BD8ECFBFAADC]
               0 File(s)              0 bytes
               3 Dir(s)  21,230,641,152 bytes free
C:\mnt>cd azure

C:\mnt\azure>dir
 Volume in drive C has no label.
 Volume Serial Number is F878-8D74

 Directory of C:\mnt\azure

11/28/2017  07:46 AM    <DIR>          .
11/28/2017  07:46 AM    <DIR>          ..
11/28/2017  07:46 AM    <DIR>          ..119811_28_11_07_46_28.746441697
11/28/2017  07:46 AM    <SYMLINKD>     ..data [..119811_28_11_07_46_28.746441697]
11/28/2017  07:46 AM    <SYMLINK>      annotations [..data\annotations]
11/28/2017  07:46 AM    <SYMLINK>      labels [..data\labels]
               2 File(s)              0 bytes
               4 Dir(s)   1,055,793,152 bytes free

C:\mnt\azure>powershell
Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

PS C:\mnt\azure> Get-Content .\annotations
Get-Content : Could not find a part of the path 'C:\mnt\azure\annotations'.
At line:1 char:1
+ Get-Content .\annotations
+ ~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:\mnt\azure\annotations:String) [Get-Content], DirectoryNotFoundException
    + FullyQualifiedErrorId : GetContentReaderDirectoryNotFoundError,Microsoft.PowerShell.Commands.GetContentCommand

PS C:\mnt\azure> cd .\..119811_28_11_07_46_28.746441697\
PS C:\mnt\azure\..119811_28_11_07_46_28.746441697> ls -lt
Get-ChildItem : A parameter cannot be found that matches parameter name 'lt'.
At line:1 char:4
+ ls -lt
+    ~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-ChildItem], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.GetChildItemCommand

PS C:\mnt\azure\..119811_28_11_07_46_28.746441697> dir


    Directory: C:\mnt\azure\..119811_28_11_07_46_28.746441697


Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----       11/28/2017   7:46 AM            121 annotations
-a----       11/28/2017   7:46 AM             58 labels


PS C:\mnt\azure\..119811_28_11_07_46_28.746441697> Get-Content .\annotations
build="two"
builder="john-doe"
kubernetes.io/config.seen="2017-11-28T07:46:28.3353966Z"
kubernetes.io/config.source="api"
PS C:\mnt\azure\..119811_28_11_07_46_28.746441697> Get-Content .\labels
cluster="test-cluster1"
rack="rack-22"
zone="us-est-coast"
```
