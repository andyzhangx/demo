# Deploy kubernetes cluster on mooncake
```
./acs-engine generate kubernetes-1.7.9.json
RESOURCE_GROUP_NAME=andy-k8s179
az group create -l chinaeast -n $RESOURCE_GROUP_NAME

az group deployment create \
    --name="andy-k8s179" \
    --resource-group=$RESOURCE_GROUP_NAME \
    --template-file="./_output/andy-k8s179/azuredeploy.json" \
    --parameters "@./_output/andy-k8s179/azuredeploy.parameters.json"
```

acs-engine input file example: https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/mooncake/kubernetes-1.7.9.json

For detailed steps, you could refer to https://github.com/Azure/devops-sample-solution-for-azure-china/blob/master-dev/acs-engine/README.md
