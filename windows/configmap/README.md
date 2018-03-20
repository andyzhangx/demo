# Use ConfigMap Data in Pods
> Note: 
> - Following example will use ConfigMap as both environment variable and volume mount
> - ConfigMap volume mount on Windows does not work now due to a [docker container on Windows bug](https://github.com/kubernetes/kubernetes/issues/52419)
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
Microsoft Windows [Version 10.0.16299.64]
(c) 2017 Microsoft Corporation. All rights reserved.

C:\>echo %SPECIAL_LEVEL_KEY%
very

C:\etc\config>dir
 Volume in drive C has no label.
 Volume Serial Number is 8C6F-2797

 Directory of C:\etc\config

03/20/2018  05:47 AM    <DIR>          .
03/20/2018  05:47 AM    <DIR>          ..
03/20/2018  05:47 AM    <DIR>          ..2018_03_20_05_47_41.741744457
03/20/2018  05:47 AM    <SYMLINKD>     ..data [..2018_03_20_05_47_41.741744457]
03/20/2018  05:46 AM    <SYMLINK>      special.how [..data\special.how]
               1 File(s)              0 bytes
               4 Dir(s)  302,937,223,168 bytes free
```

### Links:
[Use ConfigMap Data in Pods](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
