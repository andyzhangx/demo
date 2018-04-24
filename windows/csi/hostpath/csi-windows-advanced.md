## CSI on Windows Tips
### Deployment

Since Windows does not support unix socket file, container communication inside a pod would use tcp protocol instead:
```
.\hostpathplugin.exe --nodeid=abc --endpoint=tcp://localhost:10000 --v=5
```

### Debugging
```
.\hostpathplugin.exe --nodeid=abc --endpoint=tcp://localhost:10000 --v=5

set KUBE_NODE_NAME=abc
.\driver-registrar.exe --csi-address=localhost:10000 --v=5
```
