# helm on azure examples

### helm pod scale up issue
**Issue details**

you may get following error when you try to scale up a helm deployment:
```
Events:
  FirstSeen     LastSeen        Count   From                                    SubObjectPath   Type            Reason                  Message
  ---------     --------        -----   ----                                    -------------   --------        ------                  -------
  4m            4m              1       default-scheduler                                       Normal          Scheduled               Successfully assigned edgy-eel-mariadb-3171167167-lpk44 to aks-agentpool-14759709-2
  4m            4m              1       kubelet, aks-agentpool-14759709-2                       Normal          SuccessfulMountVolume   MountVolume.SetUp succeeded for volume "config"
  4m            4m              1       kubelet, aks-agentpool-14759709-2                       Normal          SuccessfulMountVolume   MountVolume.SetUp succeeded for volume "default-token-f84dx"
  2m            14s             2       kubelet, aks-agentpool-14759709-2                       Warning         FailedMount             Unable to mount volumes for pod "edgy-eel-mariadb-3171167167-lpk44_default(4c6073aa-d020-11e7-b699-0a58ac1f1049)": timeout expired waiting for volumes to attach/mount for pod "default"/"edgy-eel-mariadb-3171167167-lpk44". list of unattached/unmounted volumes=[data]
  2m            14s             2       kubelet, aks-agentpool-14759709-2                       Warning         FailedSync              Error syncing pod
  4m            0s              2604    attachdetach                                            Warning         FailedAttachVolume      Multi-Attach error for volume "pvc-c66fbef0-d01e-11e7-b699-0a58ac1f1049" Volume is already exclusively attached to one node and can't be attached to another
```

That's because azure disk is ReadWriteOnce(RWO) access mode, it could only attach to a node, so in the scale up process, if second pod is created in another node. 

**Workaround**

Use azurefile storage class instead, it supports ReadWriteMany(RWX) access mode. Before running following command, make sure a storage account already exists in the resourse group as k8s cluster.
```
helm install --set persistence.accessMode=ReadWriteMany,persistence.storageClass=azurefile stable/wordpress
```

### Helm incompatible versions issue
```
$ helm install --set persistence.accessMode=ReadWriteOnce stable/wordpress
Error: incompatible versions client[v2.8.2] server[v2.6.2]
```

**Workaround**
 - Get server version first
```
$ helm version
Client: &version.Version{SemVer:"v2.8.2", GitCommit:"a80231648a1473929271764b920a8e346f6de844", GitTreeState:"clean"}
Server: &version.Version{SemVer:"v2.6.2", GitCommit:"be3ae4ea91b2960be98c07e8f73754e67e87963c", GitTreeState:"clean"}
```
 - Reinstall helm client version, make it identical to server version
```
curl https://raw.githubusercontent.com/kubernetes/helm/master/scripts/get > get_helm.sh
chmod 700 get_helm.sh
./get_helm.sh --version v2.6.2
helm init
```

#### Links
[helm installation guide](https://github.com/kubernetes/helm/blob/master/docs/install.md)

[Mooncake installation guide](http://mirror.kaiyuanshe.cn/help/kubernetes.html)
