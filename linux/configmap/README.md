# Use ConfigMap Data in Pods
> Note: Following example will use ConfigMap as both environment variable and volume mount
### 1. Define an environment variable as a key-value pair in a ConfigMap:
```
kubectl create configmap special-config --from-literal=special.how=very 
```
### 2. Assign the `special.how` value defined in the ConfigMap to the `SPECIAL_LEVEL_KEY` environment variable in the Pod specification.
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/configmap/nginx-configmap.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-configmap

### 2. enter the pod container to do validation
```kubectl exec -it nginx-configmap -- bash```

```
root@nginx-configmap:/# echo $SPECIAL_LEVEL_KEY
very
root@nginx-configmap:/# ls -lt -a /etc/config/
total 12
drwxr-xr-x 1 root root 4096 Mar 20 03:17 ..
drwxrwxrwx 3 root root 4096 Mar 20 03:17 .
drwxr-xr-x 2 root root 4096 Mar 20 03:17 ..3983_20_03_03_17_36.284201812
lrwxrwxrwx 1 root root   31 Mar 20 03:17 ..data -> ..3983_20_03_03_17_36.284201812
lrwxrwxrwx 1 root root   18 Mar 20 03:17 special.how -> ..data/special.how
root@nginx-configmap:/# cat /etc/config/special.how
very
```

### Links:
[Use ConfigMap Data in Pods](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
