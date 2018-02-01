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

##### Replace `kubelet.exe` binary on Windows ServerCore
Prerequisite:
assign a public ip to the agent in azure portal and use RDP to connect to that agent. (only for debugging purpose)

1. open a powershell window
```
start powershell
```
2. download pscp.exe tool
```
cd c:\k
$webclient = New-Object System.Net.WebClient
$url = "https://mirror.kaiyuanshe.org/putty/0.70/w64/pscp.exe"
$file = " $pwd\pscp.exe"
$webclient.DownloadFile($url,$file)
```
3. replace with your linux machine IP, password and then scp `kubelet.exe` to your node
```
mkdir c:\tmp
cd c:\tmp
Start-Process "$pwd\pscp.exe"  -ArgumentList ("-scp -pw PASSWROD azureuser@SERVER-IP:/tmp/kubelet.exe c:\tmp")
.\kubelet.exe --version
```

4. Backup your original binaries first
```
cp c:\k c:\k-backup -Recurse
```

5. Stop `kubeproxy`, `kubelet` services, replace `kubelet.exe` and then start these services 
```
stop-service kubeproxy
stop-service kubelet
cp C:\tmp\kubelet.exe c:\k
start-service kubeproxy
start-service kubelet
```

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
#### Linux
On master node:

1. In `func (a *azureDiskAttacher) Attach(spec *volume.Spec, nodeName types.NodeName)`
```
      1) Get a free disk LUN number "diskController.GetNextDiskLun(nodeName)"
      2) Attach data disk by "diskController.AttachDisk" with LUN number
      3) return the LUN number
```

On agent node:

2. In `func (a *azureDiskAttacher) WaitForAttach(spec *volume.Spec, devicePath string, ...)`
```
      1) rescan SCSI "scsiHostRescan(io, exec)"
      2) find disk identifier(/dev/disk/azure/lunx) by LUN number passed from master "findDiskByLun"
      3) format data disk "formatIfNotFormatted"
```

3. In `func (attacher *azureDiskAttacher) MountDevice(spec *volume.Spec, devicePath string, deviceMountPath string)`
```
      1) make a device mount dir, e.g. /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m358246426
      2) mount /dev/disk/azure/lunx /var/lib/kubelet/plugins/kubernetes.io/azure-disk/mounts/m358246426
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

### Clean disk space on Windows
```
rm -Recurse -Force C:\Windows\Temp\*
```

#### Links
[How to update hyperkube image directly in k8s master](https://github.com/andyzhangx/Demo/blob/master/dev/update-hyperkube.md)

[Azure subscription and service limits, quotas, and constraints](https://docs.microsoft.com/en-us/azure/azure-subscription-service-limits)
