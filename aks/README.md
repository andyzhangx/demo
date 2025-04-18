# Azure Container Service - AKS

## Steps to create an AKS cluster by [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
#### Prerequisite, define environment variables here:
```console
RESOURCE_GROUP_NAME=
CLUSTER_NAME=
LOCATION=westus2
```

#### 1. Create a resource group
```console
az group create -n $RESOURCE_GROUP_NAME -l $LOCATION
```

#### 2. Create an AKS cluster
```console
az aks create -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --node-count 2 --generate-ssh-keys --disable-rbac --kubernetes-version 1.8.1
```

#### 3. get aks cluster credentials
```console
az aks get-credentials -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME
```

#### 4. Get AKS nodes
```console
kubectl get nodes
```

#### 5. scale up/down AKS cluster nodes
```console
az aks scale -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME --agent-count=2
```

#### 6. delete AKS cluster node
```console
az aks delete -g $RESOURCE_GROUP_NAME -n $CLUSTER_NAME
```

### Tips:
#### Get all avaialbe k8s verions on AKS cluster
```console
az aks get-versions -l $LOCATION -o table
```


### known issues
#### Create azure file PVC error

you may get following error when set up an azure file PVC:
```
Events:
From                            SubObjectPath   Type            Reason                  Message
----                            -------------   --------        ------                  -------
persistentvolume-controller     Warning         ProvisioningFailed      Failed to provision volume with StorageClass "azurefile": failed to find a matc
hing storage account
```

 - Workaround:
Create a `Standard_LRS` storage account in a `shadow resource group` which contains all resources of your aks cluster, naming as `MC_{RESOUCE-GROUP-NAME}{CLUSTER-NAME}{REGION}`, e.g. if you create an aks cluster `andy-aks182` in resouce group `aks` in westus2 region, then `shadow resource group` would be `MC_aks_andy-aks182_westus2`, wait for a few seconds, azure file PVC will be created successfully.

#### Image garbage collection

Current AKS kubelet default setting:
```
/usr/local/bin/kubelet
--image-gc-high-threshold=85
--image-gc-low-threshold=80
```

Kubernetes manages lifecycle of all images through imageManager, with the cooperation of cadvisor.

The policy for garbage collecting images takes two factors into consideration: `HighThresholdPercent` and `LowThresholdPercent`. Disk usage above the high threshold will trigger garbage collection. The garbage collection will delete least recently used images until the low threshold has been met.

https://kubernetes.io/docs/concepts/cluster-administration/kubelet-garbage-collection/#image-collection

to fasten the docker image cleanup, user could use following daemonset as workaround:
```console
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/dev/docker-image-cleanup.yaml
```

#### CNI plugin
 - check which cni plugin is used on k8s node
```
# cat /etc/cni/net.d/10-azure.conflist
{
   "cniVersion":"0.3.0",
   "name":"azure",
   "plugins":[
      {
         "type":"azure-vnet",
         "mode":"transparent",
         "ipsToRouteViaHost":["169.254.20.10"],
         "ipam":{
            "type":"azure-vnet-ipam"
         }
      },
      {
         "type":"portmap",
         "capabilities":{
            "portMappings":true
         },
         "snat":true
      }
   ]
}

# ll /opt/cni/bin
total 207636
drwxr-xr-x 2 root root     4096 Mar 12 01:47 ./
drwxr-xr-x 3 root root     4096 Mar 12 01:47 ../
-rwxrwxr-x 1 root root 46706110 Sep 14 00:56 azure-vnet*
-rwxrwxr-x 1 root root 46446992 Sep 14 00:56 azure-vnet-ipam*
-rwxrwxr-x 1 root root 46446984 Sep 14 00:56 azure-vnet-ipamv6*
-rwxrwxr-x 1 root root  7713432 Sep 14 00:56 azure-vnet-telemetry*
-rw-rw-r-- 1 root root      184 Sep 14 00:56 azure-vnet-telemetry.config
-rwxr-xr-x 1 root root  3780654 Mar  9  2022 bandwidth*
-rwxr-xr-x 1 root root  4221977 Mar  9  2022 bridge*
-rwxr-xr-x 1 root root  9742834 Mar  9  2022 dhcp*
-rwxr-xr-x 1 root root  4345726 Mar  9  2022 firewall*
-rwxr-xr-x 1 root root  3811793 Mar  9  2022 host-device*
-rwxr-xr-x 1 root root  3241605 Mar  9  2022 host-local*
-rwxr-xr-x 1 root root  3922560 Mar  9  2022 ipvlan*
-rwxr-xr-x 1 root root  3295519 Mar  9  2022 loopback*
-rwxr-xr-x 1 root root  3959868 Mar  9  2022 macvlan*
-rwxr-xr-x 1 root root  3679140 Mar  9  2022 portmap*
-rwxr-xr-x 1 root root  4092460 Mar  9  2022 ptp*
-rwxr-xr-x 1 root root  3484284 Mar  9  2022 sbr*
-rwxr-xr-x 1 root root  2818627 Mar  9  2022 static*
-rwxr-xr-x 1 root root  3379564 Mar  9  2022 tuning*
-rwxr-xr-x 1 root root  3920827 Mar  9  2022 vlan*
-rwxr-xr-x 1 root root  3523475 Mar  9  2022 vrf*
```

#### aznfs - turbo mount
```console
curl -Ls https://packages.microsoft.com/ubuntu/24.04/prod/pool/main/a/aznfs/aznfs_2.1.0_amd64.deb > /tmp/aznfs_2.1.0_amd64.deb
cd /
ar p /tmp/aznfs_2.1.0_amd64.deb data.tar.gz | tar xvzf - -C / --keep-directory-symlink
cp /opt/microsoft/aznfs/sample-turbo-config.yaml /opt/microsoft/aznfs/data/sample-turbo-config.yaml
chmod a+x /opt/microsoft/aznfs/*.sh

dpkg-deb -x /tmp/aznfs_2.1.0_amd64.deb /tmp/aznfs_2.1.0_amd64
cd /tmp/
tar -czvf aznfs_2.1.0_amd64.tar.gz aznfs_2.1.0_amd64
```

#### Kubernetes dashboard error due to RBAC enabled
please refer to https://docs.microsoft.com/en-us/azure/aks/kubernetes-dashboard#for-rbac-enabled-clusters

#### Issues
 - [Cannot set a different default storage class](https://github.com/Azure/AKS/issues/118#issuecomment-627860179)
 - [kubelet port 10255/10250](https://github.com/Azure/AKS/issues/1601#issuecomment-627922947)

#### Links
 - [Azure Container Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/)
 - [Deploy an Azure Container Service (AKS) cluster](https://docs.microsoft.com/en-us/azure/aks/kubernetes-walkthrough)
 - [Frequently asked questions about Azure Container Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/faq#are-security-updates-applied-to-aks-agent-nodes)
