## 1. Build csi-hostpath image

```
make hostpath
cp _output/hostpathplugin pkg/hostpath/extras/docker/
cd pkg/hostpath/extras/docker/
docker build --no-cache -t andyzhangx/csi-hostpath:1.0.0 .
#docker login
docker push andyzhangx/csi-hostpath:1.0.0
```

## 2. Test csi-flexvol-installer image
```
docker run -it --name csi-hostpath andyzhangx/csi-hostpath:1.0.0 --nodeid=abc bash
docker stop csi-hostpath && docker rm csi-hostpath
```
