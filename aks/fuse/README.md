### check all statfs calls on fuse file system on Linux node

```console
wget https://raw.githubusercontent.com/andyzhangx/demo/master/aks/fuse/statfs_count.bt
bpftrace statfs_count.bt
Counting vfs_statfs for cifs... Hit Ctrl-C to end.

Top 10 vfs_statfs process:
@counter[20748, telegraf]: 28
@counter[14652, node-exporter]: 35
```

