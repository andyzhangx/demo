# Design: Mount Azure File with User-Provided OAuth Token

## Summary

Support mounting Azure File shares using a user-provided OAuth token stored in a Kubernetes Secret. This enables cross-tenant scenarios where kubelet identity and workload identity are not applicable.

**GitHub Issue:** https://github.com/kubernetes-sigs/azurefile-csi-driver/issues/3099

## Motivation

First-party users in cross-tenant scenarios cannot use:
- **Kubelet identity** — bound to the node's subscription/tenant
- **Workload identity** — requires SA token exchange within the same tenant trust boundary

These users need to bring their own OAuth token, obtained from a managed identity in a different tenant.

## Design

### New Volume Context Parameter

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mountWithOAuthToken` | `"true"/"false"` | `"false"` | When true, CSI driver reads OAuth token from the referenced secret for OAuth-based SMB mount |

This parameter is **mutually exclusive** with `mountWithManagedIdentity` and `mountWithWorkloadIdentityToken`.

### Secret Format

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: azure-oauth-token-secret
  namespace: default
type: Opaque
data:
  azurestorageauthtoken: <base64-encoded-oauth-token>
```

Create the secret using `kubectl`:

```bash
kubectl create secret generic azure-oauth-token-secret --from-literal=azurestorageauthtoken="<oauth-token>"
```

The user is responsible for keeping `azurestorageauthtoken` up-to-date (e.g., via a sidecar, CronJob, or external controller that refreshes the OAuth token before expiry).

### PV Example

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: azurefile-oauth-token-pv
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
      mountwithoauthtoken: "true"
      secretname: "azure-oauth-token-secret"
      secretnamespace: "default"
```

## Implementation

### Architecture — NodePublishVolume Token Refresh Pattern

Following the same pattern as `mountWithWorkloadIdentityToken`, the OAuth token refresh happens in **NodePublishVolume** rather than a background manager. The key insight: kubelet periodically calls NodePublishVolume for volumes with service account tokens. We reuse this kubelet-driven refresh cycle.

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
│    ├─ if mountWithOAuthToken && SA token present:   │
│    │    ├─ Read OAuth token from Secret (via kubeClient)         │
│    │    ├─ Call setCredentialCache(server, token)              │
│    │    │   (pass token string directly, no temp file)        │
│    │    └─ Call NodeStageVolume (mount if not already mounted) │
│    │                                                          │
│  NodeStageVolume                                              │
│    │                                                          │
│    ├─ if mountWithOAuthToken:                       │
│    │    ├─ Read OAuth token from Secret                          │
│    │    ├─ setCredentialCache(server, token)                   │
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
2. **Token refresh**: kubelet re-invokes NodePublishVolume periodically (when SA token is projected). NodePublishVolume calls NodeStageVolume again → reads **latest** OAuth token from secret → `setCredentialCache` (updates credential cache) → mount already exists, skips re-mount

For `mountWithOAuthToken`, we follow the **exact same flow**, except:
- Instead of using the SA token directly, we read the OAuth token from the referenced Kubernetes Secret
- The user's external controller (CronJob/sidecar) keeps the secret updated with a fresh OAuth token

### Flow

#### NodePublishVolume (called by kubelet, including periodic re-invocations)

```
1. Check volumeContext: mountWithOAuthToken=true && SA token present
2. Read OAuth token from secret (secretName/secretNamespace) via kubeClient
3. Call setCredentialCache(server, token) — pass token string directly
4. Call NodeStageVolume → mount with sec=krb5 (if not already mounted)
```

#### NodeStageVolume (first mount)

```
1. Parse volumeContext: mountWithOAuthToken=true
2. Read OAuth token from secret via kubeClient
3. sensitiveMountOptions = ["sec=krb5,cruid=0,upcall_target=mount"]
4. Call setCredentialCache(server, token) inside execFunc — pass token string directly
5. Mount SMB share
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
| State management | `/var/lib/azurefile-csi/oauth-token-volumes.json` | Stateless — no persist file needed |
| Driver restart | Must restore and re-register volumes | No recovery needed — kubelet re-calls NodePublishVolume |
| Consistency | Separate refresh interval (15m) | Aligned with kubelet's token rotation |
| Code pattern | New pattern | Identical to `mountWithWorkloadIdentityToken` |

### Code Changes

#### 1. New Constants (`pkg/azurefile/azurefile.go`)

```go
mountWithOAuthTokenField = "mountwithoauthtoken"
defaultSecretOAuthToken  = "azurestorageauthtoken"
```

#### 2. Extend `setCredentialCache` (`pkg/azurefile/utils.go`)

Add a new code path for direct token passing (no temp file needed):

