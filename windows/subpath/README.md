## 1. create a pod with subpath mount(use `subPath`)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/subpath/aspnet-subpath.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po aspnet-subpath

## 2. enter the pod container to do validation
kubectl exec -it aspnet-subpath -- cmd

```
C:\>cd mnt\azure

C:\mnt\azure>dir
 Volume in drive C has no label.
 Volume Serial Number is F878-8D74

 Directory of C:\mnt\azure

11/08/2017  03:20 AM    <DIR>          .
11/08/2017  03:20 AM    <DIR>          ..
09/29/2017  02:39 PM    <DIR>          ADFS
09/29/2017  12:28 PM    <DIR>          AppCompat
10/13/2017  09:04 PM    <DIR>          apppatch
10/04/2017  11:28 PM    <DIR>          assembly
09/29/2017  12:25 PM            65,536 bfsvc.exe
09/29/2017  12:28 PM    <DIR>          Boot
09/29/2017  12:28 PM    <DIR>          Branding
10/13/2017  09:02 PM    <DIR>          CbsTemp
10/03/2017  08:25 PM    <DIR>          debug
...
```

### Note
 - [CVE-2017-1002101 - subpath volume mount handling allows arbitrary file access in host filesystem](https://github.com/kubernetes/kubernetes/issues/60813)
 
**Attack case on Windows node**
 ```
 kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/windows/subpath/secbypass-subpath-windows.yaml
 ```
 
**Fix**

| k8s version | fixed version |
| ---- | ---- |
| v1.6 | no fix since v1.6 does not accept any cherry-pick |
| v1.7 | 1.7.14 by #61047 |
| v1.8 | 1.8.9 by #61046 |
| v1.9 | 1.9.4 by #61045 |
| v1.10 | 1.10.0 |

**Logs after fix**
```
$ kubectl describe po secbypass-win
Name:           secbypass-win
Namespace:      default
Node:           38156k8s9010/10.240.0.5
Start Time:     Sun, 18 Mar 2018 14:02:10 +0000
Labels:         <none>
Annotations:    <none>
Status:         Pending
IP:             10.244.2.68
Init Containers:
  prep-symlink:
    Container ID:       docker://a964f65a5772315b3e6a66ea04b9e3013b4e69bb31b62306c1aea8f2a9503554
    Image:              microsoft/windowsservercore:1709
    Image ID:           docker-pullable://microsoft/windowsservercore@sha256:dfc84737964de95ec888ae25aa70affd815ded546e30491dec630205f8297012
    Port:               <none>
    Command:
      cmd.exe
      /c
      mklink /J c:\tmp\abc c:\windows
    State:              Terminated
      Reason:           Completed
      Exit Code:        0
      Started:          Sun, 18 Mar 2018 14:09:00 +0000
      Finished:         Sun, 18 Mar 2018 14:09:02 +0000
    Ready:              True
    Restart Count:      0
    Environment:        <none>
    Mounts:
      /tmp from docker-socket (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-s3c96 (ro)
Containers:
  all-your-base-are-belong-to-us:
    Container ID:
    Image:              microsoft/aspnet:4.7.1-windowsservercore-1709
    Image ID:
    Port:               <none>
    State:              Waiting
      Reason:           failed to prepare subPath for volumeMount "docker-socket" of container "all-your-base-are-belong-to-us"
    Ready:              False
    Restart Count:      0
    Environment:        <none>
    Mounts:
      /test from docker-socket (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-s3c96 (ro)
Conditions:
  Type          Status
  Initialized   True
  Ready         False
  PodScheduled  True
Volumes:
  docker-socket:
    Type:       EmptyDir (a temporary directory that shares a pod's lifetime)
    Medium:
  default-token-s3c96:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-s3c96
    Optional:   false
QoS Class:      BestEffort
Node-Selectors: beta.kubernetes.io/os=windows
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                                   Type            Reason                  Message
  ---------     --------        -----   ----                    -------------                                   --------        ------                  -------
  8m            8m              1       default-scheduler                                                       Normal          Scheduled               Successfully assigned secbypass-win to 38156k8s9010
  8m            8m              1       kubelet, 38156k8s9010                                                   Normal          SuccessfulMountVolume   MountVolume.SetUp succeeded for volume "docker-socket"
  8m            8m              1       kubelet, 38156k8s9010                                                   Normal          SuccessfulMountVolume   MountVolume.SetUp succeeded for volume "default-token-s3c96"
  8m            8m              1       kubelet, 38156k8s9010   spec.initContainers{prep-symlink}               Normal          Pulling                 pulling image "microsoft/windowsservercore:1709"
  2m            2m              1       kubelet, 38156k8s9010   spec.initContainers{prep-symlink}               Normal          Pulled                  Successfully pulled image "microsoft/windowsservercore:1709"
  2m            2m              1       kubelet, 38156k8s9010   spec.initContainers{prep-symlink}               Normal          Created                 Created container
  1m            1m              1       kubelet, 38156k8s9010   spec.initContainers{prep-symlink}               Normal          Started                 Started container
  1m            9s              2       kubelet, 38156k8s9010   spec.containers{all-your-base-are-belong-to-us} Normal          Pulling                 pulling image "microsoft/aspnet:4.7.1-windowsservercore-1709"
  10s           8s              2       kubelet, 38156k8s9010   spec.containers{all-your-base-are-belong-to-us} Normal          Pulled                  Successfully pulled image "microsoft/aspnet:4.7.1-windowsservercore-1709"
  10s           8s              2       kubelet, 38156k8s9010   spec.containers{all-your-base-are-belong-to-us} Warning         Failed                  Error: failed to prepare subPath for volumeMount "docker-socket" of container "all-your-base-are-belong-to-us"
```
