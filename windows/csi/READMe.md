## upgrade csi-proxy version on AKS windows node

ssh to the windows node, and then run following command to upgrade csi-proxy binary, since stop csi-proxy service would also stop other dependency service, the agent node would be in NotReady state after the highlighted operation, and then you could restart that windows node manually, after a few minutes, v1.0.2 csi-proxy version would be started, and then you could continue your test. 
And about how to ssh to the windows node, you could:
```
1) update the windows admin password by running “az aks update -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --windows-admin-password xxx” command 
2) kubectl exec -it ama-logs-windows-n8p4c -n kube-system -- cmd 
3) ssh azureuser@windows-node-internal-ip
```

-	Update csi-proxy binary operations
```
Microsoft Windows [Version 10.0.20348.1006]
(c) Microsoft Corporation. All rights reserved.
C:\opt\amalogswindows\scripts\powershell>powershell

cd c:\tmp
$webclient = New-Object System.Net.WebClient
$url = https://acs-mirror.azureedge.net/csi-proxy/v1.0.2/binaries/csi-proxy-v1.0.2.tar.gz
$file = " $pwd\csi-proxy-v1.0.2.tar.gz"
$webclient.DownloadFile($url,$file)
tar.exe -x -f .\csi-proxy-v1.0.2.tar.gz
dir c:\tmp\bin\csi-proxy.exe


Get-Service csi-proxy
Stop-Service csi-proxy -Force;cp c:\tmp\bin\csi-proxy.exe c:\k\csi-proxy.exe

type c:\k\csi-proxy.err.log
I0113 14:06:31.377898    3684 main.go:54] Starting CSI-Proxy Server ...
I0113 14:06:31.411205    3684 main.go:55] Version: v1.0.2-0-g51a6f06
```
