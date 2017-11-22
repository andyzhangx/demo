# Use ConfigMap Data in Pods
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
```

### Links:
Use ConfigMap Data in Pods: https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/
