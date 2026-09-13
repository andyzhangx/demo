# AKS identity bindings vs Azure File CSI workload identity

## Summary

This note answers one specific question:

> Can the new AKS **identity binding** feature described in
> <https://learn.microsoft.com/en-us/azure/aks/identity-bindings-concepts>
> directly work with Azure File CSI driver's documented **workload identity** flow in
> <https://github.com/kubernetes-sigs/azurefile-csi-driver/blob/master/docs/workload-identity-static-pv-mount.md>?

### Short answer

**Not directly today.**

Azure File CSI driver's current workload identity path is built around the
existing federated token / workload identity flow. AKS identity bindings require
an **Azure Proxy-aware** `WorkloadIdentityCredential` flow, and the current Azure
File CSI driver path does not appear to enable that mode.

Also, there are actually **two different auth paths** involved, and they need
**different fixes**:

1. **ARM / account-key retrieval path**
   - Azure File CSI driver -> `cloud-provider-azure` -> Azure Identity SDK
2. **`mountWithWorkloadIdentityToken: "true"` token-only mount path**
   - Azure File CSI driver -> `azfilesauthmanager` / AzFilesAuthenticator

These two paths must be analyzed separately.

---

## What AKS identity bindings require

The AKS identity bindings concept doc says identity bindings extend workload
identity, but clients must:

- use **`WorkloadIdentityCredential`**
- explicitly enable **Azure Proxy** / identity binding mode
- not rely on `ManagedIdentityCredential` or `DefaultAzureCredential`

That means a component is not identity-binding-ready just because it already
uses workload identity in the traditional federated identity credential (FIC)
model.

---

## Path 1: Azure File CSI driver workload identity for ARM / account-key retrieval

### Current Azure File CSI driver behavior

In `pkg/azurefile/azure.go`, the driver reads the environment variables injected
by workload identity webhook and copies them into cloud config:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_FEDERATED_TOKEN_FILE`

When `AZURE_FEDERATED_TOKEN_FILE` is present, it sets:

- `config.AADFederatedTokenFile = federatedTokenFile`
- `config.UseFederatedWorkloadIdentityExtension = true`

Relevant code:

- `azurefile-csi-driver/pkg/azurefile/azure.go`

```go
if tenantID := os.Getenv("AZURE_TENANT_ID"); tenantID != "" {
    config.TenantID = tenantID
}
if clientID := os.Getenv("AZURE_CLIENT_ID"); clientID != "" {
    config.AADClientID = clientID
}
if federatedTokenFile := os.Getenv("AZURE_FEDERATED_TOKEN_FILE"); federatedTokenFile != "" {
    config.AADFederatedTokenFile = federatedTokenFile
    config.UseFederatedWorkloadIdentityExtension = true
}
```

### Current `cloud-provider-azure` behavior

`cloud-provider-azure` eventually constructs the workload identity credential in:

- `pkg/azclient/auth.go`
- `pkg/azclient/auth_func.go`

The relevant function is:

- `newAuthProviderWithWorkloadIdentity(...)`

It calls:

```go
azidentity.NewWorkloadIdentityCredential(&azidentity.WorkloadIdentityCredentialOptions{
    ClientOptions: *clientOptions,
    ClientID:      config.GetAADClientID(),
    TenantID:      armConfig.GetTenantID(),
    TokenFilePath: aadFederatedTokenFile,
})
```

So today it passes:

- `ClientID`
- `TenantID`
- `TokenFilePath`

But it does **not** enable Azure Proxy / identity binding mode.

### Smallest change point for this path

If the goal is to support AKS identity bindings for the **ARM/account-key** path,
the smallest code change in the repo stack is:

#### In `cloud-provider-azure`

1. Add a config knob in:
   - `pkg/azclient/auth_conf.go`

   Example shape:

```go
EnableAzureProxy bool `json:"enableAzureProxy,omitempty" yaml:"enableAzureProxy,omitempty"`
```

2. Plumb that knob into:
   - `pkg/azclient/auth_func.go`

Conceptually:

```go
azidentity.NewWorkloadIdentityCredential(&azidentity.WorkloadIdentityCredentialOptions{
    ClientOptions:    *clientOptions,
    ClientID:         config.GetAADClientID(),
    TenantID:         armConfig.GetTenantID(),
    TokenFilePath:    aadFederatedTokenFile,
    EnableAzureProxy: config.EnableAzureProxy,
})
```

#### In `azurefile-csi-driver`

3. Add a small config/env plumbing point in:
   - `pkg/azurefile/azure.go`

For example, allow the driver to read something like:

- `AZURE_ENABLE_AZURE_PROXY=true`

and map that into the cloud config passed to `cloud-provider-azure`.

### Important blocker

There is an SDK-level catch.

In the current Azure SDK for Go `azidentity` source, the workload identity
credential has an `enableAzureProxy` field in `WorkloadIdentityCredentialOptions`,
but the field appears **unexported** in the current source snapshot that was
checked.

That means even though `cloud-provider-azure` is the right integration point,
**it may not yet be able to set the option from outside the SDK**.

So the real dependency chain for this path is:

1. **Azure SDK for Go** exposes a public Azure Proxy / identity binding option
2. `cloud-provider-azure` plumbs it into `NewWorkloadIdentityCredential(...)`
3. `azurefile-csi-driver` sets the config/env that turns it on

### Bottom line for path 1

For the **traditional workload identity path used to get ARM/storage tokens or
account keys**, the smallest repo-local change point is:

- **primary change:** `cloud-provider-azure/pkg/azclient/auth_func.go`
- **config plumbing:** `cloud-provider-azure/pkg/azclient/auth_conf.go`
- **driver wiring:** `azurefile-csi-driver/pkg/azurefile/azure.go`

But successful end-to-end support likely also depends on a small Azure SDK for Go
change first.

---

## Path 2: `mountWithWorkloadIdentityToken: "true"` token-only mount path

This path is different.

Here the node plugin does not depend on `cloud-provider-azure` for token exchange.
Instead, it writes the projected service account token to a local file and then
invokes `azfilesauthmanager`.

### Current Azure File CSI driver behavior

In `pkg/azurefile/azurefile.go`, when `mountWithWorkloadIdentityToken` is used,
the driver:

1. parses `csi.storage.k8s.io/serviceAccount.tokens`
2. writes the token to a file under the Azure OAuth token directory
3. returns `tokenFilePath`

Relevant code:

- `azurefile-csi-driver/pkg/azurefile/azurefile.go`

```go
if mountWithWIToken {
    ...
    token, err := parseServiceAccountToken(serviceAccountToken)
    ...
    tokenFilePath = filepath.Join(defaultAzureOAuthTokenDir, tokenFileName)
    if err := os.WriteFile(tokenFilePath, []byte(token), 0600); err != nil {
        ...
    }
    return ..., tokenFilePath, err
}
```

Then in `pkg/azurefile/nodeserver.go`, the node plugin refreshes credential cache
by calling `setCredentialCache(...)`.

That helper is implemented in:

- `azurefile-csi-driver/pkg/azurefile/utils.go`

```go
args = []string{"set", serverURL, "--workload-identity", "--tenant-id", tenantID, "--client-id", clientID, "--token-file", tokenFile}
```

So the driver is not exchanging the token itself. It is delegating that job to
`azfilesauthmanager`.

### Current AzFilesAuthenticator behavior

`azfilesauthmanager` is implemented in the AzFilesAuthenticator repo.
The relevant function is:

- `Azure/AzFilesAuthenticator/src/azfilesauthmanager.py`
- `get_workload_identity_token(...)`

That code currently reads the federated token file and then creates a
`ClientAssertionCredential`, not a `WorkloadIdentityCredential` in identity-binding
mode.

Conceptually it does this:

```python
credential = ClientAssertionCredential(
    tenant_id=tenant_id,
    client_id=client_id,
    func=token_provider,
    authority=authority,
)

