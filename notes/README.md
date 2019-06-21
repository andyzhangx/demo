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
 - [All Kubernetes Ports in code](https://github.com/kubernetes/kubernetes/blob/99e61466ab694b3652db2c063b9996a5d324a57a/pkg/master/ports/ports.go#L43)
 - [Feature Gates](https://github.com/kubernetes/kubernetes/blob/master/pkg/features/kube_features.go)
 - [Debug Services](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-service/)
 - [Improving Kubernetes reliability: quicker detection of a Node down](https://fatalfailure.wordpress.com/2016/06/10/improving-kubernetes-reliability-quicker-detection-of-a-node-down/), [Kubernetes recreate pod if node becomes offline timeout](https://stackoverflow.com/questions/53641252/kubernetes-recreate-pod-if-node-becomes-offline-timeout)
 
#### Kubernetes network KB
 - [Basic Iptables Options](https://help.ubuntu.com/community/IptablesHowTo)
 - [Kubernetes Services By Example](https://blog.openshift.com/kubernetes-services-by-example/)
 
#### Kubernetes storage KB
  - [readOnly should respect values in both FlexVolume PV and PVC ](https://github.com/kubernetes/kubernetes/pull/61759)
