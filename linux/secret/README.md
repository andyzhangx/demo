## Examples of using k8s secret in azure

### 1. use secret to access azure file
Following example would use `secret` kind to store azure storage account, and then let azure file use that secret object in k8s.

#### azure file example using secret
https://github.com/andyzhangx/Demo/tree/master/linux/azurefile#static-provisioning-for-azure-file-in-linux-support-from-v150

#### secret file storing azure storage account
https://github.com/andyzhangx/Demo/blob/master/pv/azure-secrect.yaml

### 2. use secret to Pull an Image from an Azure Private Registry
#### 1) Create a Secret that holds your authorization token
```
kubectl create secret docker-registry regsecret --docker-server=<your-registry-server> --docker-username=<your-name> --docker-password=<your-pword> --docker-email=<your-email>
```

#### 2) Create a Pod that uses your Secret
Here is a configuration file for a Pod that needs access to your secret data:
```
apiVersion: v1
kind: Pod
metadata:
  name: nginx-private-reg
spec:
  containers:
  - name: nginx-private-reg
    image: YOUR-ACR-ACCOUNT.azurecr.io/nginx:v1
  imagePullSecrets:
  - name: regsecret
```

#### 3) Watch the status of pod until its `Status` changed from `Pending` to `Running`
```
watch kubectl describe po nginx-private-reg
```

Refer to following link for more details:
[Pull an Image from a Private Registry](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry)

##### Note:
The ACS cluster uses its service principal to log into the ACR repository. So as long as the cluster service principal has read rights to ACR, there is no need to use secret to Pull an Image from an Azure Private Registry.
