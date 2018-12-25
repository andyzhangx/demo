# Set azure file mountOptions
 - azure file mountOptions feature is available from v1.8.5, for lower k8s version, could use `volume.beta.kubernetes.io/mount-options` instead, which is only supported in PersistentVolume.
 - For dynamic provision, `mountOptions` should be set in storage class, while for static provision(use existing file share), `mountOptions` should be set in PersistentVolume
 
## Set mountOptions in Dynamic Provisioning
#### download `storageclass-azurefile-mountoptions.yaml` file and modify `mountOptions` values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile-mountoptions.yaml
vi storageclass-azurefile-mountoptions.yaml
kubectl create -f storageclass-azurefile-mountoptions.yaml
```

## Set mountOptions in Static Provisioning
> static provisioning means user must create an azure file before using azure file mount feature.

## Prerequisite
 - create an azure file share in Azure storage account in the same resource group with k8s cluster
 - get `azurestorageaccountname`, `azurestorageaccountkey` and `shareName` of that azure file
 
#### 1. create a secret for azure file
 - Use `kubectl create secret` to create `azure-secret`
```
kubectl create secret generic azure-secret --from-literal azurestorageaccountname=NAME --from-literal azurestorageaccountkey="KEY" --type=Opaque
```

#### 2. create an azure file persistent volume(pv)
 - for k8s version >= v1.8.5
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pv-azurefile-mountoptions.yaml
```
 - for k8s version < v1.8.5 (including 1.7.x)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pv-azurefile-mountoptions-1.7.yaml
```
> Note: `vers`,`dir_mode`,`file_mode` could not be specified in `pv-azurefile-mountoptions-1.7.yaml` since there is already default values as in [vers=3.0,dir_mode=0777,file_mode=0777](https://github.com/kubernetes/kubernetes/blob/release-1.7/pkg/volume/azure_file/azure_file.go#L215)


#### 3. create an azure file persistent volume claim(pvc)
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azurefile-static.yaml```

 - watch the status of pv until its `Status` changed from `Pending` to `Bound`
```
watch kubectl describe pvc pvc-azurefile
```

#### 4. create a pod with azure file pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azurefile/nginx-pod-azurefile.yaml```

 - watch the status of pod until its Status changed from `Pending` to `Running`
```
watch kubectl describe po nginx-azurefile
```

#### Or Use A combined configuration of step#2 to #4:
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azurefile/pod-azurefile-mountoptions-example.yaml
```

#### 5. enter the pod container to do validation
```kubectl exec -it nginx-azurefile -- bash```

```
root@nginx-azurefile:/# df -h
Filesystem                                 Size  Used Avail Use% Mounted on
overlay                                     30G  4.1G   26G  14% /
tmpfs                                      6.9G     0  6.9G   0% /dev
tmpfs                                      6.9G     0  6.9G   0% /sys/fs/cgroup
//andytestx.file.core.windows.net/k8stest  5.0G   64K  5.0G   1% /mnt/azurefile
/dev/sda1                                   30G  4.1G   26G  14% /etc/hosts
shm                                         64M     0   64M   0% /dev/shm
tmpfs                                      6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount

root@nginx-azurefile:/mnt/azurefile# ls -lt
total 1
-rwx-w-r-- 1 1000 1000 1015 Nov 27 06:09 outfile
drwx-wx--x 2 1000 1000    0 Nov 27 06:09 a
```

 - `fileMode`, `dirMode` value would be different in different versions, in latest master branch, it's `0755` by default, to set a different value, follow this [mount options support of azure file](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/azurefile-mountoptions.md) (available from v1.8.5). 
   - For version v1.8.0-v1.8.4, since [mount options support of azure file](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/azurefile-mountoptions.md) is not available, as a workaround, [securityContext](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) could be specified for the pod, [detailed pod example](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/demo-azurefile-securitycontext.yaml)
```
  securityContext:
    runAsUser: XXX
    fsGroup: XXX
```

| version | `fileMode`, `dirMode` value |
| ---- | ---- |
| v1.6.x, v1.7.x | 0777 |
| v1.8.0-v1.8.5 | 0700 |
| v1.8.6 or above | 0755 |
| v1.9.0 | 0700 |
| v1.9.1 or above | 0755 |
