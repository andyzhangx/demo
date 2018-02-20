#!/bin/bash

set -eo pipefail

target_dir="${TARGET_DIR}"

if [[ -z "${target_dir}" ]];then
  target_dir="/etc/kubernetes/volumeplugins"
fi

blobfuse_vol_dir="${target_dir}/azure~blobfuse"
blobfuse_bin_dir="${blobfuse_vol_dir}/bin"
mkdir -p ${blobfuse_bin_dir}

cp /usr/bin/blobfuse ${blobfuse_bin_dir}/		#binary
cp /root/blobfuse ${blobfuse_vol_dir}/blobfuse 	#script
cp /usr/bin/jq ${blobfuse_vol_dir}/jq

#https://github.com/kubernetes/kubernetes/issues/17182
# if we are running on kubernetes cluster as a daemon set we should
# not exit otherwise, container will restart and goes into crashloop (even if exit code is 0)
while true; do echo "install done, daemonset sleeping" && sleep 30; done
