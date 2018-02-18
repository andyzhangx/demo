## 1. create a secret which stores blobfuse account name and password
```
kubectl create secret generic blobfusecreds --from-literal username=USERNAME --from-literal password="PASSWORD" --type="blobfuse/blobfuse"
```

## 2. install flex volume driver on every linux agent node
```
sudo mkdir -p /etc/kubernetes/volumeplugins/blobfuse~blobfuse
cd /etc/kubernetes/volumeplugins/blobfuse~blobfuse
sudo wget https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/blobfuse
sudo chmod a+x blobfuse
```
#### Note:
Make sure `jq` package is installed on every node.

## 3. specify `volume-plugin-dir` in kubelet service config (skip this step from acs-engine v0.12.0)
```
sudo vi /etc/systemd/system/kubelet.service
  --volume=/etc/kubernetes/volumeplugins:/etc/kubernetes/volumeplugins:rw \
        --volume-plugin-dir=/etc/kubernetes/volumeplugins \
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

Note:
1. `/etc/kubernetes/volumeplugins` has already been the default flexvolume plugin directory in acs-engine (starting from v0.12.0)
2. There would be one line of [kubelet log](https://github.com/andyzhangx/Demo/tree/master/debug#q-how-to-get-k8s-kubelet-logs-on-linux-agent) like below showing that `flexvolume-blobfuse/blobfuse` is loaded correctly
```
I0122 08:24:47.761479    2963 plugins.go:469] Loaded volume plugin "flexvolume-blobfuse/blobfuse"
```

## 4. create a pod with flexvolume-blobfuse mount on linux
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/nginx-flex-blobfuse.yaml

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-flexvolume-blobfuse

## 5. enter the pod container to do validation
kubectl exec -it nginx-flexvolume-blobfuse -- bash

```
root@nginx-flex-blobfuse:/# df -h
Filesystem                                 Size  Used Avail Use% Mounted on
overlay                                    291G  3.3G  288G   2% /
tmpfs                                      3.4G     0  3.4G   0% /dev
tmpfs                                      3.4G     0  3.4G   0% /sys/fs/cgroup
//andytestx.file.core.windows.net/k8stest  3.0G   16M  3.0G   1% /data
/dev/sda1                                  291G  3.3G  288G   2% /etc/hosts
shm                                         64M     0   64M   0% /dev/shm
tmpfs                                      3.4G   12K  3.4G   1% /run/secrets/kubernetes.io/serviceaccount
```

### Known issues
1. From v1.8.0, `echo -e` or `echo -ne` is not allowed in flexvolume driver script, related issue: [Error creating Flexvolume plugin from directory flexvolume](https://github.com/kubernetes/kubernetes/issues/54494)

2. You may get following error in the kubelet log when trying to use a flexvolume:
```
Volume has not been added to the list of VolumesInUse
```
You could let flexvolume plugin return following:
```
echo {"status": "Success", "capabilities": {"attach": false}}
```
Which means your [FlexVolume driver does not need Master-initiated Attach/Detach](https://docs.openshift.org/latest/install_config/persistent_storage/persistent_storage_flex_volume.html#flex-volume-drivers-without-master-initiated-attach-detach)

3. The default plugin direcotory `/usr/libexec/kubernetes/kubelet-plugins/volume/exec/` does not work on k8s cluster set up by acs-engine due to [bug](https://github.com/Azure/acs-engine/issues/1907)

### about this blobfuse flexvolume driver usage
1. You will get following error if you don't specify your secret type as driver name `blobfuse/blobfuse`
```
MountVolume.SetUp failed for volume "azure" : Couldn't get secret default/azure-secret
```

### Links
[Flexvolume doc](https://github.com/kubernetes/community/blob/master/contributors/devel/flexvolume.md)

More clear steps about flexvolume by Redhat doc: [Persistent Storage Using FlexVolume Plug-ins](https://docs.openshift.org/latest/install_config/persistent_storage/persistent_storage_flex_volume.html)
