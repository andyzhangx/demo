## flexvolume driver debugging skills
 - Comparison between flexvolume, built-in volume plugins, CSI volume

| Volume Plugin Name | Support Dynamic Provisioning | Supported Versions | need extra deployment |
| ---- | ---- | ---- | ---- |
| flexvolume | [No](https://github.com/kubernetes/kubernetes/pull/33538) | from v1.7 | Yes  |
| built-in plugin | Yes | all | no |
| CSI | Yes | from v1.10 (Beta) | Yes |

 - How to build binary for flexvolume driver
 
 Since `hyperkube` image may be different in every k8s version, binary should be built independently for every k8s version.
