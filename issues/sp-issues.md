### Update Service Principal in AKS & aks-engine
#### Option#1: extend the original SP password for one more year
Get `aadClientId` and `aadClientSecret` from `/etc/kubernetes/azure.json` on the node
```
az ad sp credential reset --name <aadClientId> --password <aadClientSecret> --years 1
```

Wait about two hours at most, the original SP token will expire, and then `controller-manager`, `api-server`, `kubelet` will work.

#### Option#2: create a new SP password and then replace the password in `/etc/kubernetes/azure.json`
 - check whether current Service Principal `aadClientId` has expired
```
az ad sp credential list --id <aadClientId>
```

 - paste my practice about how to update service principal secret in an existing k8s cluster:
```
# update service principle (aadClientSecret)
sudo vi /etc/kubernetes/azure.json

# on master node
docker restart $(docker ps  -q)

# on Linux agent node
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# on Windows agent node
notepad c:\k\azure.json  #update aadClientSecret and save
start powershell
stop-service kubeproxy
stop-service kubelet
start-service kubeproxy
start-service kubelet
```

To automate this, you may use custom extension to run these scripts in VM, refer to https://docs.microsoft.com/en-us/azure/virtual-machines/extensions/custom-script-linux
