# syntax=docker/dockerfile:1
#
# nfs-kerberos-server: minimal NFSv4 + MIT KDC image for CI/e2e.
#
# Provisions two principals in an in-container KDC:
#   * nfs/${SERVER_FQDN}@${REALM}          -> server host key (/etc/krb5.keytab)
#   * host/${CLIENT_FQDN}@${REALM}         -> client machine key (/shared/client.keytab)
#
# The client keytab is written under /shared so callers can mount that path
# into their NFS client pod (via emptyDir or hostPath) and use it with
# `rpc.gssd -k /shared/client.keytab`.
#
# Exports /srv/shared with `sec=sys:krb5:krb5i:krb5p` so v4.1 session bring-up
# does not depend on GSS succeeding first, and clients can pick any flavor.
#
# Build: docker build -t <registry>/nfs-kerberos-server:v0.1.0 .

FROM alpine:3.22

ARG NFSV4_DOMAIN=default.svc.cluster.local
ARG REALM=EXAMPLE.COM
ARG SERVER_FQDN=nfs-kerberos-server.default.svc.cluster.local
ARG CLIENT_FQDN=nfs-kerberos-client.default.svc.cluster.local

ENV NFSV4_DOMAIN=${NFSV4_DOMAIN} \
    REALM=${REALM} \
    SERVER_FQDN=${SERVER_FQDN} \
    CLIENT_FQDN=${CLIENT_FQDN}

RUN apk add --no-cache \
        bash \
        openrc \
        nfs-utils \
        krb5 \
        krb5-server \
        rpcbind \
        tini \
    && rm -rf /var/cache/apk/*

RUN mkdir -p /srv/shared /shared /var/lib/nfs/rpc_pipefs /var/lib/nfs/v4recovery \
    && chmod 0777 /srv/shared

COPY entry.sh /entry.sh
COPY init.sh  /init.sh
RUN  chmod +x /entry.sh /init.sh

# NFSv4 TCP (2049), MOUNTD (20048), portmap (111), KDC (88), kadmin (749)
EXPOSE 2049/tcp 20048/tcp 111/tcp 111/udp 88/tcp 88/udp 749/tcp

ENTRYPOINT ["/sbin/tini", "--", "/entry.sh"]
