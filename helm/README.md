# helm on azure examples

### helm pod scale up issue
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
