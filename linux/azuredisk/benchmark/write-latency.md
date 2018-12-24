#Latency of small sized disk writes
Lets measure compare disk write latencies for 1024Gb data disk
 
Azure instance: Standard_DS3_v2 +  1024Gb Premium managed data disk (cache=None) 
Aws instance: m5.xlarge + 1024Gb EBS gp2 
 
by timing of `dd if=/dev/zero of=/mnt/disk1/512b-latency bs=512 count=1000 oflag=direct`
 
The "real" value of the command below dividing by 10000 gives us a delay on write operations (write time of 512 bytes can be ignored)
```
time for ii in {1..10}; do echo "$ii ..."; dd if=/dev/zero of=/mnt/disk1/512b-latency bs=512 count=1000 oflag=direct; done
```
