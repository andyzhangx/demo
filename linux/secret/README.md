## Examples of using k8s secret in azure

#### 1. use secret to access azure file
Following example would use `secret` kind to store azure storage account, and then let azure file use that secret object in k8s.

#### azure file example using secret
https://github.com/andyzhangx/Demo/tree/master/linux/azurefile#static-provisioning-for-azure-file-in-linux-support-from-v150

#### secret file storing azure storage account
https://github.com/andyzhangx/Demo/blob/master/pv/azure-secrect.yaml

#### 2. use secret to Pull an Image from a Azure Private Registry
##### Note:
Image Pull Secrets will work, but are generally unnecessary. 
The ACS cluster uses its service principal to log into the ACR repository.
So as long as the cluster service principal has read rights to ACR, it should all just work.

https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/#create-a-secret-that-holds-your-authorization-token
