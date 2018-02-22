#!/bin/bash

set -eo pipefail

LOG="/var/log/blobfuse-flexvol-installer.log"
target_dir="${TARGET_DIR}"

if [[ -z "${target_dir}" ]]; then
  target_dir="/etc/kubernetes/volumeplugins"
fi

apt-get update && apt-get install wget -y >>$LOG

blobfuse_vol_dir="${target_dir}/azure~blobfuse"
blobfuse_bin_dir="${blobfuse_vol_dir}/bin"
mkdir -p ${blobfuse_bin_dir}

#download blobfuse binary
version="v1.9"
if [[ -z "${KUBELET_VERSION}" ]]; then
	echo "ERR: could not get env var: KUBELET_VERSION, use default kubelet version ${version}" >>$LOG
else
	version=`echo ${KUBELET_VERSION} | awk -F '.' '{print $1"."$2}'`
fi

wget -O ${blobfuse_bin_dir}/blobfuse https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/blobfuse/binary/kubelet/$version/blobfuse >>$LOG	
chmod a+x ${blobfuse_bin_dir}/blobfuse

#download blobfuse script
wget -O ${blobfuse_vol_dir}/blobfuse https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/blobfuse/blobfuse >>$LOG	
chmod a+x ${blobfuse_vol_dir}/blobfuse

#https://github.com/kubernetes/kubernetes/issues/17182
# if we are running on kubernetes cluster as a daemon set we should
# not exit otherwise, container will restart and goes into crashloop (even if exit code is 0)
while true; do echo "install done, daemonset sleeping" && sleep 30; done
