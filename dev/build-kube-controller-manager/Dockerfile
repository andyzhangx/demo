FROM ubuntu:16.04

ENV DEBIAN_FRONTEND=noninteractive \
    container=docker
	
COPY ./kube-controller-manager /usr/bin/

RUN set -x \
    && apt-get update \
    && apt install wget apt-transport-https ca-certificates -y \
    && wget -q -O- 'https://download.ceph.com/keys/release.asc' | apt-key add - \
    && echo deb https://download.ceph.com/debian-nautilus/ xenial main | tee /etc/apt/sources.list.d/ceph.list \
    && apt-get update \
    && apt-get install -y \
        ceph-common \
        curl \
    && touch /etc/ceph/ceph.conf /etc/ceph/ceph.keyring \
    && apt-get purge -y --auto-remove \
        curl \
	&& chmod +x /usr/bin/kube-controller-manager \
    && rm -rf /var/lib/apt/lists/*
