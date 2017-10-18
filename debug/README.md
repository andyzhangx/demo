# Debugging skills for kubernetes on azure
### Q: How to change log level in k8s cluster
#### On master
edit yaml files under `/etc/kubernetes/manifests/`, change `--v=2` value and then run `sudo service docker restart`
#### On Linux agent

#### On Windows agent
edit `c:\k\kubeletstart.ps1`, check the parameter(`--v=2`) in `c:\k\kubelet.exe` command
restart `Kubelet` service

### Q: There is no k8s component container running on master, how to do troubleshooting?
run `journalctl -u kubelet` to get the kubelet related logs


### Q: How to get the k8s component logs on master?
run `docker ps -a` to get all containers, if there is any stopped container, using following command to get that container logs.
`docker ps CONTAINER-ID > CONTAINER-ID.log 2>&1 &`

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
And then follow below guide to set the default class:
https://kubernetes.io/docs/tasks/administer-cluster/change-default-storage-class/
