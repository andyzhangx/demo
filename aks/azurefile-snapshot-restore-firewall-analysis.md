# Azure File CSI Snapshot Restore behind Storage Firewall — Analysis

Related upstream issue: [kubernetes-sigs/azurefile-csi-driver#2121](https://github.com/kubernetes-sigs/azurefile-csi-driver/issues/2121)

**Scenario**: The storage account has `publicNetworkAccess = "Selected networks"` or `Disabled`. Restoring a PVC from a `VolumeSnapshot`, or checking snapshot state, fails with:

```
RESPONSE 403: 403 This request is not authorized to perform this operation.
ERROR CODE: AuthorizationFailure
```

## TL;DR (2026-07 status)

**This scenario now works with pure configuration**, via the AKS Trusted Microsoft Service integration on the Storage side.

Required setup:

| # | Config |
|---|---|
| 1 | AKS version rolled out with `storage.azure.com/` + `management.azure.com/` audience registered in the hcp `msi-adapter` (audience config landed 2026-06-12; trailing-slash fix landed 2026-06-22; validated end-to-end by Storage 2026-06-25) |
| 2 | `useDataPlaneAPI: "oauth"` set on the `VolumeSnapshotClass` (and `StorageClass` where relevant) |
| 3 | AKS control plane MI has **`Storage File Data Privileged Contributor`** on the storage account |
| 4 | Storage account `networkRuleSet.bypass` includes `AzureServices` (this is the default) |
| 5 | (Recommended) Shared key access disabled on the storage account so the CSI driver cannot silently fall back to SAS |

Validated by Storage team (Mayank Aggarwal, 2026-06-25) across:

- SMB: All networks / Selected networks / Public disabled / Selected networks + PE / Public disabled + PE
- NFS: Selected networks + PE / Public disabled + PE

No Private Endpoint on the AKS side, no vnet allowlist, no public network access required.

---

## 1. Where the CSI controller actually runs

For the **AKS managed Azure File CSI driver add-on**, the `csi-azurefile-controller` Deployment runs inside the **AKS-managed control plane (hcp)**, not on the user's nodepool.

Consequences that shape the rest of this document:
- Outbound traffic exits from Microsoft-managed underlay, not from the customer's vnet.
- Source IP is not routable / not knowable from the customer side; any workaround based on "add my subnet / my NAT / my PE to the storage firewall" is by construction ineffective for this pod.
- Anything that lets snapshot operations succeed against a firewalled storage account must therefore work **inside the token**, not by making the storage account trust the network origin.

---

## 2. Management plane vs data plane — why `CreateFileShare` was never blocked

Azure Storage exposes two independent endpoints:

| Plane | Endpoint | Owner | Storage firewall applies? |
|---|---|---|---|
| Management (SRP / ARM) | `management.azure.com/.../Microsoft.Storage/storageAccounts/<a>/fileServices/default/shares/<s>` | Azure Resource Manager | **No** |
| Data plane | `<account>.file.core.windows.net/<share>/...` | Storage service front-end | **Yes** |

`controllerserver.go` (`CreateFileShare`, L726):

```go
if err := d.CreateFileShare(ctx, accountOptions, shareOptions, secret, useDataPlaneAPI); err != nil {
```

- `useDataPlaneAPI` empty / `"false"` (default) → `armstorage.FileSharesClient.Create` → ARM path → only needs `Storage Account Contributor` RBAC → **not subject to storage firewall**.
- `useDataPlaneAPI="true"` → `share.Client.Create` → hits `<account>.file.core.windows.net` → **subject to firewall**.

So file share create/delete/resize from hcp has always succeeded through firewalled accounts because it uses ARM. Same story for snapshot metadata operations that have a SRP path.

The **data copy for snapshot restore has no ARM equivalent** — Azure Files doesn't expose a server-side share-to-share copy management API (Blob has [Copy Blob](https://learn.microsoft.com/en-us/rest/api/storageservices/copy-blob), Files does not). Driver source (L1371 in `copyFileShareByAzcopy`):

```go
cmd := exec.Command("azcopy", "copy", srcPath, dstPath)
```

`azcopy copy` always hits `<account>.file.core.windows.net`. **Any solution for #2121 must therefore let the data-plane request survive the firewall check.**

---

## 3. The actual firewall evaluation order (updated)

An earlier revision of this document claimed firewall is purely network-based. **That was wrong.** The real order is:

```
TCP/TLS
   ↓
Network rules (Selected networks: IP allow, subnet allow, PE)
   ↓ if none match
Bypass rules (networkRuleSet.bypass: None | Logging | Metrics | AzureServices)
   ↓ if AzureServices is set, and the caller token is recognized as a trusted MSFT service
   ↓        ↑ this is where the identity-based bypass lives
AuthN (SAS validation / OAuth token validation)
   ↓
AuthZ (RBAC / share ACL)
```

- Storage recognizes a caller as a "trusted Microsoft service" by inspecting **`xms_az_tm` claim** in the OAuth token (`xms_az_tm=azureinfra` is the trusted-infrastructure trust mode).
- **The claim is not something AAD issues automatically for any MSI request.** It has to be requested by an intermediary — for AKS, that intermediary is the hcp-side `msi-adapter` sidecar. The msi-adapter has a hard-coded per-client audience allowlist:

```go
"msi-adapter/csi-azurefile-controller": {
    s.cloudEnvCfg.ResourceIdentifiers.Storage: true,           // storage.azure.com/
    s.cloudEnvCfg.ServiceManagementEndpoint:  true,            // management.azure.com/
    s.cloudEnvCfg.TokenAudience:              true,
},
```

  When csi-azurefile-controller asks IMDS for a token, IMDS → msi-adapter → AAD, and the trusted-service claim is injected only for these audiences.

- Storage's default `networkRuleSet.bypass` includes `AzureServices`, so once the token is identified as trusted service the firewall is skipped and evaluation proceeds to authN/authZ.

- Nothing about the network path changes — DNS still resolves `<acct>.file.core.windows.net` to a public IP, request still traverses the same hcp egress. What changes is only the firewall's decision.

---

## 4. Why this only lights up when `useDataPlaneAPI: "oauth"` is set

Trusted-service bypass requires the request to actually reach storage carrying the OAuth Bearer token whose `xms_az_tm` claim can be inspected. Two CSI code paths matter:

### 4.1 SDK data plane calls (`snapshotExists`, `getFileShareQuota`, `getShareClient`, `CreateFileShare`)

`controllerserver.go` L1474:

```go
if d.cloud != nil && d.cloud.AuthProvider != nil && strings.EqualFold(useDataPlaneAPI, oauth) {
    fileClient, err = newAzureFileClientWithOAuth(d.cloud.AuthProvider.GetAzIdentity(), ...)
}
```

- `useDataPlaneAPI = ""` or `"false"` → SRP / ARM path → not applicable (already always worked).
- `useDataPlaneAPI = "true"` → data plane with **shared key** → no OAuth token → no `xms_az_tm` claim → **still blocked**.
- `useDataPlaneAPI = "oauth"` → data plane with **OAuth token via `AzIdentity`** → token from hcp MSI adapter carries `xms_az_tm=azureinfra` → **trusted service bypass fires**.

This is why simply setting `useDataPlaneAPI: "oauth"` on the snapshotclass unblocks the `snapshotExists` 403 that #2121 reports.

### 4.2 AzCopy subprocess (`copyFileShareByAzcopy` → `execAzcopyCopy`)

`controllerserver.go` L1593 (`authorizeAzcopyWithIdentity`):

```go
authAzcopyEnv = append(authAzcopyEnv, fmt.Sprintf("%s=%s", azcopyAutoLoginType, MSI))
```

- Sets `AZCOPY_AUTO_LOGIN_TYPE=MSI` (+ optional `AZCOPY_MSI_CLIENT_ID`).
- AzCopy at runtime queries IMDS from inside the csi-azurefile-controller pod → **same IMDS → same msi-adapter → same trusted-service claim** is included in the token AzCopy uses to authenticate its `<acct>.file.core.windows.net` calls.
- Prerequisite for this path to actually be used instead of SAS fallback (L760):

  ```go
  klog.Warningf("azcopy copy failed with AuthorizationPermissionMismatch error,
      should assign \"Storage File Data Privileged Contributor\" role ...")
  ```

  If RBAC is missing, driver falls back to SAS; SAS has no `xms_az_tm`, trusted-service bypass will not fire on the retry, and the customer sees 403 again. Hence the **`Storage File Data Privileged Contributor` role assignment is mandatory** for the AzCopy path.

The `useDataPlaneAPI="oauth"` value is what the customer configures at storage-class/snapshot-class level; it also has the side-effect of the SDK OAuth path above, so the whole flow is consistent.

---

## 5. What was rolled out to enable this

Timeline reconstructed from the storage / AKS trusted-service thread:

| Date (2026) | Change | Where |
|---|---|---|
| 06-12 | Added `storage.azure.com/` audience to msi-adapter trusted-service client list for `csi-azurefile-controller` | AKS internal repo |
| 06-12 | Also added `management.azure.com/` audience | AKS internal repo |
| 06-22 | Fixed trailing-slash mismatch — csi-azurefile-controller was requesting audience `https://storage.azure.com` (no trailing slash) but msi-adapter matched with slash → trusted-service claim was silently dropped | AKS internal repo |
| 06-24 | Mayank validates all SMB + NFS scenarios successfully (Selected networks / Public disabled, with and without PE) | Test cluster |
| 06-25 | Storage side confirms trusted-service integration correct | — |

Any AKS release cut before ~2026-06-22 will not have the trailing-slash fix and will still hit 403 even with all customer-side config right.

---

## 6. Prerequisites — full checklist

For **snapshot create + restore (SMB and NFS)** against a private storage account:

1. **AKS release** with:
   - msi-adapter `storage.azure.com/` audience for `csi-azurefile-controller` — ✅ landed 2026-06-12
   - Trailing-slash fix — ✅ landed 2026-06-22
   - Rolled out to the target region (check via [Rollout dashboard](https://ev2portal.azure.net/)).

2. **VolumeSnapshotClass / StorageClass parameters**:
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   parameters:
     useDataPlaneAPI: "oauth"      # required
     # ... other params
   ```

3. **RBAC on the AKS control plane MI**:
   ```bash
   PRINCIPAL_ID=$(az aks show -g <rg> -n <cluster> --query identity.principalId -o tsv)
   az role assignment create \
     --assignee-object-id "$PRINCIPAL_ID" \
     --assignee-principal-type ServicePrincipal \
     --role "Storage File Data Privileged Contributor" \
     --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<acct>
   ```
   The `Storage Account Contributor` role is also often present for management plane operations; both roles can coexist. `Storage File Data Privileged Contributor` is the one that unblocks OAuth-authenticated data-plane traffic without falling back to SAS.

4. **Storage account settings**:
   - `networkAcls.bypass` includes `AzureServices` — default, verify it hasn't been explicitly set to `None`.
   - Optional but strongly recommended: `allowSharedKeyAccess = false`. Prevents the driver from silently landing on SAS-based auth, which would bypass the whole trusted-service path and re-introduce 403.

5. **Storage account firewall** — no changes needed on the customer side. Selected networks list can remain empty; PE optional; public network access can be `Disabled`.

Failure of any of 1/2/3/4 will typically manifest as:

- 1 (release) → 403 identical to pre-fix behavior
- 2 (`useDataPlaneAPI` not set) → 403 (driver uses SDK data plane with shared key, or ARM path for calls that have no data-plane fallback)
- 3 (RBAC) → 403 `AuthorizationPermissionMismatch`, driver falls back to SAS on AzCopy, which then gets 403 `AuthorizationFailure` since SAS ≠ trusted service
- 4 (bypass) → 403 (trusted-service claim present but bypass rule not honored)

---

## 7. What this replaces from the earlier analysis

Earlier revisions of this document argued that no pure-configuration bypass existed and proposed workarounds like running AzCopy from a customer pod, static PV with `shareSnapshotName`, temporary public-access flips, or Velero. **Those are no longer needed** on releases that carry the trusted-service audience fixes.

Statements from the earlier analysis that are now **incorrect** (superseded by section 3 and 4):

- ~~"Firewall evaluates only network origin; identity cannot bypass firewall."~~ — Firewall does read the OAuth token's `xms_az_tm` claim during the bypass evaluation. Identity-based bypass is exactly what's implemented.
- ~~"AKS is not in the Trusted Microsoft Services list nor in resource instance supported types."~~ — AKS was onboarded as a trusted service via `xms_az_tm=azureinfra` trust mode; the `Microsoft.ContainerService` resource type onboarding is a separate (Resource Instance rules) mechanism which remains unsupported, but is not required for this scenario.
- ~~"`useDataPlaneAPI: 'oauth'` only affects SDK calls, not the AzCopy subprocess."~~ — The `oauth` value affects the SDK path directly, and the AzCopy subprocess also runs inside the csi-azurefile-controller pod, so it inherits the same msi-adapter path and gets the same trusted-service claim. The RBAC assignment (Storage File Data Privileged Contributor) is what actually determines whether AzCopy stays on OAuth or falls back to SAS.
- ~~"Only bypass is to run AzCopy inside the customer vnet."~~ — Correct in the pre-fix era, no longer needed.

The **ARM vs data plane distinction (section 2)** is still accurate and still explains why `CreateFileShare` was never affected — that reasoning is unchanged.

---

## 8. Residual limitations

The trusted-service bypass **only helps requests originating from processes inside csi-azurefile-controller pod**. The following paths do **not** benefit:

| Path | Reason |
|---|---|
| `mount.cifs` at node plugin | Uses account key or Kerberos, not OAuth token; no `xms_az_tm` involved. Still needs the traditional network path (PE / vnet rules) into storage. |
| Any customer pod hitting `<acct>.file.core.windows.net` directly | Their own MSI tokens don't go through msi-adapter → no trusted-service claim. |
| SAS-based auth from csi-azurefile-controller | SAS carries no claims. If shared key access is left enabled and RBAC is missing, driver may fall back to SAS and the whole bypass is lost. |
| Non-controller CSI operations that don't touch `<acct>.file.core.windows.net` (e.g. mgmt-plane ARM calls) | Already worked via ARM; unaffected either way. |

Practical implication: **snapshot lifecycle is unblocked, but the eventual `PersistentVolumeClaim` mount from the restored share still requires the node → storage path to be reachable** (PE + private DNS on the node vnet, or account allows the node subnet). This has always been true and is independent of the trusted-service work.

---

## 9. Summary

| Question | Answer |
|---|---|
| Does `useDataPlaneAPI: "oauth"` fix snapshot restore behind firewall? | **Yes**, on AKS releases with the msi-adapter trusted-service audience config (post 2026-06-22). |
| Does the `Storage File Data Privileged Contributor` role matter? | **Yes** — required, otherwise AzCopy falls back to SAS and loses the trusted-service claim. |
| Does the control plane MI's token cross the firewall? | **Yes**, because msi-adapter injects `xms_az_tm=azureinfra` claim → storage recognizes trusted service → bypass=AzureServices allows it. |
| Why does `CreateFileShare` from hcp succeed even without the fixes? | It uses the ARM management plane, not subject to data-plane firewall. |
| Does Private Endpoint on the customer vnet help for controller-side snapshot ops? | Not needed. The customer vnet is not the network origin. |
| Does the traditional "Trusted Microsoft Services" allowlist ever include AKS? | Not directly; AKS integration uses the `xms_az_tm` trust-mode claim, evaluated via the same `AzureServices` bypass. |
| Are Resource Instance rules for `Microsoft.ContainerService` needed? | Not for this scenario. |
| Does the mount on customer nodes benefit from this fix? | No — node-side mount is CIFS, not OAuth; still needs network reachability from node subnet. |

---

*Reference: [`pkg/azurefile/controllerserver.go`](https://github.com/kubernetes-sigs/azurefile-csi-driver/blob/master/pkg/azurefile/controllerserver.go). Trusted-service enablement: internal PRs [16065499](https://msazure.visualstudio.com/CloudNativeCompute/_git/aks-rp/pullrequest/16065499) (audience), [16173168](https://msazure.visualstudio.com/CloudNativeCompute/_git/aks-rp/pullrequest/16173168) (trailing-slash fix). Related feature: [27675525 — onboard xms_az_tm trust mode in AKS managed identity](https://msazure.visualstudio.com/One/_workitems/edit/27675525).*
