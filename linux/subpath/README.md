## 1. create a pod with subpath mount(use `subPath`)
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/subpath/nginx-subpath.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po nginx-subpath

## 2. enter the pod container to do validation
kubectl exec -it nginx-subpath -- bash

```
root@nginx-hostpath:/# ls /mnt/hostpath -lt
total 4708
-rw-r--r-- 1 root root   24584 Nov 20 08:25 Microsoft.Azure.Extensions.CustomScript.6.manifest.xml
drwx------ 2 root root    4096 Nov 20 08:12 events
-rw-r--r-- 1 root root   13271 Nov 20 08:11 Prod.1.manifest.xml
-rw-r--r-- 1 root root       1 Nov 20 07:55 Incarnation
-rw-r--r-- 1 root root   21478 Nov 20 07:55 ExtensionsConfig.6.xml
-rw-r--r-- 1 root root    1280 Nov 20 07:55 ABBF05E2E537D4FC04F8BB5695743FEFC8ED981E.crt
-rw-r--r-- 1 root root     875 Nov 20 07:55 D9FBFC079879707B4F6B3D1DDDA71383F55B385A.crt
-rw-r--r-- 1 root root    1860 Nov 20 07:55 ABBF05E2E537D4FC04F8BB5695743FEFC8ED981E.prv
-rw-r--r-- 1 root root    4015 Nov 20 07:55 Certificates.pem
-rw-r--r-- 1 root root    4891 Nov 20 07:55 Certificates.p7m
...
```

### Note
 - [CVE-2017-1002101 - subpath volume mount handling allows arbitrary file access in host filesystem](https://github.com/kubernetes/kubernetes/issues/60813)

**Attack case on Linux node**
 ```
 kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/windows/subpath/secbypass-subpath.yaml
 ```

**Fix**

| k8s version | fixed version |
| ---- | ---- |
| v1.6 | no fix since v1.6 does not accept any cherry-pick |
| v1.7 | 1.7.14 by #61047 |
| v1.8 | 1.8.9 by 61046 |
| v1.9 | 1.9.4 by 61045 |
| v1.10 | 1.10.0 |

**Logs after fix**
```
$ kubectl describe po secbypass
Name:           secbypass
Namespace:      default
Node:           k8s-linuxpool1-38156607-0/10.240.0.4
Start Time:     Sun, 18 Mar 2018 14:31:08 +0000
Labels:         <none>
Annotations:    <none>
Status:         Pending
IP:             10.244.0.8
Init Containers:
  prep-symlink:
    Container ID:       docker://acb288df34d15f68a36c9de588e68b0a2eb8a48940e5aa6061015e1c05aef963
    Image:              docker:stable
    Image ID:           docker-pullable://docker@sha256:4638777f426cc7e2b4958c409557b9ec7e320bde7159b5833d97375e0bb1b691
    Port:               <none>
    Command:
      ln
      -s
      /home/anyuser
      /tmp/vol
    State:              Terminated
      Reason:           Completed
      Exit Code:        0
      Started:          Sun, 18 Mar 2018 14:31:16 +0000
      Finished:         Sun, 18 Mar 2018 14:31:16 +0000
    Ready:              True
    Restart Count:      0
    Environment:        <none>
    Mounts:
      /tmp/ from volume01 (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-s3c96 (ro)
Containers:
  all-your-base-are-belong-to-us:
    Container ID:
    Image:              docker:stable
    Image ID:
    Port:               <none>
    Command:
      /bin/sleep
      999999
    State:              Waiting
      Reason:           failed to prepare subPath for volumeMount "volume01" of container "all-your-base-are-belong-to-us"
    Ready:              False
    Restart Count:      0
    Environment:        <none>
    Mounts:
      /test from volume01 (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-s3c96 (ro)
Conditions:
  Type          Status
  Initialized   True
  Ready         False
  PodScheduled  True
Volumes:
  volume01:
    Type:       EmptyDir (a temporary directory that shares a pod's lifetime)
    Medium:
  default-token-s3c96:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-s3c96
    Optional:   false
QoS Class:      BestEffort
Node-Selectors: <none>
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                                    SubObjectPath                                   Type            Reason                  Message
  ---------     --------        -----   ----                                    -------------                                   --------        ------                  -------
  34s           34s             1       default-scheduler                                                                       Normal          Scheduled               Successfully assigned secbypass to k8s-linuxpool1-38156607-0
  34s           34s             1       kubelet, k8s-linuxpool1-38156607-0                                                      Normal          SuccessfulMountVolume   MountVolume.SetUp succeeded for volume "volume01"
  34s           34s             1       kubelet, k8s-linuxpool1-38156607-0                                                      Normal          SuccessfulMountVolume   MountVolume.SetUp succeeded for volume "default-token-s3c96"
  33s           33s             1       kubelet, k8s-linuxpool1-38156607-0      spec.initContainers{prep-symlink}               Normal          Pulling                 pulling image "docker:stable"
  26s           26s             1       kubelet, k8s-linuxpool1-38156607-0      spec.initContainers{prep-symlink}               Normal          Pulled                  Successfully pulled image "docker:stable"
  26s           26s             1       kubelet, k8s-linuxpool1-38156607-0      spec.initContainers{prep-symlink}               Normal          Created                 Created container
  26s           26s             1       kubelet, k8s-linuxpool1-38156607-0      spec.initContainers{prep-symlink}               Normal          Started                 Started container
  25s           10s             3       kubelet, k8s-linuxpool1-38156607-0      spec.containers{all-your-base-are-belong-to-us} Normal          Pulling                 pulling image "docker:stable"
  24s           9s              3       kubelet, k8s-linuxpool1-38156607-0      spec.containers{all-your-base-are-belong-to-us} Normal          Pulled                  Successfully pulled image "docker:stable"
  24s           9s              3       kubelet, k8s-linuxpool1-38156607-0      spec.containers{all-your-base-are-belong-to-us} Warning         Failed                  Error: failed to prepare subPath for volumeMount "volume01" of container "all-your-base-are-belong-to-us"
  24s           9s              3       kubelet, k8s-linuxpool1-38156607-0                                                      Warning         FailedSync              Error syncing pod
```

```
$ kubectl get po secbypass
NAME        READY     STATUS                                                                                               RESTARTS   AGE
secbypass   0/1       failed to prepare subPath for volumeMount "volume01" of container "all-your-base-are-belong-to-us"   0          1m
```