token_response = credential.get_token(scope)
```

### Why this matters

This means the **token-only mount path is not blocked by `cloud-provider-azure`**.
It bypasses that library entirely.

So even if `cloud-provider-azure` learned Azure Proxy / identity binding mode,
that alone would **not** make `mountWithWorkloadIdentityToken: "true"` work with
AKS identity bindings.

### Smallest change point for this path

#### In `azurefile-csi-driver`

The smallest driver-side hook is:

- `pkg/azurefile/utils.go`
- `setCredentialCache(...)`

If `azfilesauthmanager` ever supports Azure Proxy mode, the CSI driver would only
need to pass one more CLI flag or environment variable through this helper.

#### In AzFilesAuthenticator

The real behavioral fix lives in:

- `src/azfilesauthmanager.py`
- `get_workload_identity_token(...)`

That function needs to learn AKS identity-binding-aware token acquisition,
most likely by moving away from a raw `ClientAssertionCredential`-only flow and
using an identity-binding-capable workload identity flow instead.

### Bottom line for path 2

For **`mountWithWorkloadIdentityToken: "true"`**, the smallest true change point is:

- **driver-side integration point:** `azurefile-csi-driver/pkg/azurefile/utils.go`
- **real implementation change:** `Azure/AzFilesAuthenticator/src/azfilesauthmanager.py`

This path cannot be fixed by changing only `cloud-provider-azure`.

---

## Minimal change matrix

| Scenario | Current token exchange location | Smallest useful change point | Extra dependency |
|---|---|---|---|
| Workload identity used for ARM/account-key retrieval | `cloud-provider-azure` | `pkg/azclient/auth_func.go` | Azure SDK for Go may need public Azure Proxy option |
| Driver config plumbing for above | `azurefile-csi-driver` | `pkg/azurefile/azure.go` | Needs config/env wire-up |
| `mountWithWorkloadIdentityToken: "true"` token-only mount | `azfilesauthmanager` / AzFilesAuthenticator | `src/azfilesauthmanager.py` | CSI driver only needs thin flag plumbing in `pkg/azurefile/utils.go` |

---

## Practical recommendation

If the goal is to add identity binding support with the smallest review surface,
do it in **two stages**:

### Stage 1
Support AKS identity bindings for the **traditional workload identity -> ARM / account-key** path.

Target repos/files:

- `cloud-provider-azure/pkg/azclient/auth_conf.go`
- `cloud-provider-azure/pkg/azclient/auth_func.go`
- `azurefile-csi-driver/pkg/azurefile/azure.go`

### Stage 2
Support AKS identity bindings for **`mountWithWorkloadIdentityToken: "true"`**.

Target repos/files:

- `azurefile-csi-driver/pkg/azurefile/utils.go`
- `Azure/AzFilesAuthenticator/src/azfilesauthmanager.py`

This split keeps the first change small and avoids coupling ARM auth and node-side
SMB OAuth cache logic into a single patch.

---

## Direct answer

### Does AKS new identity binding support Azure File CSI workload identity doc directly?

**No, not directly today.**

### Where is the smallest change point?

- For **account-key / ARM workload identity**: start in **`cloud-provider-azure/pkg/azclient/auth_func.go`**
- For **`mountWithWorkloadIdentityToken: "true"`**: the real change is in **AzFilesAuthenticator** (`src/azfilesauthmanager.py`), with only light plumbing in `azurefile-csi-driver/pkg/azurefile/utils.go`
