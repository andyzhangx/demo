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
```console
# kubectl logs pod/canipull
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
