# Mooncake Demo
'''
kubectl create -f https://raw.githubusercontent.com/Azure-Samples/azure-voting-app-redis/master/azure-vote-all-in-one-redis.yml
kubectl get service azure-vote-front --watch

kubectl get pod
kubectl scale --replicas=3 deployment/azure-vote-front
kubectl get pod
'''

#cleanup
'''
kubectl delete service azure-vote-front
kubectl delete service azure-vote-back
kubectl delete deployment azure-vote-back
kubectl delete deployment azure-vote-front
'''
