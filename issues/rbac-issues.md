# Kubernetes RBAC related issues

#### 1. Access error when using kubernetes dashboard due to k8s RBAC enabled
Run
```
kubectl create clusterrolebinding kubernetes-dashboard --clusterrole=cluster-admin --serviceaccount=kube-system:kubernetes-dashboard
```
details: https://docs.microsoft.com/en-us/azure/aks/kubernetes-dashboard#for-rbac-enabled-clusters


#### 2. Azure file PVC creation due to RBAC failed
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
