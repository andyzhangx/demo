# Design: Mount Azure File with User-Provided Managed Identity Token

## Summary

Support mounting Azure File shares using a user-provided managed identity (MI) token stored in a Kubernetes Secret. This enables cross-tenant scenarios where kubelet identity and workload identity are not applicable.

**GitHub Issue:** https://github.com/kubernetes-sigs/azurefile-csi-driver/issues/3099

## Motivation

First-party users in cross-tenant scenarios cannot use:
- **Kubelet identity** — bound to the node's subscription/tenant
- **Workload identity** — requires SA token exchange within the same tenant trust boundary

These users need to bring their own MI token, obtained from a managed identity in a different tenant.

## Design

### New Volume Context Parameter

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mountWithManagedIdentityToken` | `"true"/"false"` | `"false"` | When true, CSI driver reads MI token from the referenced secret for OAuth-based SMB mount |

This parameter is **mutually exclusive** with `mountWithManagedIdentity` and `mountWithWorkloadIdentityToken`.

### Secret Format

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: azure-mi-token-secret
  namespace: default
type: Opaque
data:
  azurestorageaccountname: <base64-encoded-account-name>
  azurestoragemanagedidentitytoken: <base64-encoded-oauth-token>
```

The user is responsible for keeping `azurestoragemanagedidentitytoken` up-to-date (e.g., via a sidecar, CronJob, or external controller that refreshes the MI token before expiry).

### PV Example

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: azurefile-mi-token-pv
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  csi:
    driver: file.csi.azure.com
    volumeHandle: "unique-volume-id"
    volumeAttributes:
      storageaccount: "mystorageaccount"
      sharename: "myshare"
      mountwithmanagedidentitytoken: "true"
      clientid: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
      tenantid: "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
      secretname: "azure-mi-token-secret"
      secretnamespace: "default"
    nodeStageSecretRef:
      name: azure-mi-token-secret
      namespace: default
```

## Implementation

### Architecture — NodePublishVolume Token Refresh Pattern

Following the same pattern as `mountWithWorkloadIdentityToken`, the MI token refresh happens in **NodePublishVolume** rather than a background manager. The key insight: kubelet periodically calls NodePublishVolume for volumes with service account tokens. We reuse this kubelet-driven refresh cycle.

```
┌──────────────────────────────────────────────────────────────┐
│                       kubelet                                 │
│  (periodically re-invokes NodePublishVolume for token refresh)│
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│               CSI Driver (Node Plugin)                        │
│                                                               │
│  NodePublishVolume                                            │
│    │                                                          │
│    ├─ if mountWithManagedIdentityToken && SA token present:   │
│    │    ├─ Read MI token from Secret (via kubeClient)         │
│    │    ├─ Write token to temp file                           │
│    │    ├─ Call setCredentialCache(server, clientID,           │
│    │    │                          tenantID, tokenFile)       │
│    │    ├─ Delete temp file                                   │
│    │    └─ Call NodeStageVolume (mount if not already mounted) │
│    │                                                          │
│  NodeStageVolume                                              │
│    │                                                          │
│    ├─ if mountWithManagedIdentityToken:                       │
│    │    ├─ Read MI token from Secret                          │
│    │    ├─ setCredentialCache()                               │
│    │    ├─ Mount with sec=krb5,cruid=0,upcall_target=mount   │
│    │    └─ (skip if already mounted)                          │
│    │                                                          │
│  NodeUnstageVolume                                            │
│    └─ Normal unmount, no extra cleanup needed                 │
└──────────────────────────────────────────────────────────────┘
```

### How Token Refresh Works (Same as Workload Identity)

The `mountWithWorkloadIdentityToken` pattern works as follows:

1. **First mount**: NodePublishVolume detects `serviceAccountToken` in volume context → calls NodeStageVolume → reads token → `setCredentialCache` → SMB mount with `sec=krb5`
2. **Token refresh**: kubelet re-invokes NodePublishVolume periodically (when SA token is projected). NodePublishVolume calls NodeStageVolume again → reads **latest** MI token from secret → `setCredentialCache` (updates credential cache) → mount already exists, skips re-mount

For `mountWithManagedIdentityToken`, we follow the **exact same flow**, except:
- Instead of using the SA token directly, we read the MI token from the referenced Kubernetes Secret
- The user's external controller (CronJob/sidecar) keeps the secret updated with a fresh MI token

### Flow

#### NodePublishVolume (called by kubelet, including periodic re-invocations)

```
1. Check volumeContext: mountWithManagedIdentityToken=true && SA token present
2. Read MI token from secret (secretName/secretNamespace) via kubeClient
3. Write token to temp file
4. Call setCredentialCache(server, clientID, tenantID, tokenFile)
5. Delete temp file
6. Call NodeStageVolume → mount with sec=krb5 (if not already mounted)
```

#### NodeStageVolume (first mount)

```
1. Parse volumeContext: mountWithManagedIdentityToken=true
2. Read MI token from secret via kubeClient
3. Write token to temp file
4. sensitiveMountOptions = ["sec=krb5,cruid=0,upcall_target=mount"]
5. Call setCredentialCache(server, clientID, tenantID, tokenFile) inside execFunc
6. Mount SMB share
7. Delete temp file
```

#### NodeUnstageVolume (unmount)

```
1. Normal unmount — no extra cleanup needed
   (no background goroutines, no persist files to clean up)
