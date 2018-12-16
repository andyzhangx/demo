### Common issues
- [Volume status out of sync when kubelet restarts](https://github.com/kubernetes/kubernetes/issues/33203): 
```
one solution is restart kubelet in the original node and also the node with azure disk (`sudo systemctl restart kubelet`), and then after a few minutes, check the pod & volume status.
```

- PV & PVC accessModes

accessModes do not enforce access right, but rather act as labels to match a PV to a PVC.
One PV could only be bound to one PVC, and one PVC (after bound to a PV) could be used by multiple pods

Redhat Openshift provides a good [example](https://people.redhat.com/aweiteka/docs/preview/20170510/install_config/storage_examples/shared_storage.html) for you to understand.


### Links
 - [Common Kubernetes Ports](https://kubernetes.io/docs/setup/independent/install-kubeadm/#check-required-ports)
 - [Feature Gates](https://github.com/kubernetes/kubernetes/blob/master/pkg/features/kube_features.go)
 - [Debug Services](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-service/)
