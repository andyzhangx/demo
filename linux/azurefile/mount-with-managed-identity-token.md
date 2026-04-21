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

The user is responsible for keeping `azurestoragemanagedidentitytoken` up-to-date (e.g., via a sidecar, CronJob, or external controller that refreshes the MI token every 30 minutes).

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

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CSI Driver (Node Plugin)                     │
│                                                                       │
│  ┌──────────────┐     ┌─────────────────────┐     ┌──────────────┐ │
│  │NodeStageVolume│────▶│ TokenRefreshManager │◀────│NodeUnstageVol│ │
│  │(first mount)  │     │  (background loop)   │     │  (unmount)   │ │
│  └──────┬───────┘     └──────────┬──────────┘     └──────────────┘ │
│         │                        │                                    │
│         ▼                        ▼                                    │
│  ┌─────────────────────────────────────────┐                         │
│  │         setCredentialCache()             │                         │
│  │  (updates Linux CIFS credential cache)  │                         │
│  └─────────────────────────────────────────┘                         │
│         │                        │                                    │
└─────────┼────────────────────────┼────────────────────────────────────┘
          │                        │
          ▼                        ▼
┌──────────────────┐     ┌──────────────────────┐
│  SMB/CIFS Mount  │     │  Kubernetes Secret    │
│  (sec=krb5)      │     │  (MI token refreshed  │
│                  │     │   by user controller) │
└──────────────────┘     └──────────────────────┘
```

### Flow

#### First Mount (NodeStageVolume)

```
1. Parse volumeContext: mountWithManagedIdentityToken=true
2. Read secret (secretName/secretNamespace) via kubeClient
3. Extract azurestoragemanagedidentitytoken from secret
4. Write token to temp file
5. Call setCredentialCache(server, clientID, tenantID, tokenFile)
6. Mount with sensitiveMountOptions: ["sec=krb5,cruid=0,upcall_target=mount"]
7. Register volume in TokenRefreshManager
8. Persist registration to /var/lib/azurefile-csi/mi-token-volumes.json
```

#### Token Refresh (TokenRefreshManager - every 15 minutes)

```
1. Iterate registered volumes
2. For each volume:
   a. Get secret via kubeClient
   b. Extract latest azurestoragemanagedidentitytoken
   c. Write to temp file
   d. Call setCredentialCache(server, clientID, tenantID, tokenFile)
   e. Delete temp file