```

### Advantages Over Background TokenRefreshManager

| Aspect | Background Manager | NodePublishVolume Pattern (chosen) |
|--------|-------------------|-----------------------------------|
| Complexity | New goroutine, persist file, restart recovery | Reuse existing kubelet-driven refresh cycle |
| Failure handling | Silent background failures | Errors surface to kubelet |
| State management | `/var/lib/azurefile-csi/mi-token-volumes.json` | Stateless — no persist file needed |
| Driver restart | Must restore and re-register volumes | No recovery needed — kubelet re-calls NodePublishVolume |
| Consistency | Separate refresh interval (15m) | Aligned with kubelet's token rotation |
| Code pattern | New pattern | Identical to `mountWithWorkloadIdentityToken` |

### Code Changes

#### 1. New Constants (`pkg/azurefile/azurefile.go`)

```go
mountWithManagedIdentityTokenField = "mountwithmanagedidentitytoken"
defaultSecretManagedIdentityToken  = "azurestoragemanagedidentitytoken"
```

#### 2. NodePublishVolume Changes (`pkg/azurefile/nodeserver.go`)

Add MI token refresh in the existing SA token check block (alongside workload identity):

```go
if context != nil {
    if getValueInMap(context, serviceAccountTokenField) != "" && shouldUseServiceAccountToken(context) {
        // Existing: workload identity token refresh via NodeStageVolume
        klog.V(2).Infof("NodePublishVolume: volume(%s) mount on %s with service account token", volumeID, target)

        // New: if mountWithManagedIdentityToken, refresh MI token credential cache
        if strings.EqualFold(getValueInMap(context, mountWithManagedIdentityTokenField), trueValue) {
            if err := d.refreshMITokenCredentialCache(ctx, context, volumeID); err != nil {
                return nil, err
            }
        }

        _, err := d.NodeStageVolume(ctx, &csi.NodeStageVolumeRequest{
            StagingTargetPath: target,
            VolumeContext:     context,
            VolumeCapability:  volCap,
            VolumeId:          volumeID,
        })
        return &csi.NodePublishVolumeResponse{}, err
    }
}
```

#### 3. New Helper Function

```go
func (d *Driver) refreshMITokenCredentialCache(ctx context.Context, context map[string]string, volumeID string) error {
    secretName := getValueInMap(context, secretNameField)
    secretNamespace := getValueInMap(context, secretNamespaceField)
    clientID := getValueInMap(context, clientIDField)
    tenantID := getValueInMap(context, tenantIDField)
    server := getValueInMap(context, serverField)

    secret, err := d.kubeClient.CoreV1().Secrets(secretNamespace).Get(ctx, secretName, metav1.GetOptions{})
    if err != nil {
        return status.Errorf(codes.Internal, "failed to get secret %s/%s: %v",
            secretNamespace, secretName, err)
    }

    miToken := string(secret.Data[defaultSecretManagedIdentityToken])
    if miToken == "" {
        return status.Errorf(codes.InvalidArgument, "%s not found in secret %s/%s",
            defaultSecretManagedIdentityToken, secretNamespace, secretName)
    }

    tokenFile, err := writeMITokenToTempFile(miToken)
    if err != nil {
        return status.Errorf(codes.Internal, "failed to write MI token: %v", err)
    }
    defer os.Remove(tokenFile)

    if out, err := setCredentialCache(server, clientID, tenantID, tokenFile); err != nil {
        return status.Errorf(codes.Internal,
            "setCredentialCache failed for volume %s: %v, output: %s", volumeID, err, out)
    }

    klog.V(2).Infof("NodePublishVolume: refreshed MI token credential cache for volume %s", volumeID)
    return nil
}
```

#### 4. NodeStageVolume Changes

Add new mount branch after `mountWithWIToken`:

```go
} else if mountWithManagedIdentityToken && runtime.GOOS != "windows" {
    sensitiveMountOptions = []string{"sec=krb5,cruid=0,upcall_target=mount"}
    klog.V(2).Infof("using managed identity token from secret for volume %s", volumeID)
    // setCredentialCache is called inside execFunc (same as mountWithManagedIdentity)
}
```

And in the `execFunc` for mount:

```go
execFunc := func() error {
    if (mountWithManagedIdentity || mountWithManagedIdentityToken) && protocol != nfs && runtime.GOOS != "windows" {
        // Read MI token from secret and refresh credential cache
        if mountWithManagedIdentityToken {
            if err := d.refreshMITokenCredentialCache(ctx, context, volumeID); err != nil {
                return fmt.Errorf("refreshMITokenCredentialCache: %v", err)
            }
        } else {
            if out, err := setCredentialCache(server, clientID, tenantID, tokenFilePath); err != nil {
                return fmt.Errorf("setCredentialCache failed for %s: %v, output: %s", server, err, out)
            }
        }
    }
    return SMBMount(d.mounter, source, cifsMountPath, mountFsType, mountOptions, sensitiveMountOptions)
}
```

#### 5. Mutual Exclusion Check

```go
if (mountWithManagedIdentity && mountWithWIToken) ||
    (mountWithManagedIdentity && mountWithManagedIdentityToken) ||
    (mountWithWIToken && mountWithManagedIdentityToken) {
    return nil, status.Error(codes.InvalidArgument,
        "only one of mountWithManagedIdentity, mountWithWorkloadIdentityToken, "+
            "and mountWithManagedIdentityToken can be true")
}
```

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Secret deleted | NodePublishVolume returns error, kubelet retries |
| Token invalid/expired | `setCredentialCache` fails, error surfaces to kubelet |
| Driver pod restart | No recovery needed — kubelet re-calls NodePublishVolume |
| Node reboot | kubelet re-triggers full NodePublishVolume → NodeStageVolume flow |
| Multiple volumes same secret | Each NodePublishVolume call reads secret independently |
| Secret not yet updated | Uses current (possibly stale) token, `setCredentialCache` may fail |

## Security Considerations

1. **Token in secret** — Standard Kubernetes RBAC controls access; no broader than existing `nodeStageSecretRef` pattern
2. **Temp file** — Token written to temp file, immediately deleted after `setCredentialCache`; file permission 0600
3. **No persist file** — Unlike the background manager approach, no state file on disk
4. **RBAC** — CSI node plugin needs `get` permission on secrets in relevant namespaces (already required for existing secret-based flows)

## Limitations

- **Static provisioning only** — Dynamic provisioning does not support this flow
- **Linux only** — `setCredentialCache` and `sec=krb5` are Linux-specific
- **SMB protocol only** — NFS does not use credential cache
- **User responsibility** — User must ensure the secret token is refreshed before expiry via external controller

## Estimated Change Size

| File | Lines |
|------|-------|
| `pkg/azurefile/azurefile.go` (constants) | ~5 |
| `pkg/azurefile/nodeserver.go` (NodePublishVolume + NodeStageVolume + helper) | ~60 |
| `pkg/azurefile/nodeserver_test.go` (additions) | ~80 |
| **Total** | **~145 lines** |
