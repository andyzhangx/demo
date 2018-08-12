# ACR(Azure Container Registry) related issues

## pull image error after granting sp access to azure acr
**Fix**
 - PR [fix acr could not be listed in sp issue](https://github.com/kubernetes/kubernetes/pull/66429)
> Note that this PR would also enable feature: pull image from a cross subscription ACR

| k8s version | fixed version |
| ---- | ---- |
| v1.7 | no fix |
| v1.8 | no fix |
| v1.9 | in cherry-pick |
| v1.10 | 1.10.7 |
| v1.11 | 1.11.2 |
| v1.12 | 1.12.0 |

**workaround**
 - wait for at most 2 hours, let service principal token expires and pull image would succeed after a few tries automatically
 - restart `kubelet` service on the agent node

**Related issues**
 - [kubelet needs restart after granting sp access to azure acr](https://github.com/kubernetes/kubernetes/issues/65225)
 - [Kubelet requires restart after granting AKS SP access to ACR resource](https://github.com/Azure/AKS/issues/442)
 - [Unable to pull images from ACR: Error response from daemon](https://github.com/Azure/acs-engine/issues/3654)

### Tips
#### How to check whether current service principal could access ACR?

 - Use following command to check whether the target ACR is listed
```
az login --service-principal -u <aadClientId> -p <aadClientSecret> -t <tenantId>
az acr list
```