3. Log warnings for failures (don't crash)
```

#### Unmount (NodeUnstageVolume)

```
1. Perform normal unmount
2. Unregister volume from TokenRefreshManager
3. Persist updated registration to disk
```

#### Driver Restart Recovery

```
1. On startup: read /var/lib/azurefile-csi/mi-token-volumes.json
2. Restore all volume registrations to TokenRefreshManager
3. Immediately run one refreshAll() cycle
4. Resume periodic refresh
```

### Code Changes

#### 1. New Constants (`pkg/azurefile/azurefile.go`)

```go
mountWithManagedIdentityTokenField = "mountwithmanagedidentitytoken"
defaultSecretManagedIdentityToken  = "azurestoragemanagedidentitytoken"
```

#### 2. New File: `pkg/azurefile/token_refresh_manager.go`

```go
package azurefile

import (
    "context"
    "encoding/json"
    "fmt"
    "os"
    "sync"
    "time"

    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    clientset "k8s.io/client-go/kubernetes"
    "k8s.io/klog/v2"
)

const (
    defaultTokenRefreshInterval = 15 * time.Minute
    miTokenVolumesFile          = "/var/lib/azurefile-csi/mi-token-volumes.json"
)

// MITokenVolumeInfo holds metadata needed to refresh a volume's credential cache
type MITokenVolumeInfo struct {
    VolumeID        string `json:"volumeID"`
    Server          string `json:"server"`
    ClientID        string `json:"clientID"`
    TenantID        string `json:"tenantID"`
    SecretName      string `json:"secretName"`
    SecretNamespace string `json:"secretNamespace"`
}

// TokenRefreshManager periodically refreshes MI token credential cache
type TokenRefreshManager struct {
    mu              sync.RWMutex
    volumes         map[string]*MITokenVolumeInfo
    kubeClient      clientset.Interface
    refreshInterval time.Duration
    stopCh          chan struct{}
}

func NewTokenRefreshManager(kubeClient clientset.Interface, refreshInterval time.Duration) *TokenRefreshManager {
    if refreshInterval == 0 {
        refreshInterval = defaultTokenRefreshInterval
    }
    return &TokenRefreshManager{
        volumes:         make(map[string]*MITokenVolumeInfo),
        kubeClient:      kubeClient,
        refreshInterval: refreshInterval,
        stopCh:          make(chan struct{}),
    }
}

func (m *TokenRefreshManager) Start() {
    go m.refreshLoop()
    klog.V(2).Infof("TokenRefreshManager started with interval %v", m.refreshInterval)
}

func (m *TokenRefreshManager) Stop() {
    close(m.stopCh)
}

func (m *TokenRefreshManager) Register(info *MITokenVolumeInfo) {
    m.mu.Lock()
    m.volumes[info.VolumeID] = info
    m.mu.Unlock()
    m.persist()
    klog.V(2).Infof("TokenRefreshManager: registered volume %s (server=%s, secret=%s/%s)",
        info.VolumeID, info.Server, info.SecretNamespace, info.SecretName)
}

func (m *TokenRefreshManager) Unregister(volumeID string) {
    m.mu.Lock()
    delete(m.volumes, volumeID)
    m.mu.Unlock()
    m.persist()
    klog.V(2).Infof("TokenRefreshManager: unregistered volume %s", volumeID)
}

// Restore recovers volume registrations from disk after driver restart
func (m *TokenRefreshManager) Restore() error {
    data, err := os.ReadFile(miTokenVolumesFile)
    if os.IsNotExist(err) {
        return nil
    }
    if err != nil {
        return fmt.Errorf("read %s: %v", miTokenVolumesFile, err)
    }

    var volumes map[string]*MITokenVolumeInfo
    if err := json.Unmarshal(data, &volumes); err != nil {
        return fmt.Errorf("unmarshal %s: %v", miTokenVolumesFile, err)
    }

    m.mu.Lock()
    m.volumes = volumes
    m.mu.Unlock()

    klog.V(2).Infof("TokenRefreshManager: restored %d volumes from disk", len(volumes))
    return nil
}

func (m *TokenRefreshManager) refreshLoop() {
    // Immediate refresh on start
    m.refreshAll()

    ticker := time.NewTicker(m.refreshInterval)
    defer ticker.Stop()

    for {
        select {
        case <-ticker.C:
            m.refreshAll()
        case <-m.stopCh:
            klog.V(2).Info("TokenRefreshManager: stopped")
            return
        }
    }
}

func (m *TokenRefreshManager) refreshAll() {
    m.mu.RLock()
    volumes := make([]*MITokenVolumeInfo, 0, len(m.volumes))
    for _, v := range m.volumes {
        volumes = append(volumes, v)
    }
    m.mu.RUnlock()

    if len(volumes) == 0 {
        return
    }

    klog.V(4).Infof("TokenRefreshManager: refreshing %d volumes", len(volumes))

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    for _, vol := range volumes {
        if err := m.refreshOne(ctx, vol); err != nil {
            klog.Warningf("TokenRefreshManager: failed to refresh volume %s: %v", vol.VolumeID, err)
        }
    }
}

func (m *TokenRefreshManager) refreshOne(ctx context.Context, vol *MITokenVolumeInfo) error {
    secret, err := m.kubeClient.CoreV1().Secrets(vol.SecretNamespace).Get(ctx, vol.SecretName, metav1.GetOptions{})
    if err != nil {
        return fmt.Errorf("get secret %s/%s: %v", vol.SecretNamespace, vol.SecretName, err)
    }

    miToken := string(secret.Data[defaultSecretManagedIdentityToken])
    if miToken == "" {
        return fmt.Errorf("%s not found in secret %s/%s",
            defaultSecretManagedIdentityToken, vol.SecretNamespace, vol.SecretName)
    }

    tokenFile, err := writeMITokenToTempFile(miToken)
    if err != nil {
        return fmt.Errorf("write temp file: %v", err)
    }
    defer os.Remove(tokenFile)

    if out, err := setCredentialCache(vol.Server, vol.ClientID, vol.TenantID, tokenFile); err != nil {
        return fmt.Errorf("setCredentialCache for %s: %v, output: %s", vol.Server, err, out)
    }

    klog.V(4).Infof("TokenRefreshManager: refreshed credential cache for volume %s", vol.VolumeID)
    return nil
}

func (m *TokenRefreshManager) persist() {
    m.mu.RLock()
    data, err := json.MarshalIndent(m.volumes, "", "  ")
    m.mu.RUnlock()
    if err != nil {
        klog.Warningf("TokenRefreshManager: failed to marshal volumes: %v", err)
        return
    }

    dir := filepath.Dir(miTokenVolumesFile)
    if err := os.MkdirAll(dir, 0750); err != nil {
        klog.Warningf("TokenRefreshManager: failed to create dir %s: %v", dir, err)
        return
    }
    if err := os.WriteFile(miTokenVolumesFile, data, 0600); err != nil {
        klog.Warningf("TokenRefreshManager: failed to persist volumes: %v", err)
    }
}

// writeMITokenToTempFile writes the MI token to a temporary file
func writeMITokenToTempFile(token string) (string, error) {
    tmpFile, err := os.CreateTemp("", "mi-token-*")
    if err != nil {
        return "", fmt.Errorf("create temp file: %v", err)
    }
    if _, err := tmpFile.WriteString(token); err != nil {
        tmpFile.Close()
        os.Remove(tmpFile.Name())
        return "", fmt.Errorf("write token: %v", err)
    }
    tmpFile.Close()
    return tmpFile.Name(), nil
}
```

#### 3. NodeStageVolume Changes (`pkg/azurefile/nodeserver.go`)

Add to variable declarations in `NodeStageVolume`:

```go
var mountWithManagedIdentityToken bool
```

Add to the `for k, v := range context` switch:

```go
case mountWithManagedIdentityTokenField:
    mountWithManagedIdentityToken, err = strconv.ParseBool(v)
    if err != nil {
        return nil, status.Error(codes.InvalidArgument,
            fmt.Sprintf("Volume context property %q must be a boolean value: %v", k, err))
    }
```

Update mutual exclusion check:

```go
if (mountWithManagedIdentity && mountWithWIToken) ||
    (mountWithManagedIdentity && mountWithManagedIdentityToken) ||
    (mountWithWIToken && mountWithManagedIdentityToken) {
    return nil, status.Error(codes.InvalidArgument,
        "only one of mountWithManagedIdentity, mountWithWorkloadIdentityToken, and mountWithManagedIdentityToken can be true")
}
```

Add new mount branch (after the `mountWithWIToken` branch):

```go
} else if mountWithManagedIdentityToken && runtime.GOOS != "windows" {
    secretName := getValueInMap(context, secretNameField)
    secretNamespace := getValueInMap(context, secretNamespaceField)
    if secretName == "" || secretNamespace == "" {
        return nil, status.Error(codes.InvalidArgument,
            "secretName and secretNamespace are required when mountWithManagedIdentityToken is true")
    }

    secret, err := d.kubeClient.CoreV1().Secrets(secretNamespace).Get(ctx, secretName, metav1.GetOptions{})
    if err != nil {
        return nil, status.Errorf(codes.Internal, "failed to get secret %s/%s: %v",
            secretNamespace, secretName, err)
    }

    miToken := string(secret.Data[defaultSecretManagedIdentityToken])
    if miToken == "" {
        return nil, status.Error(codes.InvalidArgument,
            fmt.Sprintf("%s not found in secret %s/%s",
                defaultSecretManagedIdentityToken, secretNamespace, secretName))
    }

    sensitiveMountOptions = []string{"sec=krb5,cruid=0,upcall_target=mount"}
    klog.V(2).Infof("using managed identity token from secret for volume %s", volumeID)

    tokenFile, err := writeMITokenToTempFile(miToken)
    if err != nil {
        return nil, status.Errorf(codes.Internal, "failed to write MI token: %v", err)
    }
    defer os.Remove(tokenFile)

    if out, err := setCredentialCache(server, clientID, tenantID, tokenFile); err != nil {
        return nil, status.Errorf(codes.Internal,
            "setCredentialCache failed for %s: %v, output: %s", server, err, out)
    }

    // Register for periodic token refresh
    if d.tokenRefreshManager != nil {
        d.tokenRefreshManager.Register(&MITokenVolumeInfo{
            VolumeID:        volumeID,
            Server:          server,
            ClientID:        clientID,
            TenantID:        tenantID,
            SecretName:      secretName,
            SecretNamespace: secretNamespace,
        })
    }
}
```

#### 4. NodeUnstageVolume Changes

```go
func (d *Driver) NodeUnstageVolume(_ context.Context, req *csi.NodeUnstageVolumeRequest) (*csi.NodeUnstageVolumeResponse, error) {
    volumeID := req.GetVolumeId()
    // ... existing code ...

    // Unregister from token refresh manager
    if d.tokenRefreshManager != nil {
        d.tokenRefreshManager.Unregister(volumeID)
    }

    // ... rest of existing code ...
}
```

#### 5. Driver Initialization

```go
// In NewDriver() or Run():
d.tokenRefreshManager = NewTokenRefreshManager(d.kubeClient, d.miTokenRefreshInterval)
if err := d.tokenRefreshManager.Restore(); err != nil {
    klog.Warningf("Failed to restore token refresh state: %v", err)
}
d.tokenRefreshManager.Start()
```

#### 6. Driver Flag

```go
flag.DurationVar(&d.miTokenRefreshInterval, "mi-token-refresh-interval",
    15*time.Minute, "Interval for refreshing managed identity token credential cache")
