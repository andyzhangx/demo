# Attention: this page is not maintained any more, cifs FlexVolume driver and doc has been moved to [kubernetes-drivers](https://github.com/andyzhangx/kubernetes-drivers/tree/master/flexvolume/cifs).

## 1. create a secret which stores cifs account name and password
```
kubectl create secret generic cifscreds --from-literal username=USERNAME --from-literal password="PASSWORD" --type="foo/cifs"
```

## 2. install flex volume driver on every linux agent node
```
sudo mkdir -p /etc/kubernetes/volumeplugins/foo~cifs
cd /etc/kubernetes/volumeplugins/foo~cifs
sudo wget https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/cifs
sudo chmod a+x cifs
```
#### Note:
Make sure `jq` package is installed on every node.

## 3. specify `volume-plugin-dir` in kubelet service config
```
sudo vi /etc/systemd/system/kubelet.service
        --volume-plugin-dir=/etc/kubernetes/volumeplugins \
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

## 4. create a pod with flexvolume-cifs mount on linux
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/nginx-flex-cifs.yaml

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-flexvolume-cifs

## 5. enter the pod container to do validation
kubectl exec -it nginx-flexvolume-cifs -- bash

```
root@nginx-flex-cifs:/# df -h
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

### about this cifs flexvolume driver usage
1. You will get following error if you don't specify your secret type as driver name `foo/cifs`
```
MountVolume.SetUp failed for volume "azure" : Couldn't get secret default/azure-secret
```

2. You will get `Host down` error if you don't specify the cifs version

### Links
[Flexvolume doc](https://github.com/kubernetes/community/blob/master/contributors/devel/flexvolume.md)

More clear steps about flexvolume by Redhat doc: [Persistent Storage Using FlexVolume Plug-ins](https://docs.openshift.org/latest/install_config/persistent_storage/persistent_storage_flex_volume.html)
