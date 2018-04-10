## 1. Build driver-registrar image

```
cd ~/go/src/github.com/kubernetes-csi/driver-registrar
make driver-registrar
docker build --no-cache -t andyzhangx/driver-registrar:1.0.0 -f ./Dockerfile .
#docker login
docker push andyzhangx/driver-registrar:1.0.0
```

## 2. Test driver-registrar image
```
docker run -it --name driver-registrar andyzhangx/driver-registrar:1.0.0 bash
docker stop driver-registrar && docker rm driver-registrar
```
