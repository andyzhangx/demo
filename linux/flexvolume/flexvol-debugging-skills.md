## flexvolume driver debugging skills
 - Comparison between flexvolume, built-in volume plugins, CSI volume

| Volume Plugin Name | Dynamic Provisioning | Supported Versions | Notes |
| ---- | ---- | ---- | ---- |
| flexvolume | [No](https://github.com/kubernetes/kubernetes/pull/33538) | from v1.7 | need extra deployment  |
| built-in plugin | Yes | from v1.6 | no extra deployment |
| CSI | Yes | from v1.10 (Beta) | need extra deployment |

 - How to build binary for flexvolume driver
 Since `hyperkube` image may be different in every k8s version, binary should be built independently for every k8s version.
