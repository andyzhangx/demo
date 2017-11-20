## 1. create a pod with subpath mount(use `subPath`)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/subpath/nginx-subpath.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-subpath

## 2. enter the pod container to do validation
kubectl exec -it nginx-subpath -- bash

```
root@nginx-hostpath:/# ls /mnt/hostpath -lt
total 4708
-rw-r--r-- 1 root root   24584 Nov 20 08:25 Microsoft.Azure.Extensions.CustomScript.6.manifest.xml
drwx------ 2 root root    4096 Nov 20 08:12 events
-rw-r--r-- 1 root root   13271 Nov 20 08:11 Prod.1.manifest.xml
-rw-r--r-- 1 root root       1 Nov 20 07:55 Incarnation
-rw-r--r-- 1 root root   21478 Nov 20 07:55 ExtensionsConfig.6.xml
-rw-r--r-- 1 root root    1280 Nov 20 07:55 ABBF05E2E537D4FC04F8BB5695743FEFC8ED981E.crt
-rw-r--r-- 1 root root     875 Nov 20 07:55 D9FBFC079879707B4F6B3D1DDDA71383F55B385A.crt
-rw-r--r-- 1 root root    1860 Nov 20 07:55 ABBF05E2E537D4FC04F8BB5695743FEFC8ED981E.prv
-rw-r--r-- 1 root root    4015 Nov 20 07:55 Certificates.pem
-rw-r--r-- 1 root root    4891 Nov 20 07:55 Certificates.p7m
...
```
