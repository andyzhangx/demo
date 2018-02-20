FROM ubuntu:16.04
RUN apt-get update
RUN apt-get install apt-transport-https jq wget -y
RUN wget -O /tmp/packages-microsoft-prod.deb https://packages.microsoft.com/config/ubuntu/16.04/packages-microsoft-prod.deb
RUN dpkg -i /tmp/packages-microsoft-prod.deb
RUN apt-get update
RUN apt-get install blobfuse fuse -y
RUN wget -O /root/blobfuse https://raw.githubusercontent.com/andyzhangx/Demo/master/linux/flexvolume/blobfuse/blobfuse

ADD ./install.sh /bin/install_blobfuse_flexvol.sh

ENTRYPOINT ["/bin/install_blobfuse_flexvol.sh"]
