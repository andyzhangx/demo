## Get monitoring metrics from kubelet 
 - supported from [Azure/kubernetes](https://github.com/Azure/kubernetes) v1.8.6 and k8s upstream v1.9.0 
#### 1. Get node name by `kubectl get no`
```
NAME                    STATUS    ROLES     AGE       VERSION
26253k8s9000            Ready     <none>    5h        v1.9.0-alpha.1.258+7dd82519da3f8c
k8s-master-26253276-0   Ready     master    5h        v1.8.4
```

#### 2. Get agent metrics from kubelet
```
# curl http://26253k8s9000:10255/stats/summary
{
  "node": {
   "nodeName": "26253k8s9000",
   "startTime": "2017-12-26T05:39:24Z",
   "cpu": {
    "time": "2017-12-26T08:41:22Z",
    "usageCoreNanoSeconds": 284780000000
   },
   "memory": {
    "time": "2017-12-26T08:41:22Z",
    "availableBytes": 6951186432,
    "usageBytes": 1808633856,
    "workingSetBytes": 565006336,
    "rssBytes": 0,
    "pageFaults": 0,
    "majorPageFaults": 0
   },
   "fs": {
    "time": "2017-12-26T08:41:22Z",
    "availableBytes": 0,
    "capacityBytes": 0,
    "usedBytes": 0
   },
   "runtime": {
    "imageFs": {
     "time": "2017-12-26T08:41:23Z",
     "usedBytes": 0,
     "inodesUsed": 0
    }
   }
  },
  "pods": [
   {
    "podRef": {
     "name": "aspnet-flex-example",
     "namespace": "default",
     "uid": "d25664ec-e9ff-11e7-8d49-000d3af9a89c"
    },
    "startTime": "2017-12-26T05:44:21Z",
    "containers": [
     {
      "name": "aspnet-flex-example",
      "startTime": "2017-12-26T05:51:03Z",
      "cpu": {
       "time": "2017-12-26T08:41:24Z",
       "usageNanoCores": 0,
       "usageCoreNanoSeconds": 16796875000
      },
      "memory": {
       "time": "2017-12-26T08:41:24Z",
       "workingSetBytes": 45748224,
       "rssBytes": 0
      },
      "rootfs": {
       "time": "2017-12-26T08:41:24Z",
       "usedBytes": 0
      },
      "logs": {
       "time": null,
       "availableBytes": 0,
       "capacityBytes": 0
      },
      "userDefinedMetrics": null
     }
    ],
    "ephemeral-storage": {
     "time": "2017-12-26T08:41:24Z",
     "availableBytes": 0,
     "capacityBytes": 0,
     "usedBytes": 0
    }
   }
  ]
```

##### Note:
 - Get metrics from cAdvisor Web UI on Windows is not supported yet
 - Related issue
   - ["ImageGCFailed" on Windows nodes](https://github.com/Azure/acs-engine/issues/658)
 - Related PR fixed this issue
   - fixed in k8s upstream: [Implement CRI stats in Docker Shim](https://github.com/kubernetes/kubernetes/pull/51152)
   - fixed in [Azure/kubernetes](https://github.com/Azure/kubernetes): [merge #51152: Implement CRI stats in Docker Shim on Windows](https://github.com/Azure/kubernetes/pull/29)


