# Deploy kubernetes cluster on Azure China
### 1. download acs-engine binary
```
acs_version=v0.26.3
wget https://mirror.azure.cn/kubernetes/acs-engine/$acs_version/acs-engine-$acs_version-linux-amd64.tar.gz
tar -xvzf acs-engine-$acs_version-linux-amd64.tar.gz
```

### 2. download acs-engine cluster defination file and edit fields, e.g. `location`, `orchestratorVersion`, `dnsPrefix`, `linuxProfile`, `servicePrincipalProfile` etc.
```
k8s_version=1.10.7
wget -O kubernetes-$k8s_version.json https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/mooncake/kubernetes-1.10.7.json
vi kubernetes-$k8s_version.json
```
> specify `location` as (`chinaeast`, `chinanorth`, `chinaeast2`, `chinanorth2`) in cluster defination file

### 3. generate ARM templates by acs-engine
```
./acs-engine generate kubernetes-$k8s_version.json
```

### 4. create kubernetes cluster by ARM templates
```
# create a resource group first
RESOURCE_GROUP_NAME=andy-k8s1107
REGION=chinaeast2
az group create -l $REGION -n $RESOURCE_GROUP_NAME

# deploy ARM template
dnsPrefix=andy-k8s1107
az group deployment create \
    --name="$dnsPrefix" \
    --resource-group=$RESOURCE_GROUP_NAME \
    --template-file="./_output/$dnsPrefix/azuredeploy.json" \
    --parameters "@./_output/$dnsPrefix/azuredeploy.parameters.json"
```

### 5. After k8s cluster creation successfully, ssh to master node by:
```
ssh azureuser@$dnsPrefix.$REGION.cloudapp.chinacloudapi.cn
```

#### [Container Registry Proxy in Azure China](https://github.com/Azure/container-service-for-azure-china/tree/master/aks#22-container-registry-proxy)

#### Known issues
 - [Azure disk on Sovereign Cloud](https://github.com/kubernetes/kubernetes/pull/50673) is supported from v1.7.9, v1.8.3
 - [Azure file on Sovereign Cloud](https://github.com/kubernetes/kubernetes/pull/48460) is supported from v1.7.11, v1.8.0
 
#### Related issues
 - [Unable to create Load balancer service in Azure Government](https://github.com/Azure/acs-engine/issues/3754)
 - [Generate Templates with `acs-engine` with location `chinaeast2` failed](https://github.com/Azure/acs-engine/issues/3812)
 - [Cannot deploy generated ARM template to AzureChinaCloud](https://github.com/Azure/acs-engine/issues/3024)
 - [ip-masq-agent daemonset does not work in AzureChinaCloud](https://github.com/Azure/acs-engine/issues/4063)
 - [Can we increase the timeout for docker pull](https://github.com/Azure/acs-engine/issues/4126) 
 
#### Related PRs
 - [use dockerhub.azk8s.cn in mooncake](https://github.com/Azure/acs-engine/pull/3887)
 - [container registry proxy change for azure china cloud](https://github.com/Azure/acs-engine/pull/3683)
 - [change docker-engine to docker-ce for mooncake](https://github.com/Azure/azure-docker-extension/pull/132)
 - [use china mirror in binary downloading on azure china](https://github.com/Azure/acs-engine/pull/4137)
 - [use gcr.azk8s.cn for all add-on configs on Azure China](https://github.com/Azure/acs-engine/pull/4190)

#### Links
 - [acs-engine input file example](https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/mooncake/kubernetes-1.10.7.json)
 > For detailed steps, refer to https://github.com/Azure/devops-sample-solution-for-azure-china/blob/master-dev/acs-engine/
 - [Kubernetes on Azure Government](https://docs.microsoft.com/en-us/azure/azure-government/documentation-government-k8)
