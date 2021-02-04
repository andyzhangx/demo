#!/bin/bash

set -euo pipefail

wget -O /tmp/cifs-5.4.0-1039.41.patched.tar.gz https://raw.githubusercontent.com/andyzhangx/demo/master/dev/cifs/cifs-5.4.0-1039.41.patched.tar.gz
cd /tmp/
tar -xvf /tmp/cifs-5.4.0-1039.41.patched.tar.gz
cd cifs-5.4.0-1039.41.patched
make -C /usr/src/linux-headers-$(uname -r)/ M=$(pwd) modules
modprobe cifs; rmmod cifs; insmod ./cifs.ko
