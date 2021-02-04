#!/bin/bash

set -euo pipefail

echo "downloading cifs-5.4.0-1039.41.patched.tar.gz ..."
wget -O /tmp/cifs-5.4.0-1039.41.patched.tar.gz https://raw.githubusercontent.com/andyzhangx/demo/master/dev/cifs/cifs-5.4.0-1039.41.patched.tar.gz
cd /tmp/
tar -xvf /tmp/cifs-5.4.0-1039.41.patched.tar.gz
cd cifs-5.4.0-1039.41.patched

echo "build modules ..."
make -C /usr/src/linux-headers-$(uname -r)/ M=$(pwd) modules

echo "install modules ..."
modprobe cifs; rmmod cifs; insmod ./cifs.ko

echo "patched cifs driver installed successfully."
