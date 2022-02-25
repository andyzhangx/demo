# kubernetes developing practices
### build kube-controller-manager image
```console
cd ~/go/src/k8s.io/kubernetes/cmd/kube-controller-manager
go build
wget https://raw.githubusercontent.com/andyzhangx/demo/master/dev/build-kube-controller-manager/Dockerfile
docker build --no-cache -t andyzhangx/kube-controller-manager:v1.20.0 -f ./Dockerfile .
```

### build kube-apiserver image
```console
cd ~/go/src/k8s.io/kubernetes/cmd/kube-apiserver
go build
wget https://raw.githubusercontent.com/andyzhangx/demo/master/dev/build-kube-apiserver/Dockerfile
docker build --no-cache -t andyzhangx/kube-apiserver:v1.20.0 -f ./Dockerfile .
```
About how to change api-server built-in version, refer to https://github.com/andyzhangx/kubernetes/commit/37349b38f76d684468102d379b5c9abe5f9fee81

### build hyperkube image
```console
# Run the following from the top level kubernetes directory, to build the binaries necessary for creating hyperkube image.
$ KUBE_BUILD_PLATFORMS=linux/amd64 make kube-apiserver kube-controller-manager kube-proxy kube-scheduler kubectl kubelet

# Create and push the hyperkube image
$ REGISTRY=andyzhangx VERSION=1.18.0-beta-azurefile ARCH=amd64 make -C cluster/images/hyperkube push
```
for details, refer to [build hyperkube image and push](https://github.com/kubernetes/kubernetes/tree/master/cluster/images/hyperkube)

## kubernetes on Windows
### 2. build kubernetes on Windows
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

#### Replace `kubelet` binary on Linux Agent node
 - upload `kubelet` binary to azure storage account
```console
az storage blob upload --account-name andydevdiag --account-key xxx --container-name public --file kubelet --name kubelet
```
 - `kubectl-enter` agent node
```
wget -O /tmp/kubelet https://andydevdiag.blob.core.windows.net/public/kubelet
sudo systemctl stop kubelet && cp /tmp/kubelet /usr/local/bin/kubelet && sudo systemctl start kubelet
```

### debug kubernetes windows node

#### Replace `kubelet.exe` binary on Windows Agent node
 - Prerequisite:
assign a public ip to the agent in azure portal (only for debugging purpose)
 - build `kubelet.exe` on Kubernetes branch
```console
KUBE_BUILD_PLATFORMS=windows/amd64 make WHAT=cmd/kubelet
```

1. Copy `kubelet.exe` to the agent node
##### Option#1 (ssh)
 - scp `kubelet.exe` to the agent node, e.g.
```console
scp ./_output/local/bin/windows/amd64/kubelet.exe azureuser@hostname.eastus2.cloudapp.azure.com:/tmp/
```

##### Option#2 (RDP)
 - use RDP to connect to that agent
 - open a powershell window
```console
start powershell
```
 - download pscp.exe tool
```console
cd c:\k
$webclient = New-Object System.Net.WebClient
$url = "https://mirror.azure.cn/putty/0.73/w64/pscp.exe"
$file = " $pwd\pscp.exe"
$webclient.DownloadFile($url,$file)
```
 - replace with your linux machine IP, password and then scp `kubelet.exe` to your node
```console
mkdir c:\tmp
cd c:\tmp
Start-Process "$pwd\pscp.exe"  -ArgumentList ("-scp -pw PASSWROD azureuser@SERVER-IP:/tmp/kubelet.exe c:\tmp")
.\kubelet.exe --version
```

2. Backup your original binaries first
```
cp c:\k c:\k-backup -Recurse
```

3. Stop `kubeproxy`, `kubelet` services, replace `kubelet.exe` and then start these services 
```
stop-service kubeproxy
stop-service kubelet
cp C:\tmp\kubelet.exe c:\k
start-service kubeproxy
start-service kubelet
```

### 2. build kubernetes on Linux

##### Q: got an error "runtime: goroutine stack exceeds 1000000000-byte limit" running `make` command
```
make clean
make
```

##### Q: build error: `cannot touch '_output/bin/deepcopy-gen': No such file or directory`
```
make clean
mkdir -p ~/go/src/k8s.io/kubernetes/_output/local/bin/linux/amd64
cd ~/go/src/k8s.io/kubernetes

go build -o _output/bin/conversion-gen ./vendor/k8s.io/code-generator/cmd/conversion-gen
go build -o _output/bin/deepcopy-gen ./vendor/k8s.io/code-generator/cmd/deepcopy-gen
go build -o _output/bin/defaulter-gen ./vendor/k8s.io/code-generator/cmd/defaulter-gen
go build -o _output/bin/go-bindata ./vendor/github.com/jteeuwen/go-bindata/go-bindata
go build -o _output/bin/openapi-gen ./vendor/k8s.io/code-generator/cmd/openapi-gen

cp api/api-rules/violation_exceptions.list _output/violations.report
make
```

##### Build your own `hyperkube` image
```
cp _output/bin/hyperkube ~/go/src/k8s.io/kubernetes/cluster/images/hyperkube/	
#export BASEIMAGE=k8s.gcr.io/debian-hyperkube-base-amd64:0.10
sed -i 's/BASEIMAGE/k8s.gcr.io\/debian-hyperkube-base-amd64:0.10/g' Dockerfile
IMAGE_TAG=andyzhangx/hyperkube:v1.15.0-azure-config
docker build --no-cache -t $IMAGE_TAG .
docker push $IMAGE_TAG	
```
 - Build Your Custom Kubelet Image
```
cd cluster/images/hyperkube/
make VERSION=v1.15.0-azure-metrics ARCH=amd64
```
 > For details, refer to https://tureus.github.io/devops/2017/01/24/build-your-custom-kubelet-image.html
 > https://github.com/kubernetes/kubernetes/tree/master/cluster/images/hyperkube

## General development practices
#### precheck before submit any code
```
hack/update-bazel.sh
hack/verify-golint.sh
hack/verify-gofmt.sh
```

## Azure disk mount process
#### Linux
On master node:

1. In `func (a *azureDiskAttacher) Attach(spec *volume.Spec, nodeName types.NodeName)`
```
      1) Get a free disk LUN number "diskController.GetNextDiskLun(nodeName)"
      2) Attach data disk by "diskController.AttachDisk" with LUN number
      3) return the LUN number
```

On agent node(before k8s v1.10.2):

2. In `func (a *azureDiskAttacher) WaitForAttach(spec *volume.Spec, devicePath string, ...)`
```
      1) rescan SCSI "scsiHostRescan(io, exec)"
      2) find disk identifier(/dev/disk/azure/lunx) by LUN number passed from master "findDiskByLun"
      3) format data disk "formatIfNotFormatted", e.g.
      mkfs.ext4 -F /dev/disk/azure/scsi1/lun0
```

3. In `func (attacher *azureDiskAttacher) MountDevice(spec *volume.Spec, devicePath string, deviceMountPath string)`
```
      1) make a device mount dir, e.g. /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m358246426
      2) mount -t ext4 -o defaults /dev/disk/azure/scsi1/lun0 /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/b3492765522
```

4. In `func (m *azureDiskMounter) SetUpAt(dir string, fsGroup *int64)`
```
      1) mkdir a pod dir, e.g. /var/lib/kubelet/pods/950f2eb8-d4e7-11e7-bc95-000d3a041274/volumes/kubernetes.io~azure-disk/pvc-67e4e319-d4e7-11e7-bc95-000d3a041274
      2) mount --bind /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m358246426 /var/lib/kubelet/pods/950f2eb8-d4e7-11e7-bc95-000d3a041274/volumes/kubernetes.io~azure-disk/pvc-67e4e319-d4e7-11e7-bc95-000d3a041274
```
In pod volume mapping, it only uses `/var/lib/kubelet/pods/950f2eb8-d4e7-11e7-bc95-000d3a041274/volumes/kubernetes.io~azure-disk/pvc-67e4e319-d4e7-11e7-bc95-000d3a041274` 

The whole mounting chain would be like following:
```
/dev/sdc <--
/var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m358246426 <-- (bind mount)
/var/lib/kubelet/pods/950f2eb8-d4e7-11e7-bc95-000d3a041274/volumes/kubernetes.io~azure-disk/pvc-67e4e319-d4e7-11e7-bc95-000d3a041274 <--
/mnt/azure #mountPath in container
```

Other:
```
/var/lib/kubelet/pods/26a3137c-d4e5-11e7-bc95-000d3a041274/plugins/kubernetes.io~empty-dir
```

Example logs:
```
Sep 27 10:21:49 reconciler.go:207] operationExecutor.VerifyControllerAttachedVolume started for volume "pvc-12b458f4-c23f-11e8-8d27-46799c22b7c6"
Sep 27 10:23:57 operation_generator.go:1168] Controller attach succeeded for volume "pvc-12b458f4-c23f-11e8-8d27-46799c22b7c6"

Sep 27 10:23:57 operationExecutor.MountVolume started for volume "pvc-12b458f4-c23f-11e8-8d27-46799c22b7c6" 
Sep 27 10:23:57 operation_generator.go:486] MountVolume.WaitForAttach entering for volume "pvc-12b458f4-c23f-11e8-8d27-46799c22b7c6"
Sep 27 10:25:05 azure_common_linux.go:194] azureDisk - Disk "/dev/disk/azure/scsi1/lun3" appears to be unformatted, attempting to format as type: "ext4" with options: [-E lazy_itable_init=0,lazy_journa
Sep 27 10:25:08 azure_common_linux.go:199] azureDisk - Disk successfully formatted with 'mkfs.ext4 [-E lazy_itable_init=0,lazy_journal_init=0 -F /dev/disk/azure/scsi1/lun3]'
Sep 27 10:25:08 operation_generator.go:495] MountVolume.WaitForAttach succeeded for volume "pvc-12b458f4-c23f-11e8-8d27-46799c22b7c6" 
Sep 27 10:25:08 operation_generator.go:514] MountVolume.MountDevice succeeded for volume "pvc-12b458f4-c23f-11e8-8d27-46799c22b7c6"
Sep 27 10:25:08 azure_mounter.go:166] azureDisk - successfully mounted disk kubernetes-dynamic-pvc-12b458f4-c23f-11e8-8d27-46799c22b7c6 on /var/lib/kubelet/pods/12bb6f88-c23f-11e8-8d27-46799c22b7c6/vol
Sep 27 10:25:08 operation_generator.go:557] MountVolume.SetUp succeeded for volume "pvc-12b458f4-c23f-11e8-8d27-46799c22b7c6"
```

### Clean disk space on Windows
```console
rm -Recurse -Force C:\Windows\Temp\*
```

### kubectl-enter
```console
sudo wget https://raw.githubusercontent.com/andyzhangx/demo/master/dev/kubectl-enter
sudo chmod a+x ./kubectl-enter
./kubectl-enter <node-name>
```

### nonroot image
```console
COPY ./_output/blobplugin /blobplugin
ENTRYPOINT ["/blobplugin"]

FROM mcr.microsoft.com/aks/fundamental/base-ubuntu:v0.0.5
RUN useradd -u 10001 nonroot
USER nonroot

docker build --no-cache -t andyzhangx/ubuntu1604:nonroot -f ~/test2/Dockerfile .
```

### Get node metics
```console
kubectl get --raw /api/v1/nodes/aks-agentpool-21757482-vmss000000:10250/proxy/metrics
```

#### Links
 - [build hyperkube image and push](https://github.com/kubernetes/kubernetes/tree/master/cluster/images/hyperkube)
 - [How to update hyperkube image directly in k8s master](https://github.com/andyzhangx/Demo/blob/master/dev/update-hyperkube.md)
 - [Azure subscription and service limits, quotas, and constraints](https://docs.microsoft.com/en-us/azure/azure-subscription-service-limits)
