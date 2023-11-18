### check all statfs calls on nfs file system on Linux node
 - run following command to collect statfs calls on nfs file system on Linux node for 3 minutes
 > following example out shows nfs statfs calls from azurefileplugin, du, df, etc.
```console
root@aks-agentpool-18739669-vmss00000N:/# wget https://raw.githubusercontent.com/andyzhangx/demo/master/aks/nfs_statfs_count.bt
root@aks-agentpool-18739669-vmss00000N:/# bpftrace nfs_statfs_count.bt
Attaching 4 probes...
Counting nfs_statfs for nfs... Hit Ctrl-C to end.

@counter[du]: 1
@counter[azurefileplugin]: 2
@counter[df]: 6

@counter[azurefileplugin]: 2
@counter[du]: 3
@counter[df]: 9

@counter[azurefileplugin]: 2
@counter[du]: 3
@counter[df]: 9
```
