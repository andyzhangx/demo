## 1. install flex volume driver on every Windows node
make a plugin directory, e.g. `C:\volumeplugins\test~example.cmd` and put driver file https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/flexvolume/example.cmd under `C:\volumeplugins\test~example.cmd`

## 2. specify `volume-plugin-dir` value for Windows kubelet service
edit file `c:\k\kubeletstart.ps1`, append following config
```
--volume-plugin-dir=c:\volumeplugins
```

## 3. create a pod with flexvolume mount on Windows
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/flexvolume/aspnet-flex-example.yaml

#### watch the status of pod until its Status changed from `Pending` to `Running`
watch kubectl describe po aspnet-flex-example

## 4. enter the pod container to do validation
kubectl exec -it aspnet-flex-example -- cmd

```
Microsoft Windows [Version 10.0.14393]
(c) 2016 Microsoft Corporation. All rights reserved.

C:\>dir
 Volume in drive C has no label.
 Volume Serial Number is F4B3-1384

 Directory of C:\
12/07/2017  03:54 AM    <SYMLINKD>     data [\\?\ContainerMappedDirectories\8022AF84-E3B2-44AC-9BB5-9B733C92E6B8]
12/07/2017  03:54 AM    <DIR>          inetpub
11/22/2016  10:45 PM             1,894 License.txt
07/16/2016  01:18 PM    <DIR>          PerfLogs
11/03/2017  07:14 PM    <DIR>          Program Files
11/14/2017  11:48 PM    <DIR>          Program Files (x86)
11/15/2017  12:09 AM    <DIR>          RoslynCompilers
10/18/2017  04:01 PM           126,632 ServiceMonitor.exe
12/07/2017  03:54 AM    <DIR>          Users
12/07/2017  03:54 AM    <DIR>          var
12/07/2017  04:27 AM    <DIR>          Windows
               2 File(s)        128,526 bytes
               9 Dir(s)  21,129,273,344 bytes free

C:\>cd data
C:\data>dir
 Volume in drive C has no label.
 Volume Serial Number is F4B3-1384

 Directory of C:\data
12/07/2017  03:37 AM    <DIR>          .
12/07/2017  03:37 AM    <DIR>          ..
               0 File(s)              0 bytes
               2 Dir(s)  100,983,214,080 bytes free
```

### Known issues
1. You may get following error in the kubelet log when trying to use a flexvolume driver written by yourself:
```
Volume has not been added to the list of VolumesInUse
```
You could let flexvolume plugin return following:
```
echo {"status": "Success", "capabilities": {"attach": false}}
```
Which means your [FlexVolume driver does not need Master-initiated Attach/Detach](https://docs.openshift.org/latest/install_config/persistent_storage/persistent_storage_flex_volume.html#flex-volume-drivers-without-master-initiated-attach-detach)

### Links
[Flexvolume doc](https://github.com/kubernetes/community/blob/master/contributors/devel/flexvolume.md)

More clear steps about flexvolume by Redhat doc: [Persistent Storage Using FlexVolume Plug-ins](https://docs.openshift.org/latest/install_config/persistent_storage/persistent_storage_flex_volume.html)
