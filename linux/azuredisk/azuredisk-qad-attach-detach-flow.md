# Azure Disk CSI Driver QAD Attach/Detach Flow

This note analyzes the new disk attach/detach behavior in:

- upstream branch: `feature/qad`
- file: `pkg/azuredisk/nodeserver.go`

Related code paths also referenced below:

- `pkg/azuredisk/controllerserver.go`
- `pkg/azuredisk/azuredisk.go`
- `pkg/azureconstants/azure_constants.go`

## Summary

The new QAD path changes the responsibility split for disk attach/detach:

- **Classic path**
  - `ControllerPublishVolume` performs attach and returns `LUN`
  - `NodeStageVolume` uses the `LUN` to find the device and mount it
  - `ControllerUnpublishVolume` performs detach

- **QAD path**
  - `ControllerPublishVolume` does **not** actually attach the disk
  - it prepares and persists QAD metadata on the PV
  - `NodeStageVolume` performs the real **ATTACH** through the QAD wireserver endpoint
  - `NodeUnstageVolume` performs the real **DETACH** through the QAD wireserver endpoint
  - `ControllerUnpublishVolume` skips detach for QAD-enabled volumes

In short: **attach/detach moves from the controller side to the node side**.

---

## How the QAD path is recognized

On the node side, QAD is determined by checking whether the matching PV carries QAD annotations, rather than by relying only on transient request parameters.

Key annotations:

- `azuredisk.csi.azure.com/attach-sequence`
- `azuredisk.csi.azure.com/blob-url`
- `azuredisk.csi.azure.com/claim-identifier`

Constants:

- `pkg/azureconstants/azure_constants.go`
  - `QADWireserverEndpoint = "http://168.63.129.16/vmservice/diskstate"`
  - `AttachSequenceAnnotation = "azuredisk.csi.azure.com/attach-sequence"`
  - `BlobURLAnnotation = "azuredisk.csi.azure.com/blob-url"`
  - `ClaimIdentifierAnnotation = "azuredisk.csi.azure.com/claim-identifier"`

Node-side detection:

- `pkg/azuredisk/nodeserver.go:isUsingQADPath(...)`
- `pkg/azuredisk/azuredisk.go:getPVFromDiskURI(...)`

Behavior:

1. Find the PV from `diskURI`
2. If the PV has `attach-sequence`, treat it as a QAD volume
3. Use `blob-url` and `claim-identifier` from the PV annotations for attach/detach requests

---

## Controller-side preparation

### CreateVolume

When `qadenabled=true`, `CreateVolume` claims the disk resource and places QAD metadata into `VolumeContext`.

Relevant logic:

- `pkg/azuredisk/controllerserver.go` around `CreateVolume`

Observed behavior:

1. Create managed disk in Azure
2. If `qadenabled=true`, call `claimDiskResource(...)`
3. Get:
   - `blobURL`
   - `claimIdentifier`
4. Put them into `diskParams.VolumeContext`

This is preparation only; the actual attach still happens later on the node side.

### ControllerPublishVolume

Relevant code:

- `pkg/azuredisk/controllerserver.go:917-963`

QAD behavior:

1. Check `qadenabled` in `volumeContext`
2. Claim the disk again via `claimDiskResource(...)`
   - current code comments say this is also helping the static provisioning case
3. Look up the PV from `diskURI`
4. If PV does not already have QAD annotations, write:
   - `attach-sequence = "0"`
   - `blob-url = ...`
   - `claim-identifier = ...`
5. Return success immediately

Important difference from classic behavior:

- In QAD mode, `ControllerPublishVolume` does **not** call traditional Azure attach logic
- It also does **not** return a controller-computed `LUN` in `PublishContext`

So controller publish becomes a **prepare/persist metadata** step, not the real attach step.

### ControllerUnpublishVolume

Relevant code:

- `pkg/azuredisk/controllerserver.go:1056-1075`

QAD behavior:

1. Get PV from `diskURI`
2. If PV has `attach-sequence` annotation, treat it as QAD
3. Skip detach and return success

Code comment says the disk should already have been detached in `NodeUnstageVolume`.

---

