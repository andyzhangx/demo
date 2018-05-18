# Use ConfigMap Data in Pods
> Note: 
> - Following example will use ConfigMap as both environment variable and volume mount
### 1. Define an environment variable as a key-value pair in a ConfigMap:
```
kubectl create configmap special-config --from-literal=special.how=very 
```
### 2. Assign the `special.how` value defined in the ConfigMap to the `SPECIAL_LEVEL_KEY` environment variable in the Pod specification.
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/configmap/aspnet-configmap.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po aspnet-configmap

### 2. enter the pod container to do validation
kubectl exec -it aspnet-configmap -- cmd

```
Microsoft Windows [Version 10.0.17134.48]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\>echo %SPECIAL_LEVEL_KEY%
very

C:\>cd net\config
The system cannot find the path specified.

C:\>cd etc\config

C:\etc\config>dir
 Volume in drive C has no label.
 Volume Serial Number is E06C-0519

 Directory of C:\etc\config

05/18/2018  08:25 AM    <DIR>          .
05/18/2018  08:25 AM    <DIR>          ..
05/18/2018  08:25 AM    <DIR>          ..2018_05_18_08_25_14.352501044
05/18/2018  08:25 AM    <SYMLINKD>     ..data [..2018_05_18_08_25_14.352501044]
05/18/2018  08:22 AM    <SYMLINK>      special.how [..data\special.how]
               1 File(s)              0 bytes
               4 Dir(s)   9,769,730,048 bytes free

C:\etc\config>powershell
Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

PS C:\etc\config> get-content .\special.how
very
PS C:\etc\config>
```

### Links:
[Use ConfigMap Data in Pods](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
