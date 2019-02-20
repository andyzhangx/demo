## Use service principal for kubernetes devlopment
We could create an Azure service principal, restrict it to only one or few resource group(s), and then share the service principal for devlopment, e.g. create AKS or aks-engine on that resource group, below are the detailed steps:

 - create service principal
```
RESOURCE_GROUP_NAME=<restricted-resource-group-name>
LOCATION=eastus2
az group create -n $RESOURCE_GROUP_NAME -l $LOCATION

az ad sp create-for-rbac -n <sp-name> --role contributor --scopes /subscriptions/{subs-id}/resourceGroups/$RESOURCE_GROUP_NAME
...
Retrying role assignment creation: 1/36
{
  "appId": "...",
  "displayName": "<sp-name>",
  "name": "http://<sp-name>",
  "password": "...",
  "tenant": "..."
}
```

 - use service principal to login
 ```
az login --service-principal -u <appId> -p <password> -t <tenant>
az group list
 ```

 - use service principal to create kubernetes cluster by aks-engine
```
./aks-engine generate ./kubernetes-1.13.3.json
dnsPrefix=k8s1133
az group deployment create \
    --name="your-deployment-name" \
    --resource-group=$RESOURCE_GROUP_NAME \
    --template-file="./_output/$dnsPrefix/azuredeploy.json" \
    --parameters "@./_output/$dnsPrefix/azuredeploy.parameters.json"
```
for details, refer to https://github.com/Azure/container-service-for-azure-china/tree/master/aks-engine

 - use service principal to create kubernetes cluster by AKS
```
CLUSTER_NAME=<cluster-name>
az aks create -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --node-count 1 --disable-rbac --generate-ssh-keys --kubernetes-version 1.12.5
```
for details, refer to https://github.com/andyzhangx/demo/tree/master/aks
