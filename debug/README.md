# Debugging skills for kubernetes on azure
### Q: How to change log level in k8s cluster
 - for api-server, scheduler, controller-manager:

edit yaml files under `/etc/kubernetes/manifests/`, change `--v=2`(e.g. change to --v=12) value and then run `sudo service docker restart`

 - for kubelet on Linux agent:

edit yaml file under `/etc/systemd/system/kubelet.service`, change `--v=2` value(e.g. change to `--v=12`) and then run 
```
sudo vi /etc/systemd/system/kubelet.service
#edit 
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

 - for kubelet on Windows agent:
 
edit `c:\k\kubeletstart.ps1`, check the parameter(`--v=2`) in `c:\k\kubelet.exe` command, and then restart `kubelet` service
```
notepad c:\k\kubeletstart.ps1
#edit
stop-service kubeproxy
stop-service kubelet
start-service kubeproxy
start-service kubelet
```

> Note:
 `--v=2` means only output log level <=2 messages, the bigger log level the more logging.

### Q: There is no k8s component container running on master, how to do troubleshooting?
run `journalctl -u kubelet` to get the kubelet related logs

refer to [details](https://learn.microsoft.com/en-us/azure/aks/kubelet-logs)

### Q: How to get k8s component logs on master?
run `docker ps -a` to get all containers, if there is any stopped container, using following command to get that container logs.
`docker ps CONTAINER-ID > CONTAINER-ID.log 2>&1 &`

##### Q: Get controller manager logs on master
 - Option#1:
```
kubectl logs `kubectl get po --all-namespaces | grep controller-manager | cut -d ' ' -f4` --namespace=kube-system > controller-manager.log
```

 - Option#2:
1. get the "CONTAINER ID" of "/hyperkube controlle"
```
docker ps | grep "hyperkube contro" | awk -F ' ' '{print $1}'
```
2. get controller manager logs
```
docker logs "CONTAINER ID" > "CONTAINER ID".log 2>&1 &
```
Or use below command lines directly:
```
id=`docker ps | grep "hyperkube contro" | awk -F ' ' '{print $1}'`
docker logs $id > $id.log 2>&1
vi $id.log
```

### Q: How to get k8s kubelet logs on linux agent node?
Prerequisite:
[assign a public ip to the agent in azure portal](https://github.com/andyzhangx/Demo/blob/master/debug/README.md#assign-a-public-ip-to-a-vm-in-azure-portal) and use ssh client to connect to that agent. (only for debugging purpose)

> Note: from acs-engine [v0.16.0](https://github.com/Azure/acs-engine/releases/tag/v0.16.0) and AKS, `kubelet` is not containerized. [Check whether kubelet is containerized or running as native daemon](https://github.com/andyzhangx/demo/blob/master/debug/README.md#q-check-whether-kubelet-is-containerized-or-running-as-native-daemon)

 - for kubelet running as a native daemon
```
sudo journalctl -u kubelet -l > kubelet.log
```

 - for containerized kubelet
1. get the "CONTAINER ID" of "/hyperkube kubelet"
```
docker ps -a | grep "hyperkube kubele" | awk -F ' ' '{print $1}'
```
2. get kubelet logs
```
docker logs "CONTAINER ID" > "CONTAINER ID".log 2>&1 &
```
Or use below command lines directly:
```
id=`docker ps -a | grep "hyperkube kubele" | awk -F ' ' '{print $1}'`
docker logs $id > $id.log 2>&1
vi $id.log
```



### Q: How to get k8s kubelet logs on Windows agent node?
- option#1
```console
kubectl exec -it csi-azuredisk-node-win-x9md5 -n kube-system -c azuredisk -- cmd
C:\>dir c:\k
08/04/2022  09:16 AM        10,485,566 kubelet.err-20220804T091606.948.log
08/06/2022  10:54 AM        10,485,592 kubelet.err-20220806T105439.978.log
kubectl cp csi-azuredisk-node-win-x9md5:/k/kubelet.err-20220804T091606.948.log /tmp/kubelet.err-20220804T091606.948.log -n kube-system -c azuredisk
```

- option#2

Prerequisite:
[assign a public ip to the agent in azure portal](https://github.com/andyzhangx/Demo/blob/master/debug/README.md#assign-a-public-ip-to-a-vm-in-azure-portal) and use RDP to connect to that agent. (only for debugging purpose)

1. open a powershell window
```
start powershell
```
2. download pscp.exe tool
```
cd c:\k
$webclient = New-Object System.Net.WebClient
$url = "https://mirror.azure.cn/putty/0.70/w64/pscp.exe"
$file = " $pwd\pscp.exe"
$webclient.DownloadFile($url,$file)
```
3. replace with your linux machine IP, password and then scp `c:\k\kubelet.err.log.copy` to your linux machine
```
cp c:\k\kubelet.err.log c:\k\kubelet.err.log.copy
Start-Process "$pwd\pscp.exe"  -ArgumentList ("-scp -pw PASSWROD c:\k\kubelet.err.log.copy azureuser@SERVER-IP:/tmp")
```

### Q: How to change k8s hyperkube image?
`sudo vi /etc/default/kubelet`
change `KUBELET_IMAGE` value, default value is `gcrio.azureedge.net/google_containers/hyperkube-amd64:1.x.x`
and then run:
```
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

### Q: Pod could not be scheduled to a windows node
1. make sure node is marked as `windows` label, run below command to check
`kubectl get nodes --show-labels`
use below command to label `windows` on the windows node:
```kubectl label nodes <node-name> beta.kubernetes.io/os=windows --overwrite```

2. `nodeSelector` should be specified in the pod configuration, e.g.
```
  nodeSelector:
    beta.kubernetes.io/os: windows
```

### Q: How to set default storage class in kubernetes on azure?
first edit below file, set the `default` class as false:
```
sudo vi /etc/kubernetes/addons/azure-storage-classes.yaml
```
And then follow this [guide](https://kubernetes.io/docs/tasks/administer-cluster/change-default-storage-class/) to set the default class:

### Q: How to delete the pod by force?
```kubectl delete pod PODNAME --grace-period=0 --force```

#### Q: Check whether `kubelet` is containerized or running as native daemon
 - Run following command on node, if there is no output, then `kubelet` is running as native daemon, otherwise it's a containerized kubelet
```
docker ps | grep kubel
```
 - You may also check `kubelet.service` file, if `kubelet` binary is under `ExecStart=/usr/local/bin/kubelet` then `kubelet` is running as native daemon
```
sudo vi /etc/systemd/system/kubelet.service
```

### Assign a Public IP to a VM in Azure portal
Click under network\network interface\ip config\enable public IP address
 > Note: For Linux node, where is k8s way, follow [SSH into Azure Container Service (AKS) cluster nodes](https://docs.microsoft.com/en-us/azure/aks/aks-ssh)

## Advanced skills
### Q: How to open feature gate in kubernetes on azure?
Take [Growing Persistent Volume size](https://github.com/kubernetes/community/blob/master/contributors/design-proposals/storage/grow-volume-size.md) as an example:

Append `"--feature-gates=ExpandPersistentVolumes=true"` into apiserver, scheduler and controller-manager parameters
```
sudo vi /etc/kubernetes/manifests/kube-apiserver.yaml
sudo vi /etc/kubernetes/manifests/kube-scheduler.yaml
sudo vi /etc/kubernetes/manifests/kube-controller-manager.yaml
```

Also modify kubelet `KUBELET_FEATURE_GATES` values
```
sudo vi /etc/default/kubelet
KUBELET_FEATURE_GATES=--feature-gates=ExpandPersistentVolumes=true
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```
