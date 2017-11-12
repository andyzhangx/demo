# Mooncake Demo
### 1. Create a k8s service using docker hub images
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
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/demo/azure-examples/mooncake/nginx-pod.yaml
kubectl get po -w
kubectl describe po nginx
```

#cleanup
```
kubectl delete po nginx
```

### 4. Demo jenkins 
https://github.com/andyzhangx/spin-kub-demo.git
```
putty.exe -ssh -L 8080:localhost:8080 azureuser@andy-jenkins.chinaeast.cloudapp.chinacloudapi.cn
kubectl scale --replicas=3 deployment/testapp
```
http://andy-jenkins.chinaeast.cloudapp.chinacloudapi.cn:8080/

### Links:
https://github.com/Azure/devops-sample-solution-for-azure-china

##### scale a k8s cluster
https://github.com/Azure/acs-engine/blob/master/docs/kubernetes/scale.md
https://github.com/kubernetes/charts/tree/master/stable/acs-engine-autoscaler

##### best practice for deploying k8s cluster on mooncake
https://github.com/andyzhangx/Demo/tree/master/acs-engine/mooncake
