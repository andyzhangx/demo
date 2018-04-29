## 1. Build nginx-server image
```
cd nginx-server-image
docker build --no-cache -t andyzhangx/nginx-server:1.0.0 .
```
## 2. Test nginx-server image
```
docker run -d --name nginx -p 80:80 andyzhangx/nginx-server:1.0.0
curl http://127.0.0.1
docker stop nginx && docker rm nginx
```

## 3. Push nginx-server image
```
docker login
docker push andyzhangx/nginx-server:1.0.0
```
