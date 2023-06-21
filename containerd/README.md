# containerd tips
 - set `image_pull_progress_timeout` in containerd config file

 `vi /etc/containerd/config.toml`
 
append below line after sandbox_image = "mcr.microsoft.com/oss/kubernetes/pause:3.6"
```
  image_pull_progress_timeout = "5m0s"
```

and then
```console
# systemctl restart containerd
# crictl info | grep -i timeout
    "streamIdleTimeout": "4h0m0s",
    "imagePullProgressTimeout": "5m0s",
    "drainExecSyncIOTimeout": "0s",
```

 - get containerd logs
```
journalctl -u containerd > /tmp/containerd.log
```


 - other command
```
ctr -n k8s.io image pull
```
