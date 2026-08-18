# nfs-kerberos-server

Minimal NFSv4 + MIT KDC image for CI / e2e tests that need to exercise
Kerberos-secured NFS mounts (`sec=krb5`, `krb5i`, `krb5p`).

## Why

Existing public images (e.g. `thealmightydrawingtablet/nfs-krb`) provision
only the server's own principal, use `Domain=<realm>` in `idmapd.conf`, and
export `sec=krb5p:krb5i:krb5` only, which breaks NFSv4.1 session bring-up in
CI. See [csi-driver-nfs#999][csi-nfs-999] for the investigation.

This image fixes all three:

1. Provisions **two** principals — `nfs/${SERVER_FQDN}` (server keytab under
   `/etc/krb5.keytab`) and `host/${CLIENT_FQDN}` (client keytab under
   `/shared/client.keytab`, mount `/shared` into the client pod).
2. `idmapd.conf` `Domain=` is a DNS-style name (`default.svc.cluster.local`
   by default), NOT the realm.
3. Exports `sec=sys:krb5:krb5i:krb5p` so session bring-up works even before
   the GSS context is negotiated, and clients can pick any flavor.

Also publishes convenience files under `/shared`:

| Path                        | Content                                    |
| --------------------------- | ------------------------------------------ |
| `/shared/client.keytab`     | `host/${CLIENT_FQDN}@${REALM}` keytab      |
| `/shared/krb5.conf`         | copy of `/etc/krb5.conf` used by KDC       |
| `/shared/client.fqdn`       | `${CLIENT_FQDN}`                           |
| `/shared/client.principal`  | `host/${CLIENT_FQDN}@${REALM}`             |
| `/shared/realm`             | `${REALM}`                                 |

A convenience user principal `testuser@${REALM}` with password `testpw` is
also created so `kinit testuser` works from any client pod for smoke tests.

## Build

```bash
cd linux/nfs/nfs-kerberos-server
docker build -t <registry>/nfs-kerberos-server:v0.1.0 .
```

## Run in Kubernetes (sketch)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nfs-kerberos-server
spec:
  replicas: 1
  selector: { matchLabels: { app: nfs-kerberos-server } }
  template:
    metadata: { labels: { app: nfs-kerberos-server } }
    spec:
      hostname: nfs-kerberos-server
      subdomain: nfs-kerberos-server
      containers:
        - name: server
          image: <registry>/nfs-kerberos-server:v0.1.0
          securityContext:
            privileged: true          # needs CAP_SYS_ADMIN for rpc_pipefs + nfsd mounts
            capabilities: { add: [SYS_ADMIN, SYS_MODULE] }
          env:
            - { name: REALM,        value: EXAMPLE.COM }
            - { name: NFSV4_DOMAIN, value: default.svc.cluster.local }
            - { name: SERVER_FQDN,  value: nfs-kerberos-server.default.svc.cluster.local }
            - { name: CLIENT_FQDN,  value: csi-nfs-controller.default.svc.cluster.local }
          ports:
            - { name: nfs,   containerPort: 2049 }
            - { name: kdc,   containerPort: 88 }
            - { name: kadm,  containerPort: 749 }
```

On the client (e.g. csi-driver-nfs controller pod):

```bash
# Distribute /shared/client.keytab + /shared/krb5.conf via a Secret or
# ReadWriteMany volume, then in the client init container:
cp /nfs-krb-shared/krb5.conf     /etc/krb5.conf
cp /nfs-krb-shared/client.keytab /etc/krb5.keytab
rpc.gssd -vf &

mount -t nfs4 -o sec=krb5,vers=4.1 \
    nfs-kerberos-server.default.svc.cluster.local:/srv/shared /mnt/nfs
```

## Environment variables

| Var                    | Default                                             |
| ---------------------- | --------------------------------------------------- |
| `REALM`                | `EXAMPLE.COM`                                       |
| `NFSV4_DOMAIN`         | `default.svc.cluster.local`                         |
| `SERVER_FQDN`          | `nfs-kerberos-server.default.svc.cluster.local`     |
| `CLIENT_FQDN`          | `nfs-kerberos-client.default.svc.cluster.local`     |
| `KDC_MASTER_PASSWORD`  | `masterpw`                                          |

## Status

Draft — used to unblock the Kerberos e2e in [csi-driver-nfs#999][csi-nfs-999].
Once validated we should promote it to `registry.k8s.io/sig-storage/nfs-server-krb`
via the k8s image-promoter.

[csi-nfs-999]: https://github.com/kubernetes-csi/csi-driver-nfs/pull/999
