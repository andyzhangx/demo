# Set mountOptions in Dynamic Provisioning for azure file (support from v1.7.0)
#### download `storageclass-azurefile-mountoptions.yaml` file and modify `mountOptions` values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile-mountoptions.yaml
vi storageclass-azurefile-mountoptions.yaml.yaml
kubectl create -f storageclass-azurefile-mountoptions.yaml.yaml
```

# Set mountOptions in Static Provisioning for azure file (support from v1.5.0)
kubernetes v1.5, v1.6 does not support dynamic provisioning for azure file, only static provisioning is supported for azure file which means a storage account should be created before using azure file mount feature.

## 1. create a secret for azure file
Create an azure file share in the Azure storage account, get the connection info of that azure file and then create a k8s secret that contains base64 encoded Azure Storage account name and key. 
In the secret file, base64-encode Azure Storage account name and pair it with name azurestorageaccountname, and base64-encode Azure Storage access key and pair it with name azurestorageaccountkey. 
For how to base64-encode, you could leverage this site: https://www.base64encode.net/

#### 2. download `azure-secrect.yaml` file and modify `azurestorageaccountname`, `azurestorageaccountkey` values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/azure-secrect.yaml
vi azure-secrect.yaml
kubectl create -f azure-secrect.yaml
```

## 3. create a azure file persistent volume(pv)
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pv-azurefile-mountoptions.yaml```

## 4. create a azure file persistent volume claim(pvc)
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azurefile-static.yaml```

#### watch the status of pv until its `Status` changed from `Pending` to `Bound`
```watch kubectl describe pvc pvc-azurefile```

## 5. create a pod with azure file pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/azurefile/nginx-pod-azurefile.yaml```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po nginx-azurefile```

## 6. enter the pod container to do validation
```kubectl exec -it nginx-azurefile -- bash```

```
root@nginx-azurefile:/# df -h
Filesystem                                 Size  Used Avail Use% Mounted on
overlay                                     30G  4.1G   26G  14% /
tmpfs                                      6.9G     0  6.9G   0% /dev
tmpfs                                      6.9G     0  6.9G   0% /sys/fs/cgroup
//andytestx.file.core.windows.net/k8stest  5.0G   64K  5.0G   1% /mnt/blobfile
/dev/sda1                                   30G  4.1G   26G  14% /etc/hosts
shm                                         64M     0   64M   0% /dev/shm
tmpfs                                      6.9G   12K  6.9G   1% /run/secrets/kubernetes.io/serviceaccount

root@nginx-azurefile:/mnt/blobfile# ls -lt
total 1
-rwx-w-r-- 1 1000 1000 1015 Nov 27 06:09 outfile
drwx-wx--x 2 1000 1000    0 Nov 27 06:09 a
```
