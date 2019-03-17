# known k8s on azure issues and fixes

## [azure disk plugin known issues](./azuredisk-issues.md)

## [azure file plugin known issues](./azurefile-issues.md)

## [azure network known issues](./network-issues.md)

## Other issues
### 1. `GET/VirtualMachine` has too many ARM api calls
**Issue details**:
There could be ARM api throttling due to too many ARM api calls in a time period.

**error logs**:
```
"OperationNotAllowed",\r\n    "message": "The server rejected the request because too many requests have been received for this subscription.
```

**Workaround**:
 - Make sure that instance metadata is used. (set true in azure.json) on all nodes (require restarting kubelet+ all master roles on masters and kubelet on nodes).
 - There is a large # of put against ROUTES, was that a multiple scale events, or multiple cluster creation? If that is not the case or they operate large # of clusters in the same subscription then increase "--route-reconciliation-period" on controller-manager (require restart of controller manager). 

**Fix**
 - we have used cache in GET/VirtualMachine in v1.9.2: [Add cache for VirtualMachinesClient.Get in azure cloud provider](https://github.com/kubernetes/kubernetes/pull/57432)

| k8s version | fixed version |
| ---- | ---- |
| v1.9 | 1.9.2 |
| v1.10 | 1.10.0 |

### 2. `azure-cli` failed to create aks cluster
failed with following error:
```
The password must contain at least 1 special character. paramName: PasswordCredentials, paramValue: , objectType: Microsoft.Online.DirectoryServices.Application
```

**Fix**

[update SP secret to include special characters for aad](https://github.com/Azure/azure-cli/pull/8741)

**Workaround**:
```sh
docker run -v ${HOME}:/root -it andyzhangx/azure-cli:2.0.60-aad
```

