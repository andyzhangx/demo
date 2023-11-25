### check all statfs calls on cifs file system on Linux node
 - run following command to collect statefs calls on cifs file system on Linux node for 3 minutes
 > following example out shows Azure File CSI driver(azurefileplugin) calls 200+ statfs every minute
```console
root@aks-agentpool-18739669-vmss00000N:/# wget https://raw.githubusercontent.com/andyzhangx/demo/master/aks/cifs_statfs_count.bt
root@aks-agentpool-18739669-vmss00000N:/# bpftrace cifs_statfs_count.bt
Attaching 4 probes...
Counting cifs_statfs for cifs... Hit Ctrl-C to end.

@counter[azurefileplugin]: 5
@counter[azurefileplugin]: 260
@counter[azurefileplugin]: 705
```

#### Tips
 - use `bpftrace -l` to get all bpftrace probes:
```console
bpftrace -l | grep smb | grep stat
```
