## Build blobfuse-flexvol-installer image

```
mkdir blobfuse-flexvol-installer
cd blobfuse-flexvol-installer
wget -O blobfuse-flexvol-installer https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/blobfuse/deployment/blobfuse-flexvol-installer/Dockerfile

wget -O install.sh https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/blobfuse/deployment/blobfuse-flexvol-installer/install.sh

docker build --no-cache -t andyzhangx/blobfuse-flexvol-installer:1.0 .
docker push andyzhangx/blobfuse-flexvol-installer:1.0
```
