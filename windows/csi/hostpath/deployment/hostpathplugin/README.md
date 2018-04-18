## 1. Build csi-hostpath on Windows image

```
cd ~/go/src/github.com/kubernetes-csi/drivers
CGO_ENABLED=0 GOOS=windows go build -a -ldflags '-extldflags "-static"' -o _output/hostpathplugin.exe ./app/hostpathplugin
#copy Dockerfile and hostpathplugin.exe to one folder
docker build --no-cache -t andyzhangx/hostpathplugin-windows:1.0.0 -f ./Dockerfile .
#docker login
docker push andyzhangx/hostpathplugin-windows:1.0.0
```

## 2. Test hostpathplugin-windows image
```
docker run -it --name hostpathplugin andyzhangx/hostpathplugin-windows:1.0.0 --nodeid=abc --endpoint=tcp://127.0.0.1:10000 cmd
docker stop hostpathplugin && docker rm hostpathplugin
```

#### Links
 - [kubernetes-csi/drivers](https://github.com/kubernetes-csi/drivers)
