## Azure secret example 
Following example would use `secret` kind to store azure storage account, and then let azure file use that secret object in k8s.

#### azure file example using secret
https://github.com/andyzhangx/Demo/tree/master/linux/azurefile#static-provisioning-for-azure-file-in-linux-support-from-v150

#### secret file storing azure storage account
https://github.com/andyzhangx/Demo/blob/master/pv/azure-secrect.yaml
