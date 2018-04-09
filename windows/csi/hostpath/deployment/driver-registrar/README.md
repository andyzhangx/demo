## 1. Build driver-registrar on Windows image

```
cd ~/go/src/github.com/kubernetes-csi/driver-registrar
CGO_ENABLED=0 GOOS=windows go build -a -ldflags '-extldflags "-static"' -o ./bin/driver-registrar.exe ./cmd/driver-registrar
#copy Dockerfile and driver-registrar.exe to one folder
docker build --no-cache -t andyzhangx/driver-registrar-windows:1.0.0 -f ./Dockerfile .
#docker login
docker push andyzhangx/driver-registrar-windows:1.0.0
```

## 2. Test driver-registrar-windows image
```
docker run -it --name driver-registrar andyzhangx/driver-registrar-windows:1.0.0 cmd
docker stop driver-registrar && docker rm driver-registrar
```
