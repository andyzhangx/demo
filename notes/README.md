### Common issues
- [Volume status out of sync when kubelet restarts](https://github.com/kubernetes/kubernetes/issues/33203): 
```
one solution is restart kubelet in the original node and also the node with azure disk (`sudo systemctl restart kubelet`), and then after a few minutes, check the pod & volume status.
```

### Links
 - [Common Kubernetes Ports](https://kubernetes.io/docs/setup/independent/install-kubeadm/#check-required-ports)
 - [Feature Gates](https://kubernetes.io/docs/reference/feature-gates/)
