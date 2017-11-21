# gitrepo on Windows is not supported yet as git is not built-in on Windows host now
## 1. create a pod with gitrepo mount on windows
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/gitrepo/aspnet-gitrepo.yaml
```

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po aspnet-gitrepo

```
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath   Type            Reason                  Message
  ---------     --------        -----   ----                    -------------   --------        ------                  -------
  1m            1m              1       default-scheduler                       Normal          Scheduled               Successfully assigned aspnet-gitrepo to 36830k8s9000
  1m            1m              1       kubelet, 36830k8s9000                   Normal          SuccessfulMountVolume   MountVolume.SetUp succeeded for volume "default-token-g35gn"
  1m            1s              8       kubelet, 36830k8s9000                   Warning         FailedMount             MountVolume.SetUp failed for volume "git-volume" : failed to exec 'git clone https://github.com/andyzhangx/Demo.git':
 : executable file not found in %!!(MISSING)P(MISSING)ATH%!!(MISSING)(NOVERB)
```

## 2. enter the pod container to do validation
kubectl exec -it aspnet-gitrepo -- cmd