## Node-side attach behavior

### Entry point: NodeStageVolume

Relevant code:

- `pkg/azuredisk/nodeserver.go:241-317`

The logic is now split into two branches.

### Classic branch

If the volume is **not** using QAD:

1. Read `LUN` from `req.PublishContext["LUN"]`
2. Resolve device path from LUN
3. Format/mount as before

### QAD branch

If the volume **is** using QAD:

1. Read `blobURL` and `claimIdentifier` from PV annotations
2. Increment `attach-sequence` on the PV
3. Enqueue a QAD ATTACH request
4. Wait for attach completion if needed
5. Read the `LUN` from the QAD/wireserver response
6. Resolve device path from LUN
7. Continue with format/mount

### Attach sequence increment

Relevant code:

- `pkg/azuredisk/nodeserver.go:1041-1062`

Behavior:

1. Read current `attach-sequence` from PV annotation
2. Increment it by 1
3. Update the PV object through the Kubernetes API
4. Return the new value

This sequence is used both for attach and detach. It acts like an operation generation/version, not just a simple attach counter.

### Batching behavior

Relevant code:

- `pkg/azuredisk/azuredisk.go:294-299`
- `pkg/azuredisk/nodeserver.go:1065-1163`
- `pkg/azuredisk/nodeserver.go:655-701`

Behavior:

- Node driver initializes:
  - `httpClient`
  - `qadBatcher`
- There are two separate queues:
  - `attachQueue`
  - `detachQueue`
- Requests are flushed when:
  - the batching time window expires, or
  - the queue size reaches `maxDataDiskCount`

Details:

- `NewDriver()` currently initializes `newQADDiskBatcher(1000 * time.Millisecond)`
- so the effective batching window is **1 second**
- batch size is derived from cached `maxDataDiskCount`
- if unavailable, it falls back to `defaultAzureVolumeLimit`

### Actual ATTACH request to wireserver

Relevant code:

- `pkg/azuredisk/nodeserver.go:1165-1262`

The node builds a POST request to:

- `http://168.63.129.16/vmservice/diskstate`

The request contains:

- a VM access token obtained from node credentials
- one or more disk operations

Shape:

```json
{
  "vmAccessToken": "...",
  "diskOps": {
    "<diskURI>": {
      "blobUrl": "...",
      "claimIdentifier": "...",
      "attachSequence": 1,
      "action": "ATTACH",
      "cachePolicy": "None"
    }
  }
}
```

Notable detail:

- token scope is `https://management.azure.com//.default`
- the code comment explains the double slash is intentional so the resulting audience includes a trailing slash

### How NodeStageVolume obtains the LUN

Relevant code:

- `pkg/azuredisk/nodeserver.go:271-305`
- `pkg/azuredisk/nodeserver.go:1397-1432`

Returned disk status can be either:

- `DISK_STATUS_ATTACHED`
- `DISK_STATUS_ATTACHING`

Behavior:

- If `ATTACHED`, use the returned `LUN` directly
- If `ATTACHING`, poll `GET /vmservice/diskstate` until the disk becomes `ATTACHED`
- Then use the returned `LUN`

Polling details:

- interval: `250ms`
- timeout: `5s`

Only after the `LUN` is known does the node continue with:

- `getDevicePathWithLUN(lun)`
- format
- mount

So under QAD, **the node discovers the LUN itself after attach completes**.

---

## Node-side detach behavior

### Entry point: NodeUnstageVolume

Relevant code:

- `pkg/azuredisk/nodeserver.go:434-485`

Behavior:

1. Unmount the staging target path first
2. If volume is using QAD:
   - read `blobURL` and `claimIdentifier` from PV annotations
   - increment `attach-sequence`
   - enqueue a QAD DETACH request
   - poll wireserver until the disk disappears from the attached-disk list

### Actual DETACH request

The request shape is the same as attach, except:

- `action = "DETACH"`

### Detach completion logic

Behavior:

- If the response does not contain the disk, treat it as already detached
- If the status is `DISK_STATUS_DETACHING`, poll until the disk is absent from `GET /vmservice/diskstate`

Polling details:

- interval: `500ms`
- timeout: `5s`

