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
# curl http://127.0.0.1:10255/stats/summary
```

#### 3. Get metrics from cAdvisor Web UI
Log on to node `k8s-agentpool1-55859097-0`, run following command:
```
curl http://localhost:4194/containers/
```

#### Notes
```
The Kubelet also starts an internal HTTP server on port 10255 and exposes some endpoints (mostly for debugging, stats, and for one-off container operations such as kubectl logs or kubectl exec), such as /metrics, /metrics/cadvisor, /pods, /spec, and so on.
```
[Kubernetes Node Components: Service Proxy, Kubelet, and cAdvisor](https://medium.com/jorgeacetozi/kubernetes-node-components-service-proxy-kubelet-and-cadvisor-dcc6928ef58c)
