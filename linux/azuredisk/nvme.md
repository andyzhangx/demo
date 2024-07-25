# NVME disk controller support

```console
# wget -O /etc/udev/rules.d/80-azure-nvme.rules https://raw.githubusercontent.com/Azure/azure-nvme-utils/main/udev/80-azure-nvme.rules.in
wget -O /etc/udev/rules.d/80-azure-nvme.rules https://raw.githubusercontent.com/Azure/SAP-on-Azure-Scripts-and-Utilities/main/NVMe-Preflight-Check/88-azure-nvme-data-disk.rules
cd /tmp/
wget https://download.copr.fedorainfracloud.org/results/cjp256/azure-nvme-utils/opensuse-leap-15.5-x86_64/07402358-azure-nvme-utils/azure-nvme-utils-0.1.3-1.x86_64.rpm
rpm -i azure-nvme-utils-0.1.3-1.x86_64.rpm
udevadm control --reload-rules && udevadm trigger
```