This is why `ControllerUnpublishVolume` later skips detach for QAD volumes.

---

## Error handling model

Relevant code:

- `pkg/azuredisk/nodeserver.go:1265-1395`

The implementation distinguishes three kinds of failures.

### 1. HTTP 2xx with per-disk error

A batch POST can succeed overall, but individual disks can still fail through `diskStatus.Error`.

Examples:

- `QADDiskErrAttachSequenceMismatch -> codes.Aborted`
- `QADDiskErrDiskNotFound -> codes.NotFound`
- `QADDiskErrNoLUNAvailable -> codes.ResourceExhausted`
- retriable internal/auth issues -> `codes.Unavailable`

### 2. HTTP non-2xx with QAD JSON error response

Examples:

- `QADRequestErrFetchAttachedDisks`
- `QADRequestErrFetchVMAccessToken`
- `QADRequestErrMadariCGSPublish`

Mapped to gRPC codes such as:

- `InvalidArgument`
- `Unauthenticated`
- `Unavailable`
- `Internal`

### 3. HTTP non-2xx generic wireserver failure

Mapped by HTTP status code, for example:

- `400 -> InvalidArgument`
- `404 -> NotFound`
- `429 -> Aborted`
- `503 -> Unavailable`
- `504 -> DeadlineExceeded`

---

## End-to-end QAD sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as User / PVC
    participant EP as external-provisioner / attacher
    participant CC as CSI Controller
    participant API as Kubernetes API (PV)
    participant QS as QAD claim service
    participant NP as CSI Node plugin
    participant WS as QAD WireServer (168.63.129.16)
    participant OS as Node OS / SCSI / filesystem

    U->>EP: Create PVC
    EP->>CC: CreateVolume

    rect rgb(235,245,255)
    Note over CC,QS: CreateVolume
    CC->>CC: Create managed disk in Azure
    alt qadenabled=true
        CC->>QS: claimDiskResource(diskURI, clusterOwner)
        QS-->>CC: blobURL, claimIdentifier
        CC->>EP: CreateVolumeResponse\nVolumeId=diskURI\nVolumeContext includes qadenabled/blobURL/claimIdentifier
    else classic path
        CC->>EP: normal CreateVolumeResponse
    end
    end

    EP->>CC: ControllerPublishVolume(nodeID, volumeContext)

    rect rgb(235,245,255)
    Note over CC,API: ControllerPublishVolume
    alt qadenabled=true
        CC->>QS: claimDiskResource(...)
        QS-->>CC: blobURL, claimIdentifier
        CC->>API: get PV by diskURI
        API-->>CC: PV
        alt PV missing QAD annotations
            CC->>API: update PV annotations:\nattach-sequence=0\nblob-url=...\nclaim-identifier=...
            API-->>CC: PV updated
        else already annotated
            CC->>CC: no-op
        end
        CC-->>EP: ControllerPublishVolumeResponse\n(no actual attach, no LUN)
    else classic path
        CC->>CC: AttachDisk via Azure ARM/compute
        CC-->>EP: PublishContext{LUN=...}
    end
    end

    EP->>NP: NodeStageVolume(volumeID, stagingTargetPath, volumeContext, publishContext)

    rect rgb(235,245,255)
    Note over NP,WS: NodeStageVolume
    NP->>API: get PV by diskURI
    API-->>NP: PV
    alt PV has attach-sequence annotation (QAD path)
        NP->>API: increment PV annotation attach-sequence += 1
        API-->>NP: updated sequence
        NP->>NP: enqueueQADDiskOperation(ATTACH)\n(batch by timer / maxDataDiskCount)
        NP->>WS: POST /vmservice/diskstate\n{vmAccessToken, diskOps[diskURI]={blobURL, claimIdentifier, attachSequence, action=ATTACH}}
        alt response status = ATTACHED
            WS-->>NP: diskStatus{ATTACHED, lun}
        else response status = ATTACHING
            WS-->>NP: diskStatus{ATTACHING}
            loop until attached or 5s timeout
                NP->>WS: GET /vmservice/diskstate
                WS-->>NP: diskStatus map
            end
        end
        NP->>NP: resolve LUN from response
    else classic path
        NP->>NP: read LUN from PublishContext
    end

    NP->>OS: rescan + find device by LUN
    OS-->>NP: /dev/... devicePath
    alt filesystem volume
        NP->>OS: format if needed + mount to staging path
        NP->>OS: resize fs if needed
    else raw block volume
        NP->>OS: no stage mount work
    end
    NP-->>EP: NodeStageVolumeResponse
    end

    EP->>NP: NodePublishVolume(targetPath)

    rect rgb(245,255,235)
    Note over NP,OS: NodePublishVolume
    NP->>OS: bind mount staging path -> targetPath\n(or block bind mount)
    OS-->>NP: mounted
    NP-->>EP: NodePublishVolumeResponse
    end

    U->>EP: Pod/PVC teardown
    EP->>NP: NodeUnstageVolume(stagingTargetPath)

    rect rgb(255,245,235)
    Note over NP,WS: NodeUnstageVolume
    NP->>OS: unmount staging path
    OS-->>NP: unmounted

    NP->>API: get PV by diskURI
    API-->>NP: PV
    alt PV has attach-sequence annotation (QAD path)
        NP->>API: increment PV annotation attach-sequence += 1
        API-->>NP: updated sequence
        NP->>NP: enqueueQADDiskOperation(DETACH)
        NP->>WS: POST /vmservice/diskstate\n{vmAccessToken, diskOps[diskURI]={blobURL, claimIdentifier, attachSequence, action=DETACH}}
        alt response says already absent
            WS-->>NP: no disk entry / already detached
        else response status = DETACHING
            WS-->>NP: diskStatus{DETACHING}
            loop until missing from GET result or 5s timeout
                NP->>WS: GET /vmservice/diskstate
                WS-->>NP: diskStatus map
            end
        end
    else classic path
        NP->>NP: no detach here
    end
    NP-->>EP: NodeUnstageVolumeResponse
    end

    EP->>CC: ControllerUnpublishVolume(nodeID, volumeID)

    rect rgb(255,245,235)
    Note over CC,API: ControllerUnpublishVolume
    CC->>API: get PV by diskURI
    API-->>CC: PV
    alt PV has attach-sequence annotation (QAD path)
        CC->>CC: detect QAD volume
        CC-->>EP: success; skip detach\n(detach already done in NodeUnstageVolume)
    else classic path
        CC->>CC: DetachDisk via Azure ARM/compute
        CC-->>EP: success
    end
    end
