# Deploy kubernetes cluster on mooncake
> Note: with acs-engine v0.14.0 or above, soveriegn cloud is supported directly, it's not necessary to modify `azuredeploy.parameters.json` template after generation any more, acs-engine will generate soveriegn cloud templates according to `location` field in cluster defination file, see [example](https://github.com/andyzhangx/demo/blob/master/acs-engine/mooncake/kubernetes-1.7.9.json#L3)

### download acs-engine binary
```
wget https://mirror.kaiyuanshe.org/kubernetes/acs-engine/v0.14.0/acs-engine-v0.14.0-linux-amd64.tar.gz
tar -xvzf acs-engine-v0.14.0-linux-amd64.tar.gz
```

### download acs-engine cluster defination file and edit
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/mooncake/kubernetes-1.7.9.json
vi kubernetes-1.7.9.json
```
> specify `location` as `chinaeast` or `chinanorth` in cluster defination file

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
#### Tips
 - [docker registry proxy cache](http://mirror.kaiyuanshe.cn/help/docker-registry-proxy-cache.html): `dockerhub.akscn.io`
 - [GCR Proxy Cache](http://mirror.kaiyuanshe.cn/help/gcr-proxy-cache.html): `gcr.akscn.io`

#### Known issues
 - [Azure disk on Sovereign Cloud](https://github.com/kubernetes/kubernetes/pull/50673) is supported from v1.7.9, v1.8.3
 - [Azure file on Sovereign Cloud](https://github.com/kubernetes/kubernetes/pull/48460) is supported from v1.7.11, v1.8.0

#### Links
[acs-engine input file example](https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/mooncake/kubernetes-1.7.9.json)

For detailed steps, you could refer to https://github.com/Azure/devops-sample-solution-for-azure-china/blob/master-dev/acs-engine/README.md
