## throubleshoot ACR connection issue on specific AKS node

 - download `canipull.yaml` and edit `ACRNAME`, `NODE-NAME` in the config
```console
wget https://raw.githubusercontent.com/andyzhangx/demo/master/aks/canipull/canipull.yaml
```

 - run `canipull` pod
```console
kubectl apply -f canipull.yaml
```

 - get `canipull` logs
> if `Validating image pull permission: FAILED`, then there is permission issue with the agent node identity.
```console
kubectl logs pod/canipull
```

<details>
<summary> succeeded case </summary>
 
```
[2022-05-12T07:14:43Z] Checking host name resolution (andyacr2.azurecr.io): SUCCEEDED
[2022-05-12T07:14:43Z] Canonical name for ACR (andyacr2.azurecr.io): r0419wus2.westus2.cloudapp.azure.com.
[2022-05-12T07:14:43Z] ACR location: westus2
[2022-05-12T07:14:43Z] Loading azure.json file from /etc/kubernetes/azure.json
[2022-05-12T07:14:43Z] Checking ACR location matches cluster location: FAILED
[2022-05-12T07:14:43Z] ACR location 'westus2' does not match your cluster location 'centraluseuap'. This may result in slow image pulls and extra cost.
[2022-05-12T07:14:43Z] Checking managed identity...
[2022-05-12T07:14:43Z] Cluster cloud name: AzurePublicCloud
[2022-05-12T07:14:43Z] Kubelet managed identity client ID: xxx
[2022-05-12T07:14:43Z] Validating managed identity existance: SUCCEEDED
[2022-05-12T07:14:44Z] Validating image pull permission: SUCCEEDED
[2022-05-12T07:14:44Z]
Your cluster can pull images from andyacr2.azurecr.io!
```

</details>

<details>
<summary> failed case </summary>
 
```
[2022-05-11T02:22:28Z] Checking host name resolution (ACRNAME.azurecr.io): SUCCEEDED
[2022-05-11T02:22:28Z] Canonical name for ACR (ACRNAME.azurecr.io): r0419eus.eastus.cloudapp.azure.com.
[2022-05-11T02:22:28Z] ACR location: eastus
[2022-05-11T02:22:28Z] Loading azure.json file from /etc/kubernetes/azure.json
[2022-05-11T02:22:28Z] Checking ACR location matches cluster location: FAILED
[2022-05-11T02:22:28Z] ACR location 'eastus' does not match your cluster location 'centraluseuap'. This may result in slow image pulls and extra cost.
[2022-05-11T02:22:28Z] Checking managed identity...
[2022-05-11T02:22:28Z] Cluster cloud name: AzurePublicCloud
[2022-05-11T02:22:28Z] Kubelet managed identity client ID: xxx
[2022-05-11T02:22:28Z] Validating managed identity existance: SUCCEEDED
[2022-05-11T02:22:28Z] Validating image pull permission: FAILED
[2022-05-11T02:22:28Z] ACR ACRNAME.azurecr.io rejected token exchange: ACR token exchange endpoint returned error status: 403. body:
```

</details>

 - if canipull log shows `Validating image pull permission: SUCCEEDED`, get ACR password and then pull ACR image on the agent node directly
 ```console
apt install docker.io -y
docker login acrname.azurecr.io -u acrname -p password
docker pull acrname.azurecr.io/image:version
 ```
