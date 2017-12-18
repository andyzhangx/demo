### Change default storage class (with single master)
For k8s cluster setup by acs-engine (prior to v0.10.0), the default storage class would be [unmanaged azure disk storage class](https://kubernetes.io/docs/concepts/storage/storage-classes/#azure-unmanaged-disk-storage-class), below is the workaround to change the default class to **managed** azure disk storage class:
1. edit following file on master:
```
sudo vi /etc/kubernetes/addons/azure-storage-classes.yaml
```
2. Move the following config to the **managed** kind storage class where you want:
```
storageclass.beta.kubernetes.io/is-default-class: "true"
```
3. After about 2 min, the default storage class will be changed automatically. Use following command to check:
```
watch kubectl get storageclass
```

### Change `/var/lib/docker` to `/mnt` which has 100GB disk space
1. Move docker data in `/var/lib/docker` to `/mnt`
```
sudo service docker stop
sudo mv /var/lib/docker /mnt
sudo ln -s /mnt/docker /var/lib/docker
sudo service docker start
```

2. Set volume path mapping in `/etc/systemd/system/kubelet.service`
```sudo vi /etc/systemd/system/kubelet.service```, append following (**this is the key point here**)
```
--volume=/mnt/docker:/mnt/docker:rw \
```

3. reload kubelet config changes
```
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```
