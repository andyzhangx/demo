## azure file account key rotating procedure
Changing storage account key after creating azure file pvc would make pod mounting with pvc failed, while some users still need to change the storage account key periodically for security reason, below are the details how to make azure file mount work after account key changed:

The k8s secret is created right after azure file pvc is created and then k8s will use that secret in the azure file mounting process. 
 - How to get that secret?
```
kubectl get secret
kubectl get secret azure-storage-account-...secret -o yaml
# get account name & key by base64 decoding, e.g.
echo Zjk1OWNlY2M5ZWU1ZDExZTg4YzkxNmU= | base64 -d
```
 - Below are the correct way for rotating account key:
1.	Before new pod mount with azure file, rotate the “azurestorageaccountkey” value in k8s secret with base64 encoded (`echo <ACCONT-KEY> | base64`)
```
kubectl edit secret azure-storage-account-...secret
```
2.	Old pod with azure file mount should always work since it’s already mounted there, and new pod will use the new account key from the secret.

We use k8s secret to store account name & key in azure file plugin, and in the new azure file CSI driver, we will retrieve the account key when mount azure file, so it won’t have that issue.

**Related issues**

- [Azure file mount permission denied](https://github.com/Azure/AKS/issues/714)
