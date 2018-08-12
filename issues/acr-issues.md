# ACR(Azure Container Registry) related issues

## Cross subscription access from ACR
**Fix**
 - PR [fix acr could not be listed in sp issue](https://github.com/kubernetes/kubernetes/pull/66429)

| k8s version | fixed version |
| ---- | ---- |
| v1.7 | no fix |
| v1.8 | no fix |
| v1.9 | in cherry-pick |
| v1.10 | 1.10.7 |
| v1.11 | 1.11.2 |
| v1.12 | 1.12.0 |

**Related issues**


### Tips
#### How to check whether current service principal could access ACR?

```
az login --service-principal -u <aadClientId> -p <aadClientSecret> -t <tenantId>
az acr list
```
