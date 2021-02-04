## install cifs patch driver on Kubernetes agent node
This page shows how to install cifs patch driver(with following fixes) on Kubernetes agent nodes with Linux kernel 5.4.x, `sysctl-install-cifs-module` daemonset will download the source code, build and then install cifs driver on every agent node.

 - details

 Commit id 6988a619f5b7 ("cifs: allow syscalls to be restarted in __smb_send_rqst()") and 2659d3bff3e1 ("cifs: fix interrupted close commands") is scheduled to include in 5.4 Azure tuned kernel in the upcoming release that is currently planned for Feb 22.

### Prerequisite
Make sure there is no Azure File(CIFS) mount on all agent nodes, otherwise installation will fail.

### Install patched CIFS driver on every agent node
 - install daemonset
```console
kubectl apply -f https://raw.githubusercontent.com/andyzhangx/demo/master/dev/cifs/sysctl-install-cifs-module.yaml
```

 - check daemonset status
 ```console
kubectl get po -n kube-system | grep install-cifs-module
sysctl-install-cifs-module-k4fqr            1/1     Running   0          2m11s
 ```

 - check cifs driver installation logs
 ```console
kubectl cp sysctl-install-cifs-module-k4fqr:/tmp/install-cifs-module.log /tmp/install-cifs-module.log -n kube-system
cat /tmp/install-cifs-module.log
...
build modules ...
make: Entering directory '/usr/src/linux-headers-5.4.0-1035-azure'
  Building modules, stage 2.
  MODPOST 1 modules
make: Leaving directory '/usr/src/linux-headers-5.4.0-1035-azure'
install modules ...
patched cifs driver installed successfully.
 ```
