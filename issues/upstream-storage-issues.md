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


### Tips:
 - [Postpone deletion of a PV or a PVC when they are being used](https://github.com/kubernetes/kubernetes/blob/f170ef66340f6355d331ed90902574ff0532a20a/pkg/features/kube_features.go#L207-L208) reaches BETA in k8s v1.10