```

---

## Key differences from the classic path

1. **ControllerPublishVolume no longer performs the real attach** for QAD volumes
2. **NodeStageVolume becomes responsible for attach**
3. **NodeUnstageVolume becomes responsible for detach**
4. **ControllerUnpublishVolume skips detach** for QAD volumes
5. **LUN is discovered by the node after QAD attach completes**, not precomputed by the controller
6. **attach-sequence** becomes a core sequencing mechanism for attach/detach operations
7. **batched node-local attach/detach** is introduced to coalesce concurrent operations

---

## Implementation observations / risks worth reviewing

1. **Attach/detach poll timeout is only 5 seconds**
   - attach polling interval: `250ms`
   - detach polling interval: `500ms`
   - this may be aggressive if the backend occasionally reacts slowly

2. **PV update conflicts may matter**
   - both attach and detach increment `attach-sequence` by updating the PV directly
   - concurrent update conflicts are possible if multiple actors touch the PV metadata

3. **Unmount happens before detach**
   - if unmount succeeds but QAD detach fails, the node path is already unstaged while the disk may still remain attached at the VM level

4. **Controller and node split relies on PV annotations being correct**
   - if the annotation write is missing/corrupted, the node may fall back to classic expectations while controller publish no longer provides a LUN

5. **Current code comments imply some temporary behavior for static provisioning**
   - especially around claiming the disk again in `ControllerPublishVolume`

---

## One-line takeaway

QAD changes Azure Disk CSI from a **controller-attached / controller-detached** model into a **controller-prepared, node-attached, node-detached** model, with PV annotations and attach-sequence acting as the handoff contract between controller and node.
