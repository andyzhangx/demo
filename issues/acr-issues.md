## ACR(Azure Container Registry) related issues

### 1. pull image error after granting sp access to Azure Container Registry
**Fix**
 - PR [fix acr could not be listed in sp issue](https://github.com/kubernetes/kubernetes/pull/66429)
> Note that this PR would also enable feature: pull image failed from a cross-subscription Azure Container Registry by **service principal**

| k8s version | fixed version |
| ---- | ---- |
| v1.7 | no fix |
| v1.8 | no fix |
| v1.9 | 1.9.11 |
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
 - [pull image from a cross-subscription azure container registry does not work by MSI](https://github.com/kubernetes/kubernetes/issues/67892)

## 2. image pull error from ACR anonymous repository

**Issue details**:

Currently we cannot pull image from ACR repo which provides anonymous image pull access since when do image pull, it will always use service principal for all ACR repos, and finally image pull will fail with error authentication. Error message would be like following:
```
 Type     Reason          Age                  From                               Message
  ----     ------          ----                 ----                               -------
  Normal   Pulling         10m (x3 over 10m)    kubelet, k8s-agentpool-34398540-1  pulling image "xxx.azurecr.io/bitnami/apache:2.4.38"
  Warning  Failed          10m (x3 over 10m)    kubelet, k8s-agentpool-34398540-1  Failed to pull image "xxx.azurecr.io/bitnami/apache:2.4.38": rpc error: code = Unknown desc = Error response from daemon: Get https://xxx.azurecr.io/v2/bitnami/apache/manifests/2.4.38: unauthorized: authentication required
```


**Related issues**

- [cannot access Azure Container Registry public repo](https://github.com/kubernetes/kubernetes/issues/74714)

**Fix**

PR [fix Azure Container Registry anonymous repo image pull error](https://github.com/kubernetes/kubernetes/pull/74715) fixed this issue by allowing * .azurecr. * with two secrets: 1. service principal 2. empty username & password, and if first secret failed, it will fall back to use second secret


| k8s version | fixed version |
| ---- | ---- |
| v1.10 | no fix |
| v1.11 | 1.11.9 |
| v1.12 | 1.12.7 |
| v1.13 | 1.13.5 |
| v1.14 | 1.14.0 |

**Work around**:
 - provide a secret with empty username/password, specify that secret in `spec.imagePullSecrets` according to [Pull an Image from a Private Registry](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry):
```
kubectl create secret generic emptysecret --from-literal=.dockerconfigjson='{"auths":{"marketplace.azurecr.io":{"Username":"","Password":"","Email":""}}}' --type=kubernetes.io/dockerconfigjson

kind: Pod
apiVersion: v1
metadata:
  name: apache
spec:
  containers:
  - image: marketplace.azurecr.io/bitnami/apache:2.4.38
    name: apache
  imagePullSecrets:
  - name: emptysecret
```
 
### 3. pull private ACR image error on a MSI enabled cluster

**Issue details**:
On a MSI enabled cluster, pull private ACR image does not work on k8s cluster version < 1.15

**Related issues**
- [UseManagedIdentityExtension is broken for Auth with Azure container registry](https://github.com/kubernetes/kubernetes/issues/87579)

**Fix**

PR [Fix ACR MSI cross-subscription authentication error](https://github.com/kubernetes/kubernetes/pull/77245) fixed this issue 

| k8s version | fixed version |
| ---- | ---- |
| v1.14 | no fix |
| v1.15 | 1.15.0 |
| v1.16 | 1.16.0 |

### 4. pull private ACR image failed randomly on a managed identity enabled cluster

**Issue details**:
On a MSI enabled cluster, when non-ACR docker image is pulled first, the cache credential will only cache anonymous access credential, managed identity credential won't be fetched in the next 1min until cache expired.

**Related issues**
- [Pulling Azure Container Registry image using Managed Service Identity may fail
](https://github.com/kubernetes/kubernetes/issues/92326)

**Fix**

 - PR [fix: don't use docker config cache if it's empty](https://github.com/kubernetes/kubernetes/pull/92330) partially fixed this issue(solve most of the issues)
 - Another WIP PR to fix it permanantly: [fix: pull image error with azure managed identity](https://github.com/kubernetes/kubernetes/pull/92818)

| k8s version | fixed version |
| ---- | ---- |
| v1.15 | no fix |
| v1.16 | 1.16.14 |
| v1.17 | 1.17.10 |
| v1.18 | 1.18.6 |
| v1.19 | 1.19.0 |

### 5. random authentication failure when pulling image from multiple container registries using Azure managed identity

**Issue details**:

On an Azure managed identity enabled cluster, user may hit random authentication failure when pulling images from multiple container registries simultaneously, e.g. pulling images from multiple ACRs, or pulling one image from ACR and pulling another image from dockerhub in parallel.

**Related issues**
- [Pulling Azure Container Registry image using Managed Service Identity may fail](https://github.com/kubernetes/kubernetes/issues/92326)
- [ACR Image Pull Errors](https://github.com/Azure/acr/issues/451)

**Fix**

 - PR [fix pull image error from multiple ACRs using azure managed identityy](https://github.com/kubernetes/kubernetes/pull/96355)

| k8s version | fixed version |
| ---- | ---- |
| v1.16 | no fix |
| v1.17 | 1.17.14 |
| v1.18 | 1.18.12 |
| v1.19 | 1.19.4 |
| v1.20 | 1.20.0 |

**Work around**:
wait for a few more tries or using single container registry

### Tips
#### How to check whether current service principal could access ACR?

 - Use following command to check whether the target ACR is listed
```
az login --service-principal -u <aadClientId> -p <aadClientSecret> -t <tenantId>
az acr list
```

 - How to get the service principal inside an AKS cluster
 ```
 az aks show -n <ASK-CLUSTER-NAME> -g <RESOURCE_GROUP_NAME> | grep clientId
 ```
 > Make sure this service principal could access your ACR, you could set from azure portal "Container Registry"\"Access Control"\"Add Role Assignment", input the `clientId` value and add as `Reader` role

#### Code
 - [kubelet pull image](https://github.com/kubernetes/kubernetes/blob/49c50720e4e36f8b6d736feadb926b6dfa8421e6/pkg/kubelet/kuberuntime/kuberuntime_image.go#L59)
