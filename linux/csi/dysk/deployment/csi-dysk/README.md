## 1. Build csi-dysk image

```
make dysk
cp _output/dyskplugin pkg/dysk/extras/docker/
cd pkg/dysk/extras/docker/
docker build --no-cache -t andyzhangx/csi-dysk:1.0.0 .
#docker login
docker push andyzhangx/csi-dysk:1.0.0
```

## 2. Test csi-flexvol-installer image
```
docker run -it --name csi-dysk andyzhangx/csi-dysk:1.0.0 --nodeid=abc bash
docker stop csi-dysk && docker rm csi-dysk
```
