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

#### Links
 - [Accessing RBAC enabled Kubernetes Dashboard](https://unofficialism.info/posts/accessing-rbac-enabled-kubernetes-dashboard/)