```go
func setCredentialCache(server, clientID, tenantID, tokenFile string) ([]byte, error) {
    if server == "" {
        return nil, fmt.Errorf("server must be provided")
    }

    var args []string
    if tokenFile != "" {
        // Existing: workload identity with token file
        if clientID == "" {
            return nil, fmt.Errorf("clientID must be provided")
        }
        if tenantID == "" {
            return nil, fmt.Errorf("tenantID must be provided when tokenFile is provided")
        }
        args = []string{"set", "https://" + server, "--workload-identity",
            "--tenant-id", tenantID, "--client-id", clientID, "--token-file", tokenFile}
    } else if clientID != "" {
        // Existing: managed identity via IMDS
        args = []string{"set", "https://" + server, "--imds-client-id", clientID}
    } else {
        return nil, fmt.Errorf("clientID must be provided")
    }

    cmd := exec.Command("azfilesauthmanager", args...)
    cmd.Env = append(os.Environ(), cmd.Env...)
    klog.V(2).Infof("Executing command: %q", cmd.String())
    return cmd.CombinedOutput()
}

// setCredentialCache sets credential cache by passing OAuth token directly
// Uses: azfilesauthmanager set https://<server> <access_token>
func setCredentialCache(server, token string) ([]byte, error) {
    if server == "" {
        return nil, fmt.Errorf("server must be provided")
    }
    if token == "" {
        return nil, fmt.Errorf("token must be provided")
    }

    args := []string{"set", "https://" + server, token}
    cmd := exec.Command("azfilesauthmanager", args...)
    cmd.Env = append(os.Environ(), cmd.Env...)
    klog.V(2).Infof("Executing command: azfilesauthmanager set https://%s <token-redacted>", server)
    return cmd.CombinedOutput()
}
```

#### 3. NodePublishVolume Changes (`pkg/azurefile/nodeserver.go`)

Add OAuth token refresh in the existing SA token check block (alongside workload identity):

```go
if context != nil {
    if getValueInMap(context, serviceAccountTokenField) != "" && shouldUseServiceAccountToken(context) {
        // Existing: workload identity token refresh via NodeStageVolume
        klog.V(2).Infof("NodePublishVolume: volume(%s) mount on %s with service account token", volumeID, target)

        // New: if mountWithOAuthToken, refresh OAuth token credential cache
        if strings.EqualFold(getValueInMap(context, mountWithOAuthTokenField), trueValue) {
            if err := d.setCredentialCacheWithOAuthToken(ctx, context, volumeID); err != nil {
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

#### 4. New Helper Function

```go
func (d *Driver) setCredentialCacheWithOAuthToken(ctx context.Context, context map[string]string, volumeID string) error {
    secretName := getValueInMap(context, secretNameField)
    secretNamespace := getValueInMap(context, secretNamespaceField)
    server := getValueInMap(context, serverField)

    secret, err := d.kubeClient.CoreV1().Secrets(secretNamespace).Get(ctx, secretName, metav1.GetOptions{})
    if err != nil {
        return status.Errorf(codes.Internal, "failed to get secret %s/%s: %v",
            secretNamespace, secretName, err)
    }

    oauthToken := string(secret.Data[defaultSecretOAuthToken])
    if oauthToken == "" {
        return status.Errorf(codes.InvalidArgument, "%s not found in secret %s/%s",
            defaultSecretOAuthToken, secretNamespace, secretName)
    }

    // Pass token directly to azfilesauthmanager — no temp file needed
    if out, err := setCredentialCache(server, oauthToken); err != nil {
        return status.Errorf(codes.Internal,
            "setCredentialCache failed for volume %s: %v, output: %s", volumeID, err, out)
    }

    klog.V(2).Infof("NodePublishVolume: refreshed OAuth token credential cache for volume %s", volumeID)
    return nil
}
```

#### 5. NodeStageVolume Changes

Add new mount branch after `mountWithWIToken`:

```go
} else if mountWithOAuthToken && runtime.GOOS != "windows" {
    sensitiveMountOptions = []string{"sec=krb5,cruid=0,upcall_target=mount"}
    klog.V(2).Infof("using OAuth token from secret for volume %s", volumeID)
    // setCredentialCache is called inside execFunc (same as mountWithManagedIdentity)
}
```

And in the `execFunc` for mount:

```go
execFunc := func() error {
    if (mountWithManagedIdentity || mountWithOAuthToken) && protocol != nfs && runtime.GOOS != "windows" {
        if mountWithOAuthToken {
            // Pass token directly — no temp file
            if err := d.setCredentialCacheWithOAuthToken(ctx, context, volumeID); err != nil {
                return fmt.Errorf("setCredentialCacheWithOAuthToken: %v", err)
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

#### 6. Mutual Exclusion Check

```go
if (mountWithManagedIdentity && mountWithWIToken) ||
    (mountWithManagedIdentity && mountWithOAuthToken) ||
    (mountWithWIToken && mountWithOAuthToken) {
    return nil, status.Error(codes.InvalidArgument,
        "only one of mountWithManagedIdentity, mountWithWorkloadIdentityToken, "+
            "and mountWithOAuthToken can be true")
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
2. **No temp file** — Token passed directly to `azfilesauthmanager` as CLI argument; no file written to disk
3. **No persist file** — No state file on disk (unlike background manager approach)
4. **Token in process args** — Token briefly visible in `/proc/<pid>/cmdline`; same exposure as existing `--imds-client-id` flow. For hardened environments, consider piping via stdin in a future enhancement.
5. **RBAC** — CSI node plugin needs `get` permission on secrets in relevant namespaces (already required for existing secret-based flows)

## Limitations

- **Static provisioning only** — Dynamic provisioning does not support this flow
- **Linux only** — `setCredentialCache` and `sec=krb5` are Linux-specific
- **SMB protocol only** — NFS does not use credential cache
- **User responsibility** — User must ensure the secret token is refreshed before expiry via external controller

## Estimated Change Size

| File | Lines |
|------|-------|
| `pkg/azurefile/azurefile.go` (constants) | ~5 |
| `pkg/azurefile/utils.go` (`setCredentialCache`) | ~15 |
| `pkg/azurefile/nodeserver.go` (NodePublishVolume + NodeStageVolume + helper) | ~50 |
| `pkg/azurefile/nodeserver_test.go` (additions) | ~80 |
| **Total** | **~150 lines** |
