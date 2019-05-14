#! /bin/sh

/usr/bin/curl http://localhost:10252/metrics | grep cloudprovider_azure_api_request | grep -e sum -e count | grep _disk >> /var/log/attach-detach-disk-monitor.txt
