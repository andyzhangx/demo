## How to update hyperkube image directly in k8s master (only applies to Ubuntu OS now)

#### 1. `scp _output/bin/hyperkube` to `/tmp/` on k8s master node and log on master node first
```
cd /tmp/
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/dev/update-k8s.perl
chmod a+x update-k8s.perl
sudo ./update-k8s.perl hyperkube
```
After a while, your controller-manager, apiserver and scheduler will be replaced by new `hyperkube` image(`aztest/hyperkube`), you could check the new image by run `docker ps`, below is an example:
```
azureuser@k8s-master-31586635-0:~$ docker images
REPOSITORY                                                       TAG                                         IMAGE ID            CREATED             SIZE
aztest/hyperkube                                                 20171211064107                              a7f129b24ec2        2 days ago     
       744.2 MB
gcrio.azureedge.net/google_containers/hyperkube-amd64            v1.8.2                                      8dc8847d478f        7 weeks ago         503.2 MB
gcrio.azureedge.net/google_containers/kube-addon-manager-amd64   v6.4-beta.2                                 0a951668696f        6 months ago        79.24 MB
gcrio.azureedge.net/google_containers/pause-amd64                3.0                                         99e59f495ffa        19 months ago       746.9 kB
```

Note:
You could check following config files to check the hyperkube image 
```
sudo vi /etc/kubernetes/manifests/kube-apiserver.yaml
sudo vi /etc/kubernetes/manifests/kube-scheduler.yaml
sudo vi /etc/kubernetes/manifests/kube-controller-manager.yaml
```

#### 2. kubelet image is not replaced automatcially, you need to replace with `aztest/hyperkube:20171211064107` image by:
```
sudo vi /etc/default/kubelet
#edit column name KUBELET_IMAGE
KUBELET_IMAGE=aztest/hyperkube:20171211064107
sudo systemctl restart kubelet
```

#### 3. How to push new `aztest/hyperkube:20171211064107` image to docker registry
```
docker tag aztest/hyperkube:20171211064107 YOURREPO/hyperkube:20171211064107
docker push YOURREPO/hyperkube:20171211064107
```

