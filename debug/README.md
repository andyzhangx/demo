# Debugging skills for kubernetes on azure
### Q: How to change log level in k8s cluster
 - for api-server, scheduler, controller-manager:

edit yaml files under `/etc/kubernetes/manifests/`, change `--v=2` value and then run `sudo service docker restart`

 - for kubelet on Linux agent:

edit yaml file under `/etc/systemd/system/kubelet.service`, change `--v=2` value and then run `sudo systemctl restart kubelet`

 - for kubelet on Windows agent:
 
edit `c:\k\kubeletstart.ps1`, check the parameter(`--v=2`) in `c:\k\kubelet.exe` command
restart `Kubelet` service
> Note:
 `--v=2` means only output log level <=2 messages, the bigger log level the more logging.

### Q: There is no k8s component container running on master, how to do troubleshooting?
run `journalctl -u kubelet` to get the kubelet related logs

### Q: How to get k8s component logs on master?
run `docker ps -a` to get all containers, if there is any stopped container, using following command to get that container logs.
`docker ps CONTAINER-ID > CONTAINER-ID.log 2>&1 &`

##### Q: Get controller manager logs on master
 - Option#1:
```
kubectl logs `kubectl get po --all-namespaces | grep controller-manager | cut -d ' ' -f4` --namespace=kube-system >> controller-manager.log
```

 - Option#2:
1. get the "CONTAINER ID" of "/hyperkube controlle"
```
docker ps -a | grep "hyperkube controlle" | awk -F ' ' '{print $1}'
```
2. get controller manager logs
```
docker logs "CONTAINER ID" > "CONTAINER ID".log 2>&1 &
```
Or use below command lines directly:
```
id=`docker ps -a | grep "hyperkube controlle" | awk -F ' ' '{print $1}'`
docker logs $id > $id.log 2>&1
vi $id.log
```

### Q: How to get k8s kubelet logs on linux agent?
Prerequisite:
[assign a public ip to the agent in azure portal](https://github.com/andyzhangx/Demo/blob/master/debug/README.md#assign-a-public-ip-to-a-vm-in-azure-portal) and use ssh client to connect to that agent. (only for debugging purpose)
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

### Q: How to get k8s kubelet logs on Windows agent?
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
$url = "https://mirror.kaiyuanshe.org/putty/0.70/w64/pscp.exe"
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
and then run `sudo service docker restart`

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

### Provide ssh access
 - option#1: To assign a public IP adress to one VM on Azure portal, click under network\network interface\ip config\enable public IP address
 - option#2: follow [SSH into Azure Container Service (AKS) cluster nodes](https://docs.microsoft.com/en-us/azure/aks/aks-ssh)

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
