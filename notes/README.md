### Common issues
- [Volume status out of sync when kubelet restarts](https://github.com/kubernetes/kubernetes/issues/33203): 
```
one solution is restart kubelet in the original node and also the node with azure disk (`sudo systemctl restart kubelet`), and then after a few minutes, check the pod & volume status.
```

- PV & PVC accessModes

accessModes do not enforce access right, but rather act as labels to match a PV to a PVC.
One PV could only be bound to one PVC, and one PVC (after bound to a PV) could be used by multiple pods

Redhat Openshift provides a good [example](https://people.redhat.com/aweiteka/docs/preview/20170510/install_config/storage_examples/shared_storage.html) for you to understand.

- PVC readOnly setting
```
At present, we allow two approaches to set PVC's ReadOnly attribute: specified by Pod.Spec.Volumes.PersistentVolumeClaim.ReadOnly, or specified by PersistentVolume.Spec.<PersistentVolumeSource>.ReadOnly, but when we try to get the ReadOnly attribute from volume.Spec for a PVC volume, we only consider volume.Spec.ReadOnly, which only comes from Pod.Spec.Volumes.PersistentVolumeClaim.ReadOnly, see AWS as an example.
```
details: https://github.com/kubernetes/kubernetes/issues/61758#issuecomment-376506621

### Links
 - [Common Kubernetes Ports](https://kubernetes.io/docs/setup/independent/install-kubeadm/#check-required-ports)
 - [Feature Gates](https://github.com/kubernetes/kubernetes/blob/master/pkg/features/kube_features.go)
 - [Debug Services](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-service/)
 
#### Kubernetes network KB
 - [Basic Iptables Options](https://help.ubuntu.com/community/IptablesHowTo)
 - [Kubernetes Services By Example](https://blog.openshift.com/kubernetes-services-by-example/)
