# Deploy kubernetes cluster on mooncake
### download acs-engine binary
```
wget https://mirror.kaiyuanshe.org/kubernetes/acs-engine/v0.9.1/acs-engine-v0.9.1-linux-amd64.tar.gz
tar -xvzf acs-engine-v0.9.1-linux-amd64.tar.gz
```

### download acs-engine input file and edit
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/mooncake/kubernetes-1.7.9.json
vi kubernetes-1.7.9.json
```

### generate ARM templates by acs-engine
```
./acs-engine generate kubernetes-1.7.9.json
RESOURCE_GROUP_NAME=andy-k8s179
az group create -l chinaeast -n $RESOURCE_GROUP_NAME
```

### create kubernetes cluster by ARM templates
```
az group deployment create \
    --name="andy-k8s179" \
    --resource-group=$RESOURCE_GROUP_NAME \
    --template-file="./_output/andy-k8s179/azuredeploy.json" \
    --parameters "@./_output/andy-k8s179/azuredeploy.parameters.json"
```

#### Links
acs-engine input file example: https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/mooncake/kubernetes-1.7.9.json

For detailed steps, you could refer to https://github.com/Azure/devops-sample-solution-for-azure-china/blob/master-dev/acs-engine/README.md
