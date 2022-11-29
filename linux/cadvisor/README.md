## Get monitoring metrics on AKS node
#### 1. Get agent node IP
```console
kubectl get node -o wide
```

#### 2. Get `ama-logs-rs`
```console
# kubectl get po -n kube-system | grep ama-logs-rs
ama-logs-rs-644ccc4bf5-qknls          1/1     Running            0                  19d
```

#### 3. kubectl exec into the `ama-logs-rs` pod
```console
kubectl exec -it ama-logs-rs-644ccc4bf5-qknls -n kube-system -- sh
```

#### 4. Get metrics from AKS node
```console
# against Linux node on which containers using the `persistent-storage` PVC
curl -s -k -H "Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" https://<LinuxNodeIP>:10250/stats/summary  | grep "persistent-storage"  -B 10

# against Windows node on which containers using the `persistent-storage` PVC
curl -s -k -H "Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" https://<WindowsNodeIP>:10250/stats/summary  | grep "persistent-storage"  -B 10
```

<details>
<summary> example output </summary>

```
   "volume": [
    {
     "time": "2022-11-28T09:00:35Z",
     "availableBytes": 107171033088,
     "capacityBytes": 107271557120,
     "usedBytes": 100524032,
     "inodesFree": 0,
     "inodes": 0,
     "inodesUsed": 0,
     "name": "persistent-storage",
     "pvcRef": {
      "name": "persistent-storage-statefulset-azuredisk-win-0",
      "namespace": "default"
     }
    }
   ],
```

</details>

#### Notes
```
The Kubelet also starts an internal HTTP server on port 10255 and exposes some endpoints (mostly for debugging, stats, and for one-off container operations such as kubectl logs or kubectl exec), such as /metrics, /metrics/cadvisor, /pods, /spec, and so on.
```
 - [Kubernetes Node Components: Service Proxy, Kubelet, and cAdvisor](https://medium.com/jorgeacetozi/kubernetes-node-components-service-proxy-kubelet-and-cadvisor-dcc6928ef58c)

 - AKS kubelet 10255/10250 port
 
 Since AKS 1.17.x, insecure port 10255 will be replaced by secure port 10250.