```

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Secret deleted | `refreshOne` logs warning, retries next tick |
| Token invalid/expired | `setCredentialCache` fails, logs warning, existing SMB session may still work |
| Driver pod restart | Restores from `/var/lib/azurefile-csi/mi-token-volumes.json`, resumes refresh |
| Node reboot | kubelet re-triggers NodeStageVolume → fresh mount + re-register |
| Multiple volumes share same secret | Each independently registered, works correctly |
| Secret not yet updated by user | Uses stale token, `setCredentialCache` may fail but existing session continues |
| Concurrent mount/unmount | `sync.RWMutex` protects the map |

## Security Considerations

1. **Token in secret** — Standard Kubernetes RBAC controls access; no broader than existing `nodeStageSecretRef` pattern
2. **Temp file** — Token written to temp file, immediately deleted after `setCredentialCache`; file permission 0600
3. **Persist file** — `/var/lib/azurefile-csi/mi-token-volumes.json` stores volume metadata only (no tokens); permission 0600
4. **RBAC** — CSI node plugin needs `get` permission on secrets in relevant namespaces (already required for existing secret-based flows)

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--mi-token-refresh-interval` | `15m` | How often to refresh the credential cache from the secret |

## Limitations

- **Static provisioning only** — Dynamic provisioning does not support this flow
- **Linux only** — `setCredentialCache` and `sec=krb5` are Linux-specific
- **SMB protocol only** — NFS does not use credential cache
- **User responsibility** — User must ensure the secret token is refreshed before expiry

## Timeline

```
t=0      User deploys token refresher (CronJob/controller) + PV + PVC + Pod
t=0      NodeStageVolume → read secret → setCredentialCache → SMB mount → register
t=15m    TokenRefreshManager → read secret → setCredentialCache (refresh)
t=30m    TokenRefreshManager → read secret → setCredentialCache (refresh)
t=50m    User's CronJob updates secret with new token
t=60m    TokenRefreshManager → read secret (new token) → setCredentialCache ✓
...
t=???    Pod deleted → NodeUnstageVolume → unregister
```

## Estimated Change Size

| File | Lines |
|------|-------|
| `pkg/azurefile/azurefile.go` (constants + struct) | ~5 |
| `pkg/azurefile/token_refresh_manager.go` (new) | ~160 |
| `pkg/azurefile/nodeserver.go` (mount logic) | ~40 |
| `pkg/azurefile/token_refresh_manager_test.go` (new) | ~120 |
| `pkg/azurefile/nodeserver_test.go` (additions) | ~50 |
| **Total** | **~375 lines** |
