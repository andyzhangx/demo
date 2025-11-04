### Common issues
- [Volume status out of sync when kubelet restarts](https://github.com/kubernetes/kubernetes/issues/33203): 
```
one solution is restart kubelet in the original node and also the node with azure disk (`sudo systemctl restart kubelet`), and then after a few minutes, check the pod & volume status.
```

- PV & PVC accessModes

accessModes do not enforce access right, but rather act as labels to match a PV to a PVC.
One PV could only be bound to one PVC, and one PVC (after bound to a PV) could be used by multiple pods

Redhat Openshift provides a good [example](https://people.redhat.com/aweiteka/docs/preview/20170510/install_config/storage_examples/shared_storage.html) for you to understand.

[Different Access modes for mounted volume in init container and actual container](https://github.com/kubernetes/kubernetes/issues/58511)

- PVC readOnly setting
```
At present, we allow two approaches to set PVC's ReadOnly attribute: specified by Pod.Spec.Volumes.PersistentVolumeClaim.ReadOnly, or specified by PersistentVolume.Spec.<PersistentVolumeSource>.ReadOnly, but when we try to get the ReadOnly attribute from volume.Spec for a PVC volume, we only consider volume.Spec.ReadOnly, which only comes from Pod.Spec.Volumes.PersistentVolumeClaim.ReadOnly, see AWS as an example.
```
details: 
 - https://github.com/kubernetes/kubernetes/issues/61758#issuecomment-376506621
 - [CSI: readOnly field is not passed to CSI NodePublish RPC call](https://github.com/kubernetes/kubernetes/issues/69843)

- namespace can not be deleted

Try the following steps:
  - Get all the resources in the namespace and delete if they’re some resources:
```
kubectl api-resources --verbs=list --namespaced -o name | xargs -n 1 kubectl get --show-kind --ignore-not-found -n $NAMESPACE
```
  - Delete finalizers:
```
kubectl get namespaces $NAMESPACE -o json | jq '.spec.finalizers=[]' > /tmp/ns.json
kubectl proxy &
curl -k -H "Content-Type: application/json" -X PUT --data-binary @/tmp/ns.json http://127.0.0.1:8001/api/v1/namespaces/$NAMESPACE/finalize
```
 - [Namespaces stuck in Terminating state](https://github.com/Azure/AKS/issues/733#issuecomment-583714454)

 - finding out right pseudo-version (vX.Y.Z-<timestamp>-<commit>) of required package
```
TZ=UTC 
git --no-pager show \
  --quiet \
  --abbrev=12 \
  --date='format-local:%Y%m%d%H%M%S' \
  --format="%cd-%h"
```

 - get diff from a pull request
```
git fetch upstream pull/3039/head:3039
```

### Links
 - [Common Kubernetes Ports](https://kubernetes.io/docs/setup/independent/install-kubeadm/#check-required-ports)
 - [All Kubernetes Ports in code](https://github.com/kubernetes/kubernetes/blob/99e61466ab694b3652db2c063b9996a5d324a57a/pkg/master/ports/ports.go#L43)
 - [Feature Gates](https://github.com/kubernetes/kubernetes/blob/master/pkg/features/kube_features.go)
 - [Kubelet parameters](https://github.com/kubernetes/kubernetes/blob/d39214ade1d60cb7120957a4dcff13fed82c01d5/cmd/kubelet/app/options/options.go#L403)
 - [Debug Services](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-service/)
 - [Improving Kubernetes reliability: quicker detection of a Node down](https://fatalfailure.wordpress.com/2016/06/10/improving-kubernetes-reliability-quicker-detection-of-a-node-down/), [Kubernetes recreate pod if node becomes offline timeout](https://stackoverflow.com/questions/53641252/kubernetes-recreate-pod-if-node-becomes-offline-timeout)
 - [Increase maximum pods per node](https://github.com/kubernetes/kubernetes/issues/23349)
 - [Kubernetes API Resources: Which Group and Version to Use](https://akomljen.com/kubernetes-api-resources-which-group-and-version-to-use)
 - [Accessing Kubernetes Pods from Outside of the Cluster](http://alesnosek.com/blog/2017/02/14/accessing-kubernetes-pods-from-outside-of-the-cluster/)
 - [From Cloud Provider to CCM](https://cloud.tencent.com/developer/article/1549964)
 
#### Kubernetes network KB
 - [Basic Iptables Options](https://help.ubuntu.com/community/IptablesHowTo)
 - [Kubernetes Services By Example](https://blog.openshift.com/kubernetes-services-by-example/)
 
#### Kubernetes storage KB
  - [readOnly should respect values in both FlexVolume PV and PVC ](https://github.com/kubernetes/kubernetes/pull/61759)
  - [Volume Security](https://docs.okd.io/latest/install_config/persistent_storage/pod_security_context.html#overview)
  - [Kubernetes: how to set VolumeMount user group and file permissions](https://stackoverflow.com/questions/43544370/kubernetes-how-to-set-volumemount-user-group-and-file-permissions)
  - [Allow volume ownership to be only set after fs formatting](https://github.com/kubernetes/kubernetes/issues/69699)
  - [Best of 2019: Demystifying Persistent Storage Myths for Stateful Workloads in Kubernetes](https://containerjournal.com/topics/container-networking/demystifying-persistent-storage-myths-for-stateful-workloads-in-kubernetes/)
  - [Kubernetes 1.23: Prevent PersistentVolume leaks when deleting out of order](https://kubernetes.io/blog/2021/12/15/kubernetes-1-23-prevent-persistentvolume-leaks-when-deleting-out-of-order/#how-did-reclaim-work-in-previous-kubernetes-releases)
  - [深度解析 Kubernetes Local Persistent Volume](https://cloud.tencent.com/developer/article/1195068)
  
#### Service Mesh
  - [Istio Example](https://istio.io/docs/examples/)

#### Golang
  - [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments)
  - [Go testing style guide](https://www.arp242.net/go-testing-style.html)
  - [Golang CommonMistakes](https://github.com/golang/go/wiki/CommonMistakes#table-of-contents)
  - [arrays-and-slices](https://blog.csdn.net/u011304970/article/details/74938457)
  - [sync](https://mp.weixin.qq.com/s/UpYbmFTowjCPU83W3DxP6Q)
  - [goroutine](https://blog.csdn.net/nuli888/article/details/63331156)
  - Coding on Windows
    - always use `filepath.Join` since `path.Join` may not work on Windows
  - Nil pointer check
    - check `nil` of `ptr`, or use `to.String(ptr)` to replace `*ptr`
  - panic: assignment to entry in nil map
  ```
  m := req.GetParameters()
  m["a"] = "b"  // if m is nil, then panic
  ```
  - Using reference to loop iterator variable
  ```
  func main() {
    var outKey []*int
    var outValue []*string
 
    m := map[int]string{
        1: "a",
        2: "b",
        3: "c",
    }
 
    for k, v := range m {
        outKey = append(outKey, &k)
        outValue = append(outValue, &v)
    }
    fmt.Println("Keys:", *outKey[0], *outKey[1], *outKey[2])
    fmt.Println("Values:", *outValue[0], *outValue[1], *outValue[2])
  }
  ```

#### Docker
  - [Understanding Docker Container Exit Codes](https://medium.com/better-programming/understanding-docker-container-exit-codes-5ee79a1d58f6)
  - [Docker: Remove all images and containers](https://techoverflow.net/2013/10/22/docker-remove-all-images-and-containers/)
```console
docker rm $(docker ps -a -q)
docker rmi $(docker images -q)
docker rmi $(docker images -q) --force
 ```
 
#### jupyterhub
 ```console
helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
helm install jupyterhub/jupyterhub --version 1.2.0 --generate-name
```
 
#### Cloud Native
  - [Future of Cloud Native](https://jimmysong.io/kubernetes-handbook/cloud-native/the-future-of-cloud-native.html)

#### go env setting
  - install go
```
Install go:
https://golang.org/doc/install

wget -O /tmp/go1.24.5.linux-amd64.tar.gz https://storage.googleapis.com/golang/go1.24.5.linux-amd64.tar.gz
cd /tmp/
tar -xvf /tmp/go1.24.5.linux-amd64.tar.gz

cd /usr/local/
mv go go-1.22.4

mv /tmp/go /usr/local/ 
cp /usr/local/go/bin/go /usr/bin/
```
  - set go env
```
export GOPATH=~/go
export GOROOT=/usr/local/go
export PATH=$PATH:$GOPATH/bin:/usr/local/go/bin:/root/go/src/k8s.io/kubernetes/third_party/etcd:~/tectonic/tectonic/tectonic-installer/linux/:/root/go/src/k8s.io/kubernetes/third_party/etcd
export working_dir=~/go/src/k8s.io/kubernetes
export csi_file=~/go/src/sigs.k8s.io/azurefile-csi-driver
export csi_disk=~/go/src/sigs.k8s.io/azuredisk-csi-driver
export csi_lustre=~/go/src/sigs.k8s.io/azurelustre-csi-driver
export csi_blob=~/go/src/sigs.k8s.io/blob-csi-driver
export csi_goofys=~/go/src/github.com/csi-driver/goofys-csi-driver
export csi_smb=~/go/src/github.com/kubernetes-csi/csi-driver-smb
export csi_nfs=~/go/src/github.com/kubernetes-csi/csi-driver-nfs
export csi_iscsi=~/go/src/github.com/kubernetes-csi/csi-driver-iscsi
export csi_proxy=~/go/src/github.com/kubernetes-csi/csi-proxy
export aks_rp=~/go/src/goms.io/aks/rp
export user=andyzhangx
export acs_dir=~/go/src/github.com/Azure/acs-engine
export aks_engine=~/go/src/github.com/Azure/aks-engine
export azure_cli=~/go/src/github.com/Azure/azure-cli
export test_infra=~/go/src/github.com/kubernetes/test-infra
export kaito=~/go/src/github.com/kaito-project/kaito
export keda=~/go/src/github.com/kaito-project/keda-kaito-scaler
/usr/bin/git config --global user.email "xiazhang@microsoft.com"
/usr/bin/git config --global user.name "andyzhangx"
/usr/bin/git config core.editor "vim"
export git_push="git push origin master"
export git_commit="git commit -a"
export GITHUB_USER=andyzhangx
export azure=~/go/src/github.com/kubernetes-sigs/cloud-provider-azure
export local=~/go/src/github.com/kubernetes-sigs/sig-storage-local-static-provisioner
export blobfuse=~/go/src/github.com/Azure/azure-storage-fuse
export agentbaker=~/go/src/github.com/Azure/AgentBaker
export spec=~/go/src/github.com/container-storage-interface/spec
export azure_volume=~/go/src/github.com/Azure/kubernetes-volume-drivers
export dalec=~/go/src/github.com/Azure/dalec-build-defs
export lws=~/go/src/sigs.k8s.io/lws
alias k="kubectl"
```
