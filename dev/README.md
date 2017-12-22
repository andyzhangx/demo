# kubernetes developing practices
## kubernetes on Windows
### build kubernetes on Windows
run dos in admin mode
```
cd C:\Go\src\k8s.io\kubernetes\vendor\k8s.io
```

delete the original link files manually
create links
```
mklink /d api ..\..\staging\src\k8s.io\api
mklink /d apiextensions-apiserver ..\..\staging\src\k8s.io\apiextensions-apiserver
mklink /d apimachinery ..\..\staging\src\k8s.io\apimachinery
mklink /d apiserver ..\..\staging\src\k8s.io\apiserver
mklink /d client-go ..\..\staging\src\k8s.io\client-go
mklink /d kube-aggregator ..\..\staging\src\k8s.io\kube-aggregator
mklink /d metrics ..\..\staging\src\k8s.io\metrics
mklink /d sample-apiserver ..\..\staging\src\k8s.io\sample-apiserver
```
begin to build k8s binaries on windows
```
go build cmd\kubelet\kubelet.go
go build cmd\kube-proxy\proxy.go
```
### build linux/windows/darwin on Linux
```
KUBE_BUILD_PLATFORMS=linux/amd64 make WHAT=cmd/kubelet
KUBE_BUILD_PLATFORMS=windows/amd64 make WHAT=cmd/kubelet
KUBE_BUILD_PLATFORMS=darwin/amd64 make WHAT=cmd/kubelet

KUBE_BUILD_PLATFORMS=linux/amd64 make
KUBE_BUILD_PLATFORMS=windows/amd64 make
KUBE_BUILD_PLATFORMS=darwin/amd64 make
```

### debug kubernetes windows node

### build kubernetes on Linux

##### Q: got an error "runtime: goroutine stack exceeds 1000000000-byte limit" running `make` command
```
make clean
make
```

## General development practices
#### precheck before submit any code
```
hack/update-bazel.sh
hack/verify-golint.sh
hack/verify-gofmt.sh
```

## Azure disk & file mount process
On agent node:
```
/dev/sdc <--
/var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m358246426 <--
/var/lib/kubelet/pods/950f2eb8-d4e7-11e7-bc95-000d3a041274/volumes/kubernetes.io~azure-disk/pvc-67e4e319-d4e7-11e7-bc95-000d3a041274 <--
/mnt/azure #mountPath in container
```

Other:
```
/var/lib/kubelet/pods/26a3137c-d4e5-11e7-bc95-000d3a041274/plugins/kubernetes.io~empty-dir
```


#### Links
[How to update hyperkube image directly in k8s master](https://github.com/andyzhangx/Demo/blob/master/dev/update-hyperkube.md)
