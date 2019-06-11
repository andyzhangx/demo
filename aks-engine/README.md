### Change default storage class (with single master)
For k8s cluster setup by aks-engine (prior to v0.10.0), the default storage class would be [unmanaged azure disk storage class](https://kubernetes.io/docs/concepts/storage/storage-classes/#azure-unmanaged-disk-storage-class), below is the workaround to change the default class to **managed** azure disk storage class:
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
**Attention**:
Before stopping your container service, you need to make sure there is no important running containers on your host, in k8s, you could run `kubectl drain NODE-NAME` to move all pods to other nodes.

1. Move docker data in `/var/lib/docker` to `/mnt`
```
sudo service docker stop
sudo mv /var/lib/docker /mnt
sudo ln -s /mnt/docker /var/lib/docker
sudo service docker start
```

2. Set volume path mapping in `/etc/systemd/system/kubelet.service`
```
sudo vi /etc/systemd/system/kubelet.service
```

append following (**this is the key point here**)
```
--volume=/mnt/docker:/mnt/docker:rw \
```

3. reload kubelet config changes
```
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

### Scale up/down an existing cluster set up by aks-engine
```
./aks-engine scale --new-node-count 1 -g rg-name -s subs-id -l eastus2 --client-id client-id --client-secret client-secret --api-model ~/acs/kubernetes-vmss-1.12.9.json
```

**related issues**
 - [Put /var/lib/docker under /mnt?](https://github.com/Azure/acs-engine/issues/1307)
 - [Document Usage of Ephemeral Disks](https://github.com/Azure/acs-engine/issues/543)
 - [Add customized config: use /mnt (the ephemeral/temp drive) for pod volumes](https://github.com/Azure/acs-engine/issues/2099)
 - [k8s Windows 1.8.13 git cherry-pick conflicts](https://github.com/Azure/acs-engine/issues/2974)

#### Links
[Create a Service Principal](https://github.com/Azure/aks-engine/blob/master/docs/serviceprincipal.md#creating-a-service-principal)

[aks-engine Cluster Definition](https://github.com/Azure/aks-engine/blob/master/docs/clusterdefinition.md)

[Make kubernetes dashboard as external access](https://github.com/Azure/devops-sample-solution-for-azure-china/tree/master-dev/aks-engine#9-config-kubernetes-dashboard-optional)

[Accessing Dashboard 1.7.X and above](https://github.com/kubernetes/dashboard/wiki/Accessing-Dashboard---1.7.X-and-above)


