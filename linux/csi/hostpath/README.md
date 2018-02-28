## 1. hostpath csi driver example
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/basic/nginx-pod.yaml```

#### 2. watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po nginx```

## 3. enter the pod container to do validation
```kubectl exec -it nginx -- bash```
