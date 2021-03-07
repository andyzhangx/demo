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

### rotate control plane certs on an AKS cluster
```console
RESOURCE_GROUP_NAME=
CLUSTER_NAME=
az aks reconcile-control-plane-certs -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME
```

#### Notes
- [commit: rotate cluster tokens](https://github.com/andyzhangx/azure-cli-extensions/commit/be645a7406fdc66772845f160d04d44db927119a)
