# A simple nginx-server demo
 - supported Kubernetes version: available from v1.7
 - supported agent OS: Linux 

# About
This demo would set up a simple nginx-server, the data is stored in an azure file.

# Prerequisite
An kubernetes cluster with a azure file storage class(name as `azurefile`) should be set up before running deployment scripts.

# Deploy nginx-server application on a kubernetes cluster
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/demo/nginx-server/nginx-server.yaml
```

A Kubernetes service is created which exposes the application to the internet. This process can take a few minutes.
To monitor progress, use the `kubectl get service` command with the `--watch` argument.
```
kubectl get service nginx-server --watch
```
Initially the `EXTERNAL-IP` for the `nginx-server` service appears as pending.

```
nginx-server   10.0.34.242   <pending>     80:30676/TCP   7s
```

Once the `EXTERNAL-IP` address has changed from `pending` to an IP address, use CTRL-C to stop the kubectl watch process.

```
nginx-server   10.0.34.242   52.179.23.131   80:30676/TCP   2m
```

# Manually scale pods
```
kubectl scale --replicas=5 deployment/nginx-server
```

# [Autoscale pods](https://docs.microsoft.com/en-us/azure/aks/tutorial-kubernetes-scale#autoscale-pods)
```
kubectl autoscale deployment nginx-server --cpu-percent=50 --min=3 --max=10
kubectl get hpa
```

# [Update an application](https://docs.microsoft.com/en-us/azure/aks/tutorial-kubernetes-app-update)

### Links


