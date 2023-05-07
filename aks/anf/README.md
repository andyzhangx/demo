# [Azure NetApp File on AKS](https://learn.microsoft.com/en-us/azure/aks/azure-netapp-files)

### Troubleshooting
 - check whether Azure credentials are correct in backend configuration setting
```console
kubectl describe tridentbackendconfig.trident.netapp.io/backend-tbc-anf -n trident
```

### Get driver logs
 - get driver pod names on the cluster
```console
# kubectl get po -n trident -o wide
NAME                                  READY   STATUS    RESTARTS   AGE     IP             NODE                                NOMINATED NODE   READINESS GATES
trident-controller-5985b99b95-qnqq5   6/6     Running   0          4h59m   10.224.0.25    aks-agentpool-20657377-vmss000003   <none>           <none>
trident-node-linux-d2p7c              2/2     Running   0          4h59m   10.224.0.222   aks-agentpool-20657377-vmss000002   <none>           <none>
trident-node-linux-k4f77              2/2     Running   0          4h59m   10.224.0.4     aks-agentpool-20657377-vmss000003   <none>           <none>
trident-operator-86696fb84f-8q9mv     1/1     Running   0          4h59m   10.224.0.110   aks-agentpool-20657377-vmss000003   <none>           <none>
```

 - get driver controller logs
```console
# kubectl logs -n trident trident-controller-5985b99b95-qnqq5 -c trident-main > /tmp/trident-controller-5985b99b95-qnqq5
```

 - get driver node logs
```console
# kubectl logs -n trident trident-node-linux-d2p7c -c trident-main > /tmp/trident-node-linux-d2p7c
```

### common issues
#### incorrect `clientID` specified in `backend-tbc-anf-secret`

 - `clientID` in `backend-tbc-anf-secret` should be `Application (client) ID` instead of `Secret ID`, while `clientSecret` should be secret `Value`, you may get following error logs if you fill in `Secret ID` in `backend-tbc-anf-secret`, here `a3617765-1571-4086-8d66-78a15f90bc4b` is actually `Secret ID` which is wrong.

```
# kubectl describe tridentbackendconfig.trident.netapp.io/backend-tbc-anf -n trident
time="2023-05-07T02:04:03Z" level=error msg="error syncing backend configuration 'trident/backend-tbc-anf', requeuing; problem initializing storage driver 'azure-netapp-files': error initializing azure-netapp-files SDK client. ClientSecretCredential authentication failed\nPOST https://login.microsoftonline.com/72f988bf-86f1-41af-91ab-2d7cd011db47/oauth2/v2.0/token\n--------------------------------------------------------------------------------\nRESPONSE 400 Bad Request\n--------------------------------------------------------------------------------\n{\n  \"error\": \"unauthorized_client\",\n  \"error_description\": \"AADSTS700016: Application with identifier 'a3617765-1571-4086-8d66-78a15f90bc4b' was not found in the directory 'Microsoft'. This can happen if the application has not been installed by the administrator of the tenant or consented to by any user in the tenant. You may have sent your authentication request to the wrong tenant.\\r\\nTrace ID: ce932228-4ae2-4919-85d5-86ef8895d200\\r\\nCorrelation ID: f3036d1d-e861-4d96-aba5-1fe575dca460\\r\\nTimestamp: 2023-05-07 02:04:03Z\",\n  \"error_codes\": [\n    700016\n  ],\n  \"timestamp\": \"2023-05-07 02:04:03Z\",\n  \"trace_id\": \"ce932228-4ae2-4919-85d5-86ef8895d200\",\n  \"correlation_id\": \"f3036d1d-e861-4d96-aba5-1fe575dca460\",\n  \"error_uri\": \"https://login.microsoftonline.com/error?code=700016\"\n}\n--------------------------------------------------------------------------------\nTo troubleshoot, visit https://aka.ms/azsdk/go/identity/troubleshoot#client-secret; no capacity pools found for storage pool backend-tbc-anf_pool; ClientSecretCredential authentication failed\nPOST https://login.microsoftonline.com/72f988bf-86f1-41af-91ab-2d7cd011db47/oauth2/v2.0/token\n--------------------------------------------------------------------------------\nRESPONSE 400 Bad Request\n--------------------------------------------------------------------------------\n{\n  \"error\": \"unauthorized_client\",\n  \"error_description\": \"AADSTS700016: Application with identifier 'a3617765-1571-4086-8d66-78a15f90bc4b' was not found in the directory 'Microsoft'. This can happen if the application has not been installed by the administrator of the tenant or consented to by any user in the tenant. You may have sent your authentication request to the wrong tenant.\\r\\nTrace ID: 3500ed39-fe6f-4923-a892-346ff1f60d01\\r\\nCorrelation ID: 325f1e34-56cd-46f4-bb4a-7d41c90f7afe\\r\\nTimestamp: 2023-05-07 02:04:03Z\",\n  \"error_codes\": [\n    700016\n  ],\n  \"timestamp\": \"2023-05-07 02:04:03Z\",\n  \"trace_id\": \"3500ed39-fe6f-4923-a892-346ff1f60d01\",\n  \"correlation_id\": \"325f1e34-56cd-46f4-bb4a-7d41c90f7afe\",\n  \"error_uri\": \"https://login.microsoftonline.com/error?code=700016\"\n}\n--------------------------------------------------------------------------------\nTo troubleshoot, visit https://aka.ms/azsdk/go/identity/troubleshoot#client-secret" logSource=trident-crd-controller requestID=e396e0a2-056b-47c6-afef-849fd90a29ea requestSource=CRD
```

- Tips
  - [Backend configuration options](https://docs.netapp.com/us-en/trident/trident-use/anf-examples.html#backend-configuration-options)
  - [Trident on Azure driver code](https://github.com/NetApp/trident/tree/master/storage_drivers/azure)
