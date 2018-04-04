## 1. create a local Persistent Volume (PV)
 - download `pv-local.yaml` and modify `spec.local.path`, `kubernetes.io/hostname` fields
```
wget -O pv-local.yaml https://raw.githubusercontent.com/andyzhangx/demo/master/windows/local/pv-local.yaml
vi pv-local.yaml
kubectl create -f pv-local.yaml
```
## 2. create a local Persistent Volume Claim (PVC) tied to above PV
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/windows/local/pvc-local.yaml
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

```

#### Links
 - [Local Volume](https://kubernetes.io/docs/concepts/storage/volumes/#local)
