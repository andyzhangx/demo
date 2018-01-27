## create a deployment with azure file mount
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/deployment/deployment-azurefile.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po deployment-azurefile```

#### enter the pod container to do validation
```kubectl exec -it deployment-azurefile-0 -- bash```

