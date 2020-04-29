## Kubernetes upstream storage issues

### 1. WaitForAttach failed for azure disk: strconv.Atoi: parsing "": invalid syntax

**Issue details**:
MountVolume.WaitForAttach may fail in the azure disk remount when mounting a volume very quickly after unmount.

**error logs**:
```
MountVolume.WaitForAttach failed for volume "pvc-66de4353-f3e0-11e8-ab47-ce9eda135fcc" : strconv.Atoi: parsing "": invalid syntax
```

**Related issues**
- [MountVolume.WaitForAttach failed - strconv.Atoi: parsing "": invalid syntax](https://github.com/Azure/AKS/issues/761)
- [Storage: devicePath is empty while WaitForAttach in StatefulSets](https://github.com/kubernetes/kubernetes/issues/67342)
- [Second Pod Using Same PVC Fails WaitForAttach Flakily](https://github.com/kubernetes/kubernetes/issues/65246)


**Fix**

- PR [Fix race between MountVolume and UnmountDevice](https://github.com/kubernetes/kubernetes/pull/71074) fixed this issue

| k8s version | fixed version |
| ---- | ---- |
| v1.10 | no fix |
| v1.11 | 1.11.7 |
| v1.12 | 1.12.5 |
| v1.13 | no such issue |

### 2. pod stuck in Terminating issue due to corrupt mnt point in flexvol plugin

**Issue details**:
pod could not be terminated when pod volume path is corrupted due to smb server return error status: resource temporarily unavailable, in this condition, pod will be in `Terminating` forever.

**Related issues**
- [pod could not be terminated when pod volume path is corrupted](https://github.com/kubernetes/kubernetes/issues/75233)

**Fix**

- PR [fix pod stuck in Terminating issue due to corrupt mnt point in flexvol plugin](https://github.com/kubernetes/kubernetes/pull/75234) would call Unmount if PathExists returns any error.

| k8s version | fixed version |
| ---- | ---- |
| v1.11 | no fix |
| v1.12 | 1.12.10|
| v1.13 | 1.13.8 |
| v1.14 | 1.14.4 |
| v1.15 | 1.15.1 |
| v1.16 | 1.16.0 |

**Workaround**
 - on agent node, run “mount | grep cifs” to get all cifs mounts
 - check every cifs mount, e.g.
```
sudo ls -lt /var/lib/kubelet/pods/5c949781-4c6d-11e9-825d-000d3a0dd47b/volumes/microsoft.com~smb/test
ls: cannot access '/var/lib/kubelet/pods/5c949781-4c6d-11e9-825d-000d3a0dd47b/volumes/microsoft.com~smb/test': Permission denied
```
 - if `s -lt …` failed (in above example), run:
```
sudo umount /var/lib/kubelet/pods/5c949781-4c6d-11e9-825d-000d3a0dd47b/volumes/microsoft.com~smb/test
```

And then the pod will be in terminated soon.

### 3. node shutdown make disk volume detach in statefulset costs more than 5min

**Issue details**:

When a node is shutdown the control plane do not distinguish between a kubelet or node failure and generally cannot answer the question "are pods still running on the node ?" This leads to a situation where it cannot make the right assumptions to preserve the availability of stateful workloads, this manifests as volumes not being detached due the fact that the control plane is not able to determine if containers are still running.

**Fix**
- [add node shutdown KEP](https://github.com/kubernetes/enhancements/pull/1116)

**Workaround**
 - [Improving Kubernetes reliability: quicker detection of a Node down](https://fatalfailure.wordpress.com/2016/06/10/improving-kubernetes-reliability-quicker-detection-of-a-node-down/)

### Tips:
 - [Postpone deletion of a PV or a PVC when they are being used](https://github.com/kubernetes/kubernetes/blob/f170ef66340f6355d331ed90902574ff0532a20a/pkg/features/kube_features.go#L207-L208) reaches BETA in k8s v1.10
