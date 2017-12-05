## 1. create a secret which stores cifs account name and passwrod
```
kubectl create secret generic cifscreds --from-literal username=USERNAME --from-literal password="PASSWORD"
```

## 2. install flex volume driver on all linux agent nodes
```
sudo mkdir -p /etc/kubernetes/volumeplugins/foo~cifs
cd /etc/kubernetes/volumeplugins/foo~cifs
sudo wget https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/cifs
sudo chmod a+x cifs
```
#### Note
There is some issue with this `cifs` driver, it's not working now.

## 3. specify `volume-plugin-dir` for kubelet service
```
sudo vi /etc/systemd/system/kubelet.service
        --volume-plugin-dir=/etc/kubernetes/volumeplugins \
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

## 4. create a pod with flexvolume-cifs mount on linux
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/nginx-flexvolume-cifs.yaml

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-flexvolume-cifs

## 5. enter the pod container to do validation
kubectl exec -it nginx-flexvolume-cifs -- bash

```
```

### Known issues
1. From v1.8.0, `echo -e` or `echo -ne` is not allowed in flexvolume driver script

### Links
[Flexvolume doc](https://github.com/kubernetes/community/blob/master/contributors/devel/flexvolume.md)

[Persistent Storage Using FlexVolume Plug-ins](https://docs.openshift.org/latest/install_config/persistent_storage/persistent_storage_flex_volume.html)
