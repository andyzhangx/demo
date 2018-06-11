## flexvolume driver debugging skills
 - Comparison between flexvolume, built-in volume plugins, CSI volume

| Volume Plugin Name | Support Dynamic Provisioning | Supported Versions | need extra deployment |
| ---- | ---- | ---- | ---- |
| built-in plugin | Yes | all | no |
| flexvolume | [No](https://github.com/kubernetes/kubernetes/pull/33538) | from v1.7 | Yes  |
| CSI | Yes | from v1.10 (Beta) | Yes |

 - How to build binary for flexvolume driver
   - Since `hyperkube` image may be different in every k8s version, binary should be built independently for every k8s version. You could find an example here: [How to build blobfuse binary for FlexVolume dirver running in kubelet](https://github.com/andyzhangx/kubernetes-drivers/tree/master/flexvolume/blobfuse/binary)

 - Check existing base64-encoded accountname in k8s secret
 
 ```
 kubectl get secret dyskcreds -o json | jq -r '.["data"] // empty' | jq -r '.["accountname"] // empty' | base64 -d
 ```
 - Debug flexvolume driver
 ```
sudo ./dysk mount ~/test '{"blob":"dysk06.vhd","container":"dysks","kubernetes.io/fsType":"ext4","kubernetes.io/pod.name":"nginx-flex-dysk","kubernetes.io/pod.namespace":"default","kubernetes.io/pod.uid":"ed04602b-6953-11e8-9895-0a58ac1f0ca0","kubernetes.io/pvOrVolumeName":"test","kubernetes.io/readwrite":"rw","kubernetes.io/secret/accountkey":"eGlhemhhbmcz","kubernetes.io/secret/accountname":"eGlhemhhbmcz","kubernetes.io/serviceAccount.name":"default"}'

sudo ./dysk unmount /var/lib/kubelet/pods/e2d7d5f2-6962-11e8-8bd3-0a58ac1f16f0/volumes/azure~dysk/test
 ```
