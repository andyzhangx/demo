# Azure File CSI Snapshot Restore behind Storage Firewall — Analysis

Related upstream issue: [kubernetes-sigs/azurefile-csi-driver#2121](https://github.com/kubernetes-sigs/azurefile-csi-driver/issues/2121)

**Scenario**: The storage account has `publicNetworkAccess = "Selected networks"` (or `Disabled`). Restoring a PVC from a `VolumeSnapshot` fails with:

```
RESPONSE 403: 403 This request is not authorized to perform this operation.
ERROR CODE: AuthorizationFailure
```

This document explains why the failure happens, what does and does not fix it, and what the theoretical clean solution looks like.

---

## 1. Where the CSI controller actually runs

For the **AKS managed Azure File CSI driver add-on**, the `csi-azurefile-controller` Deployment runs inside the **AKS-managed control plane (hcp)**, not on the user's nodepool.

Consequences:
- Its outbound traffic exits from the **Microsoft-managed underlay/overlay network**, not from the customer's vnet.
- The source IP is a floating MSFT-owned IP; the customer cannot know it or add it to a firewall allowlist.
- Adding customer subnets to storage "Selected networks" has no effect on this pod, because the traffic never traverses those subnets.

This is the root architectural cause of the #2121 behavior.

---

## 2. Management plane vs data plane — why `CreateFileShare` works but snapshot restore doesn't

Azure Storage exposes two independent endpoints:

| Plane | Endpoint | Owner | Storage firewall applies? |
|---|---|---|---|
| Management (SRP / ARM) | `management.azure.com/.../Microsoft.Storage/storageAccounts/<a>/fileServices/default/shares/<s>` | Azure Resource Manager | **No** |
| Data plane | `<account>.file.core.windows.net/<share>/...` | Storage service front-end | **Yes** |

The account-level **Networks** blade only guards the **data plane** endpoint.

In `controllerserver.go`:

```go
// L726
if err := d.CreateFileShare(ctx, accountOptions, shareOptions, secret, useDataPlaneAPI); err != nil {
```

- `useDataPlaneAPI` empty / `"false"` (default) → uses `armstorage.FileSharesClient.Create` → **ARM path** → only needs `Storage Account Contributor` RBAC → **not blocked by storage firewall**.
- `useDataPlaneAPI="true"` → hits `<account>.file.core.windows.net` → **blocked**.

This is why file share create/delete/resize from hcp works even with the firewall enabled: it uses the ARM path.

**Snapshot restore is different** — the data copy has no ARM equivalent:

```go
// L1371 in copyFileShareByAzcopy
cmd := exec.Command("azcopy", "copy", srcPath, dstPath)
```

`azcopy copy` always hits `<account>.file.core.windows.net`. There is no server-side share-to-share copy management API in Azure Files (Blob has [Copy Blob](https://learn.microsoft.com/en-us/rest/api/storageservices/copy-blob), Files does not). So snapshot restore **must** go through the data plane endpoint, and therefore **must** pass through the firewall.

---

## 3. Why identity-based fixes don't help

### 3.1 `useDataPlaneAPI: "oauth"` (added in v1.33.0)

Source (L1474):

```go
if d.cloud != nil && d.cloud.AuthProvider != nil && strings.EqualFold(useDataPlaneAPI, oauth) {
    fileClient, err = newAzureFileClientWithOAuth(d.cloud.AuthProvider.GetAzIdentity(), ...)
}
```

`oauth` only affects **SDK-based data plane calls** the driver itself makes (`snapshotExists`, `getFileShareQuota`, `getShareClient`) — swapping shared key for OAuth token. It has **no effect on the AzCopy subprocess** that actually copies snapshot data.

### 3.2 `Storage File Data Privileged Contributor` role

The role assignment only affects the **authZ layer**. Source (L760):

```go
klog.Warningf("azcopy copy failed with AuthorizationPermissionMismatch error,
    should assign \"Storage File Data Privileged Contributor\" role to controller identity,
    fall back to use sas token, original error: %v", copyErr)
```

Effect: lets AzCopy authenticate via OAuth without falling back to shared key. Good for the "shared key disabled" security posture. **Does not bypass the firewall.**

### 3.3 `authorizeAzcopyWithIdentity`

`authorizeAzcopyWithIdentity` (L1593) only sets environment variables (`AZCOPY_AUTO_LOGIN_TYPE=MSI`, `AZCOPY_MSI_CLIENT_ID=...`). It performs **no network call**.

At `azcopy copy` execution time:

1. AzCopy calls IMDS `http://169.254.169.254/metadata/identity/oauth2/token?...` — **host-local**, not subject to storage firewall.
2. AzCopy sends `GET https://<account>.file.core.windows.net/...` with `Authorization: Bearer <token>` — **hits storage firewall first**, gets 403 before the token is even inspected.

### 3.4 The processing order that dooms all identity-based fixes

```
TCP/TLS → Network ACL (firewall / vnet rules / PE) → AuthN (SAS / OAuth) → AuthZ (RBAC / ACL)
                       ↑
                 #2121 fails here
```

The firewall evaluates **network origin only** (source IP / subnet resource ID). No `Authorization` header is read. Therefore no identity, role, or token type can change the outcome.

---

## 4. Why the "obvious" workarounds also don't work for #2121

Because the CSI controller runs inside hcp (not in the customer vnet), the following fail:

| Attempted workaround | Reason it fails |
|---|---|
| Add AKS vnet/subnet to storage "Selected networks" | Traffic doesn't originate in customer vnet — hcp outbound is MSFT-owned |
| Private Endpoint on storage account bound to AKS node vnet | Private DNS zone linked to customer vnet is not visible from hcp; PE private IP is not routable from hcp |
| Enable `Microsoft.Storage` service endpoint on the system nodepool subnet | Same reason — the request is not sourced from that subnet |
| NAT Gateway to pin an egress IP | hcp egress IPs are MSFT-managed and not exposed to the customer |
| "Allow trusted Microsoft services to access this storage account" | The trusted-services list is a fixed set (Backup, Site Recovery, Azure Monitor, Event Grid, etc.). **AKS / AKS managed CSI is not in this list.** |
| Resource instance rules today | Storage RP's supported `resource type` allowlist includes AzureML, Synapse, Data Factory, Cosmos DB, HDInsight, ACR task run, Fabric, Cognitive Search, etc. **`Microsoft.ContainerService/managedClusters` is not currently supported.** |

`az storage file copy start` is also **not** a true server-side bypass here — the initiating `PUT ...?comp=copy` request still hits the data plane endpoint on `<account>.file.core.windows.net`, so it is subject to the same firewall.

---

## 5. What actually works today

Given the current architecture, only these options let snapshot restore succeed:

### 5.1 Temporarily enable public network access on the storage account

Documented in the issue. The customer flips `publicNetworkAccess=Enabled` for the duration of restore, then flips it back. Supported but obviously undesirable.

### 5.2 Skip CSI `VolumeSnapshot` restore — use static PV against `shareSnapshotName`

Directly mount the snapshot read-only from the node plugin (which runs on customer nodes and can traverse PE / vnet rules):

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-from-snapshot
spec:
  csi:
    driver: file.csi.azure.com
    volumeHandle: <rg>#<account>#<share>#<snapshot-ts>
    volumeAttributes:
      shareSnapshotName: "2026-07-30T04:00:00.0000000Z"
```

Loses K8s-native `VolumeSnapshot` / `VolumeSnapshotContent` automation, but the network path is clean because the node plugin runs on the user nodepool.

### 5.3 Run AzCopy from a customer pod (out-of-band restore Job)

Bypass the CSI restore flow entirely; do the copy from a pod on the user nodepool that can traverse a Private Endpoint:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: fileshare-restore
  namespace: kube-system
spec:
  template:
    spec:
      serviceAccountName: azurefile-restore-sa   # workload-identity bound to UAMI
      containers:
        - name: azcopy
          image: mcr.microsoft.com/azure-cli:latest   # or custom image with azcopy
          command:
            - /bin/sh
            - -c
            - |
              export AZCOPY_AUTO_LOGIN_TYPE=MSI
              azcopy copy \
                "https://<acct>.file.core.windows.net/<src>?sharesnapshot=<ts>" \
                "https://<acct>.file.core.windows.net/<dst>" \
                --recursive --preserve-smb-permissions=true
      restartPolicy: Never
```

Prerequisites: Private Endpoint on the storage account bound to the AKS node vnet, private DNS zone `privatelink.file.core.windows.net` linked to the vnet, UAMI has `Storage File Data Privileged Contributor` on the storage account.

Fully satisfies **"no firewall allowlist entry, public access disabled, AzCopy still used for data plane copy"** — but the customer has to author / operate the Job orchestration themselves.

### 5.4 Application-level backup (Velero + restic / kopia)

Traffic streams through customer pods to backup storage. Bypasses CSI snapshot mechanics entirely.

---

## 6. The clean theoretical fix — Resource Instance rules for AKS

The only Azure-native way to have identity **actually** cross a storage firewall is a **Resource Instance rule**:

- Firewall reads the `Authorization: Bearer <token>` header
- Matches the token's `oid` against an allowlist of "resource instance" identities
- If it matches, the request is permitted regardless of source IP

If Azure Storage RP added `Microsoft.ContainerService/managedClusters` to the supported resource types, the configuration would become:

```
Storage account
└── Networking
    └── Resource instances
        └── Resource type: Microsoft.ContainerService/managedClusters
            Instance: <aks-cluster-resource-id>
```

### Why this would work end-to-end

1. hcp CSI controller uses the AKS **control plane MI** via `AZCOPY_AUTO_LOGIN_TYPE=MSI`.
2. AzCopy obtains an AAD token from IMDS whose `oid` matches the control plane MI principal ID.
3. AzCopy issues `GET https://<account>.file.core.windows.net/...` with `Authorization: Bearer <token>`.
4. Storage firewall reads the token, matches `oid` against the resource instance allowlist, **permits**.
5. AuthZ layer checks RBAC (needs `Storage File Data Privileged Contributor`) → passes.
6. Copy succeeds.

Verified against source: `authorizeAzcopyWithIdentity` in hcp defaults to system-assigned MSI (`azureAuthConfig.UserAssignedIdentityID` is empty), which is the cluster's control plane MI. Token `oid` therefore equals control plane MI principal ID, matching the resource instance entry.

### Preconditions

- **Shared key access should be disabled** on the storage account. Otherwise the fallback path (L760) can still issue SAS, which has no `oid` and can't match the resource instance rule.
- Storage RP must support `Microsoft.ContainerService/managedClusters` as a resource instance type. **This is the blocking gap today.**

### End-to-end config (future)

```bash
# 1) Storage account resource instance rule (future API)
az storage account network-rule add \
  --resource-id /subscriptions/.../managedClusters/<cluster-name> \
  ...

# 2) RBAC
az role assignment create \
  --assignee <control-plane-mi-principal-id> \
  --role "Storage File Data Privileged Contributor" \
  --scope <storage-account-id>

# 3) StorageClass — default AzCopy identity path
```

No PE, no vnet allowlist, no public access. Matches exactly what customers ask for.

---

## 7. Summary

| Question | Answer |
|---|---|
| Does `useDataPlaneAPI: "oauth"` fix snapshot restore behind firewall? | No — only affects SDK calls, not AzCopy. |
| Does assigning `Storage File Data Privileged Contributor` fix it? | No — it fixes authZ only; firewall precedes authZ. |
| Does the control plane MI's OAuth token cross the firewall? | No — firewall is source-based; identity is not inspected. |
| Why does `CreateFileShare` from hcp succeed? | It uses the ARM management plane, which is not subject to storage firewall. |
| Does Private Endpoint on the customer vnet help? | No, for the managed add-on — controller runs in hcp, not in the customer vnet. |
| Trusted Microsoft services? | AKS is not in the list. |
| Resource instance rules? | AKS is not in the supported resource types today. Would be the clean fix if added. |
| What works today? | Temporary public access, static PV with `shareSnapshotName`, out-of-band Job running AzCopy from a customer pod (with PE), or app-layer backup. |
| What is the right long-term fix? | Storage RP adds `Microsoft.ContainerService/managedClusters` to Resource Instance rule types. |

---

*Reference: [`pkg/azurefile/controllerserver.go`](https://github.com/kubernetes-sigs/azurefile-csi-driver/blob/master/pkg/azurefile/controllerserver.go) (verified line references from master as of analysis).*
