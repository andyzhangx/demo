```
andyacstestmgmt.westus2.cloudapp.azure.com

ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDSEzOJcriMD1BcbcH7EKEkNjHvo+TB+7hWZ+JrLDKDoML6IrAHSUPoBEjwbLLh1Ut6iX/2g9GzQlwWZ9+uvNYfwqLRillTNq/oHGOS5FwfA9RV+O4/VXqwMogJmHxeVah7k7/auqp7vVKWoKBy6/HqxSJv+u80JO9wat1U4oHDesj8I3zhxZyk8MrvfeDNzhIoDTazc8q7OiHayZ18G/vTjAEATwiSY4dHyhxHl7qtUXKc2gLet7hlYeTeAUp0XPiQMM9y33BPDOyJkw2faSzcl7eeKFsdzuyZuSwsPePxSaX5fgXCbeqQ/BrzraDnwJlaC3IjzhT8HxfQJbYpD4mz root@andy-dev
91fe9b3f-d35a-4f9b-8c92-e8572916bd9a
ed0a7cc2-070e-416c-b42c-734da36a9caa

kubectl create -f https://raw.githubusercontent.com/Azure-Samples/azure-voting-app-redis/master/azure-vote-all-in-one-redis.yml
kubectl get service azure-vote-front --watch

kubectl get pod
kubectl scale --replicas=2 deployment/azure-vote-front
kubectl get pod
```
