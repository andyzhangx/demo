## Get monitoring metrics from kubelet
#### 1. Get node name by `kubectl get no`
```
NAME                        STATUS    AGE       VERSION
k8s-agentpool1-55859097-0   Ready     29d       v1.7.9-dirty
k8s-master-55859097-0       Ready     29d       v1.7.9
```

#### 2. Get agent metrics from kubelet
```
curl http://k8s-agentpool1-55859097-0:10255/stats/summary
```

#### 3. Get metrics from cAdvisor Web UI
Log on to node `k8s-agentpool1-55859097-0`, run following command:
```
curl http://localhost:4194/containers/
```

