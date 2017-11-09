# Mooncake Demo
### 1. Create a service using docker hub images
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/demo/azure-examples/mooncake/azure-vote-all-in-one-redis.yml
kubectl get pod -w
kubectl get service azure-vote-front --watch

kubectl get pod
kubectl scale --replicas=3 deployment/azure-vote-front
kubectl get pod -w
```

##### Speedup: use images in docker private registry
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/demo/azure-examples/mooncake/azure-vote-all-in-one-redis-speedup.yml
```

#cleanup
```
kubectl delete service azure-vote-front
kubectl delete service azure-vote-back
kubectl delete deployment azure-vote-back
kubectl delete deployment azure-vote-front
```
### 2. Use docker private registry on mooncake
docker hub proxy in china: https://www.docker-cn.com/registry-mirror

docker private registry on mooncake(only for testing/demo): 
```
curl https://mirror.azure.cn:5000/v2/_catalog
```

##### pull docker image from docker hub and then push image to docker private registry on mooncake
```
docker pull registry.docker-cn.com/library/nginx
docker tag registry.docker-cn.com/library/nginx mirror.azure.cn:5000/library/nginx
docker push mirror.azure.cn:5000/library/nginx
```

### 3. Create a pod using docker private registry on mooncake
```
curl https://mirror.azure.cn:5000/v2/_catalog

kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/demo/azure-examples/mooncake/nginx-pod.yaml
kubectl get po -w
kubectl describe po nginx
```

#cleanup
```
kubectl delete po nginx
```

### Note:
https://github.com/Azure/devops-sample-solution-for-azure-china
