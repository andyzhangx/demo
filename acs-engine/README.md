### Change default storage class
For k8s cluster setup by acs-engine (prior to v0.10.0), the default storage class would be [unmanaged azure disk storage class](https://kubernetes.io/docs/concepts/storage/storage-classes/#azure-unmanaged-disk-storage-class), below is the workaround to change the default class to **managed** azure disk storage class:
first edit following file on master:
```
sudo vi /etc/kubernetes/addons/azure-storage-classes.yaml
```
Move the following config to the storage class where you want:
```
storageclass.beta.kubernetes.io/is-default-class: "true"
```
After about 2 min, the default storage class will be changed automatically. Use following command to check:
```
watch kubectl get storageclass
```
