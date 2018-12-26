# Kubernetes RBAC related issues
This page lists all the issues when k8s RBAC is enabled

#### 1. Access error when using kubernetes dashboard
Run
```
kubectl create clusterrolebinding kubernetes-dashboard --clusterrole=cluster-admin --serviceaccount=kube-system:kubernetes-dashboard
```
details: https://docs.microsoft.com/en-us/azure/aks/kubernetes-dashboard#for-rbac-enabled-clusters


#### 2. Azure file PVC creation failed
Run
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/rbac/azure-cloud-provider-deployment.yaml
```
and then delete the original PVC and recreate PVC

details: https://github.com/andyzhangx/demo/blob/master/issues/azurefile-issues.md#2-permission-issue-of-azure-file-dynamic-provision-in-acs-engine

#### 3. Helm install charts failed
Installation error would be like following:
```
no available release name found
```

Run 
```
kubectl create clusterrolebinding add-on-cluster-admin --clusterrole=cluster-admin --serviceaccount=kube-system:default
```

#### Update Service Principal in aks-engine
paste my practice about how to update service principal secret in an existing k8s cluster:
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
