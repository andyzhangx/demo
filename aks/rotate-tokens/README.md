# How to rotate AKS cluster tokens

### Prerequisite
 - install [azure cli extension](https://docs.microsoft.com/en-us/cli/azure/azure-cli-extensions-overview?view=azure-cli-latest)

```console
az extension remove --name aks-preview
az extension add --source https://raw.githubusercontent.com/andyzhangx/demo/master/aks/rotate-tokens/aks_preview-0.5.0-py2.py3-none-any.whl -y
```

### rotate AKS cluster tokens
```console
RESOURCE_GROUP_NAME=
CLUSTER_NAME=
az aks rotate-cluster-tokens -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME
```
