## 1. create a pod with gitrepo mount
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/gitrepo/nginx-gitrepo.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-gitrepo

## 2. enter the pod container to do validation
kubectl exec -it nginx-gitrepo -- bash

```
```
