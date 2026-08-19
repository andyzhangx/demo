#!/usr/bin/env bash
# init.sh — one-shot Kerberos / NFS setup, idempotent-ish.
set -euo pipefail

: "${REALM:=EXAMPLE.COM}"
: "${NFSV4_DOMAIN:=default.svc.cluster.local}"
: "${SERVER_FQDN:=nfs-kerberos-server.default.svc.cluster.local}"
: "${CLIENT_FQDN:=nfs-kerberos-client.default.svc.cluster.local}"
: "${KDC_MASTER_PASSWORD:=masterpw}"

echo "[init] REALM=${REALM}  server=${SERVER_FQDN}  client=${CLIENT_FQDN}"

################################################################################
# /etc/krb5.conf
################################################################################
cat >/etc/krb5.conf <<EOF
[libdefaults]
    default_realm = ${REALM}
    dns_lookup_realm = false
    dns_lookup_kdc = false
    rdns = false
    ticket_lifetime = 24h
    renew_lifetime = 7d
    forwardable = true
    udp_preference_limit = 1

[realms]
    ${REALM} = {
        kdc            = ${SERVER_FQDN}
        admin_server   = ${SERVER_FQDN}
        default_domain = ${NFSV4_DOMAIN}
    }

[domain_realm]
    .${NFSV4_DOMAIN} = ${REALM}
     ${NFSV4_DOMAIN} = ${REALM}
EOF

################################################################################
# /etc/idmapd.conf  — Domain must be a DNS-style name, NOT the realm
################################################################################
cat >/etc/idmapd.conf <<EOF
[General]
Verbosity = 1
Domain = ${NFSV4_DOMAIN}
Local-Realms = ${REALM}

[Mapping]
Nobody-User  = nobody
Nobody-Group = nobody

[Translation]
Method = nsswitch
EOF

################################################################################
# /etc/exports  — allow sys AND krb5 flavors so v4.1 SEQUENCE bring-up works
#                 even before GSS context negotiation completes.
#
# NOTE: we intentionally do NOT set fsid=0 here. Marking /srv/shared as the
# NFSv4 pseudo-root would force clients to mount `server:/`, but README and
# csi-driver-nfs#999 both mount `server:/srv/shared`. Modern nfs-utils walks
# the export tree and synthesizes an implicit pseudo-root, so the client-
# visible NFSv4 path stays `/srv/shared`.
################################################################################
cat >/etc/exports <<EOF
/srv/shared  *(rw,sync,no_root_squash,insecure,no_subtree_check,sec=sys:krb5:krb5i:krb5p)
EOF

################################################################################
# KDC database + principals
################################################################################
mkdir -p /var/lib/krb5kdc
cat >/var/lib/krb5kdc/kdc.conf <<EOF
[kdcdefaults]
    kdc_ports = 88
    kdc_tcp_ports = 88

[realms]
    ${REALM} = {
        database_name        = /var/lib/krb5kdc/principal
        admin_keytab         = FILE:/etc/krb5kdc/kadm5.keytab
        acl_file             = /var/lib/krb5kdc/kadm5.acl
        key_stash_file       = /var/lib/krb5kdc/.k5.${REALM}
        max_life             = 24h 0m 0s
        max_renewable_life   = 7d 0h 0m 0s
        supported_enctypes   = aes256-cts-hmac-sha1-96:normal aes128-cts-hmac-sha1-96:normal
        default_principal_flags = +preauth
    }
EOF

echo "*/admin@${REALM} *" >/var/lib/krb5kdc/kadm5.acl

if [[ ! -f /var/lib/krb5kdc/principal ]]; then
    echo "[init] creating KDC database"
    kdb5_util create -s -P "${KDC_MASTER_PASSWORD}" -r "${REALM}"

    echo "[init] adding server principal nfs/${SERVER_FQDN}@${REALM}"
    kadmin.local -q "addprinc -randkey nfs/${SERVER_FQDN}@${REALM}"
    kadmin.local -q "ktadd -k /etc/krb5.keytab nfs/${SERVER_FQDN}@${REALM}"

    echo "[init] adding client principal host/${CLIENT_FQDN}@${REALM}"
    kadmin.local -q "addprinc -randkey host/${CLIENT_FQDN}@${REALM}"
    kadmin.local -q "ktadd -k /shared/client.keytab host/${CLIENT_FQDN}@${REALM}"
    chmod 0644 /shared/client.keytab

    # Convenience: a test user so krb5 mounts can be validated end-to-end.
    kadmin.local -q "addprinc -pw testpw testuser@${REALM}"
fi

# Publish the realm + client principal info for consumers.
cat >/shared/krb5.conf </etc/krb5.conf
echo "${CLIENT_FQDN}"                        >/shared/client.fqdn
echo "host/${CLIENT_FQDN}@${REALM}"          >/shared/client.principal
echo "${REALM}"                              >/shared/realm

echo "[init] done"
