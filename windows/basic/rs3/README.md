##  1. create a simple pod on windows
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/basic/rs3/windowsservercore-pod.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po windowsservercore```

## 2. enter the pod container to do validation
```kubectl exec -it windowsservercore -- cmd```
