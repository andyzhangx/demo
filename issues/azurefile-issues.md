# azure file plugin known issues
### 1. azure file file/dir mode setting issue
**Issue details**:

`fileMode`, `dirMode` value would be different in different versions, to set a different value, follow this [mount options support of azure file](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/azurefile-mountoptions.md) (available from v1.8.5). For version v1.8.0-v1.8.4, since [mount options support of azure file](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/azurefile-mountoptions.md) is not available, as a workaround, specify a [securityContext](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) for the container with: `runAsUser: 0`, here is an [example](https://github.com/andyzhangx/Demo/blob/master/linux/azurefile/demo-azurefile-securitycontext.yaml)

| version | `fileMode`, `dirMode` value |
| ---- | ---- |
| v1.6.x, v1.7.x | 0777 |
| v1.8.0-v1.8.5 | 0700 |
| v1.8.6 or above | 0755 |
| v1.9.0 | 0700 |
| v1.9.1 or above | 0755 |

### 2. permission issue of azure file dynamic provision in acs-engine
**Issue details**:

From acs-engine v0.12.0, RBAC is enabled, azure file dynamic provision does not work from this version

**error logs**:
```
Events:
  Type     Reason              Age   From                         Message
  ----     ------              ----  ----                         -------
  Warning  ProvisioningFailed  8s    persistentvolume-controller  Failed to provision volume with StorageClass "azurefile": Couldn't create secret secrets is forbidden: User "system:serviceaccount:kube-syste
m:persistent-volume-binder" cannot create secrets in the namespace "default"
  Warning  ProvisioningFailed  8s    persistentvolume-controller  Failed to provision volume with StorageClass "azurefile": failed to find a matching storage account
```

**Related issues**
 - [azure file PVC need secrets create permission for persistent-volume-binder](https://github.com/kubernetes/kubernetes/issues/59543)

**Workaround**:
 - Add a ClusterRole and ClusterRoleBinding for [azure file dynamic privision](https://github.com/andyzhangx/Demo/tree/master/linux/azurefile#dynamic-provisioning-for-azure-file-in-linux-support-from-v170)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/acs-engine/rbac/azure-cloud-provider-deployment.yaml
```

**Fix**
 - PR in acs-engine: [fix azure file dynamic provision permission issue](https://github.com/Azure/acs-engine/pull/2238)
 
### 3. Azure file support on Sovereign Cloud
[Azure file on Sovereign Cloud](https://github.com/kubernetes/kubernetes/pull/48460) is supported from v1.7.11, v1.8.0

### 4. azure file dynamic provision failed due to cluster name length issue
**Issue details**:

There is a [bug](https://github.com/kubernetes/kubernetes/pull/48326) of azure file dynamic provision in [v1.7.0, v1.7.10] (fixed in v1.7.11, v1.8.0): cluster name length must be less than 16 characters, otherwise following error will be received when creating dynamic privisioning azure file pvc:
```
persistentvolume-controller    Warning    ProvisioningFailed Failed to provision volume with StorageClass "azurefile": failed to find a matching storage account
```

### 5. azure file dynamic provision failed due to no storage account in current resource group
**Issue details**:

**Related issues**

**Workaround**:

**Fix**

### 6. azure file plugin on Windows does not work after node restart
**Issue details**:
azure file plugin on Windows does not work after node restart, this is due to `New-SmbGlobalMapping` cmdlet has lost account name/key after reboot

**Related issues**
 - [azure file plugin on Windows does not work after node restart](https://github.com/kubernetes/kubernetes/issues/60624)

**Workaround**:
 - delete the original pod with azure file mount
 - create the pod again

**Fix**
 - PR [fix azure file plugin failure issue on Windows after node restart](https://github.com/kubernetes/kubernetes/pull/60625)

| k8s version | fixed version |
| ---- | ---- |
| v1.7 | not support in upstream |
| v1.8 | 1.8.10 |
| v1.9 | 1.9.7 |
| v1.10 | 1.10.0 |

### 7. file permission could not be changed using azure file, e.g. postgresql
**error logs** when running postgresql on azure file plugin:
```
initdb: could not change permissions of directory "/var/lib/postgresql/data": Operation not permitted
fixing permissions on existing directory /var/lib/postgresql/data 
```

**Issue details**:
azure file plugin is using cifs/SMB protocol, file/dir permission could not be changed after mounting

**Workaround**:
Use subPath together with azure disk plugin

**Related issues**
[Persistent Volume Claim permissions](https://github.com/Azure/AKS/issues/225)

## azure network known issues
### 1. network interface failed
**Workaround**:
```
az network nic update -g RG-NAME -n NIC-NAME
```
