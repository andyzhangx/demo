## Azure secret example 
actully it's using kubernetes `secret` kind to store azure storage account, and then let azure file use that secret object in k8s.

#### azure file example using secret
https://github.com/andyzhangx/Demo/tree/master/windows/azurefile#static-provisioning-for-azure-file-on-windows-2016-datacentersupport-from-v17x

#### secret file storing azure storage account
https://github.com/andyzhangx/Demo/blob/master/pv/azure-secrect.yaml

### Windows support note:
`Opaque` type in `secret` kind works on **windows**, while type “kubernetes.io/service-account-token” does not work, it's due to bug https://github.com/kubernetes/kubernetes/issues/52419 (Symlink for ca.crt & token files are broken on windows containers)

Currently windows container team are working on this issue, would update if it's resolved.
