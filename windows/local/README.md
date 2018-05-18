## 1. create a local Persistent Volume (PV)
 - download `pv-local.yaml` and modify `spec.local.path`, `kubernetes.io/hostname` fields
```
wget -O pv-local.yaml https://raw.githubusercontent.com/andyzhangx/demo/master/windows/local/pv-local.yaml
vi pv-local.yaml
kubectl create -f pv-local.yaml
```
 > Note:
 > - You may get following error if `spec.local.path` is assigned as `c:`, this issue is fixed in [v1.10.3](https://github.com/kubernetes/kubernetes/pull/62615)
```
$ kubectl create -f pv-local.yaml
The PersistentVolume "pv-local" is invalid: spec.local: Invalid value: "c:": must be an absolute path
```

## 2. create a local Persistent Volume Claim (PVC) tied to above PV
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/windows/local/pvc-local.yaml
```
 - watch the status of PVC until its Status changed from `Pending` to `Running`
```
watch kubectl describe pvc pvc-local
```

## 3. create a pod with local mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/local/aspnet-pod-local.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
```watch kubectl describe po aspnet-local```

## 4. enter the pod container to do validation
```
$ kubectl exec -it aspnet-local -- cmd
Microsoft Windows [Version 10.0.17134.48]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\>cd data

C:\data>dir
 Volume in drive C has no label.
 Volume Serial Number is E06C-0519

 Directory of C:\data

05/17/2018  11:39 AM    <DIR>          AzureData
05/18/2018  08:48 AM    <DIR>          k
05/18/2018  05:39 AM    <DIR>          k-backup
04/27/2018  06:11 PM        55,552,858 k.zip
05/17/2018  11:39 AM    <DIR>          Packages
04/11/2018  11:44 PM    <DIR>          PerfLogs
05/17/2018  06:26 PM    <DIR>          Program Files
04/11/2018  11:44 PM    <DIR>          Program Files (x86)
05/18/2018  05:38 AM    <DIR>          tmp
05/18/2018  05:35 AM    <DIR>          Users
05/17/2018  11:42 AM    <DIR>          var
05/17/2018  07:01 PM    <DIR>          WER
05/17/2018  01:47 PM    <DIR>          Windows
05/17/2018  11:42 AM    <DIR>          WindowsAzure
               1 File(s)     55,552,858 bytes
              13 Dir(s)   9,760,030,720 bytes free
```

#### Links
 - [Local Volume](https://kubernetes.io/docs/concepts/storage/volumes/#local)
