# Cut a new release for sig-storage-local-static-provisioner

Repo: https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner

Reference: [`RELEASE.md`](https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner/blob/master/RELEASE.md) in the repo.

Example below assumes cutting **v2.9.0** (new minor after `v2.8.0`).

## Prerequisites

- OWNER permission on the repo (tag push + GitHub release creation).
- CI green on master: https://testgrid.k8s.io/sig-storage-local-static-provisioner#master-gce-lastest
- No PRs about to merge — pick a clean window so the tag matches the CHANGELOG.
- Naming convention for tags:
  - Image tag: `v2.9.0`
  - Helm chart tag: `local-static-provisioner-2.9.0`

---

## 1. Image release

### 1.1 Generate CHANGELOG and open a PR

Use the release-notes tooling described in
[csi-release-tools SIDECAR_RELEASE_PROCESS.md](https://github.com/kubernetes-csi/csi-release-tools/blob/master/SIDECAR_RELEASE_PROCESS.md#release-process).

```bash
git clone https://github.com/kubernetes-csi/csi-release-tools
cd sig-storage-local-static-provisioner

GITHUB_TOKEN=*** \
  release-notes \
  --start-sha $(git rev-list -n1 v2.8.0) \
  --end-sha   $(git rev-parse origin/master) \
  --branch    master \
  --repo      sig-storage-local-static-provisioner \
  --org       kubernetes-sigs \
  --output    CHANGELOG/CHANGELOG-2.9.md
```

Then:

1. Diff generated notes against the actual commits since `v2.8.0` — patch anything missed.
2. Reword as needed. Explicitly call out **breaking changes** and **deprecations**.
3. New major/minor → create a fresh `CHANGELOG/CHANGELOG-2.9.md`. Patch release → prepend to the existing file for that minor.
4. Open the PR, get it merged.
5. Freeze the branch: make sure no further PRs land before you tag.

### 1.2 Push the tag

```bash
git checkout master
git pull upstream master
VERSION=v2.9.0
git tag -a $VERSION -m "$VERSION"
git push upstream $VERSION
```

### 1.3 Create the release branch (new minor only)

```bash
git checkout -b release-2.9 $VERSION
git push upstream release-2.9
```

### 1.4 Create the GitHub Release

- URL: https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner/releases/new
- Tag: `v2.9.0`
- Target: `release-2.9`
- Body: paste `CHANGELOG/CHANGELOG-2.9.md`
- Follow the previous release as a template.

### 1.5 Verify the post-submit image push

Tag push triggers a Prow post-submit that pushes the image to the staging registry:

- Job dashboard: https://testgrid.k8s.io/sig-storage-image-build#post-sig-storage-local-static-provisioner-push-images
- Expected artifact: `gcr.io/k8s-staging-sig-storage/local-volume-provisioner:v2.9.0`

Wait for green.

### 1.6 Promote the image to `registry.k8s.io`

In [`kubernetes/k8s.io`](https://github.com/kubernetes/k8s.io):

```bash
cd registry.k8s.io/images/k8s-staging-sig-storage
./generate.sh
git checkout -b promote-local-volume-provisioner-2.9.0
git add -A
git commit -s -m "promote local-volume-provisioner v2.9.0"
git push origin promote-local-volume-provisioner-2.9.0
```

Open a PR against `kubernetes/k8s.io`, get SIG-Storage approvers to LGTM/approve.
Once merged, the image is pullable at:

```
registry.k8s.io/sig-storage/local-volume-provisioner:v2.9.0
```

---

## 2. Helm chart release

### 2.1 Bump chart version PR

Edit:

- `helm/provisioner/Chart.yaml`

  ```yaml
  version: 2.9.0
  appVersion: 2.9.0
  ```

- `helm/provisioner/values.yaml`

  ```yaml
  image: registry.k8s.io/sig-storage/local-volume-provisioner:v2.9.0
  ```

Regenerate templates:

```bash
./hack/update-generated.sh
git add -A
git commit -s -m "helm: bump chart to 2.9.0"
```

Open PR → merge.

### 2.2 Push the chart tag

```bash
git checkout master
git pull upstream master
CHART_TAG=local-static-provisioner-2.9.0
git tag -a $CHART_TAG -m "$CHART_TAG"
git push upstream $CHART_TAG
```

### 2.3 Wait for `helm-chart-release` GitHub Action

The action will automatically:

- Package the chart.
- Create a GitHub Release with the chart artifacts attached.
- Update `gh-pages` with the manifest served by `helm repo add`.

Verify:

- Action run is green.
- New release visible: https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner/releases
- `gh-pages` manifest updated:
  ```bash
  helm repo add sig-storage-local-static-provisioner \
    https://kubernetes-sigs.github.io/sig-storage-local-static-provisioner/
  helm repo update
  helm search repo sig-storage-local-static-provisioner --versions | head
  ```

---

## Checklist

Image release:

- [ ] CI green on master
- [ ] `CHANGELOG-2.9.md` PR merged
- [ ] Tag `v2.9.0` pushed
- [ ] Branch `release-2.9` created (new minor only)
- [ ] GitHub Release created against `release-2.9`
- [ ] `post-sig-storage-local-static-provisioner-push-images` Prow job green
- [ ] `kubernetes/k8s.io` promotion PR merged
- [ ] `registry.k8s.io/sig-storage/local-volume-provisioner:v2.9.0` pullable

Helm chart:

- [ ] Chart bump PR merged (Chart.yaml + values.yaml + `update-generated.sh`)
- [ ] Tag `local-static-provisioner-2.9.0` pushed
- [ ] `helm-chart-release` action green
- [ ] GitHub Release for chart artifacts created
- [ ] `gh-pages` manifest updated; new version visible via `helm search repo --versions`

---

## Notes / gotchas

- New minor → **must** create `release-<minor>` branch at the tag commit (used for future patch releases).
- Existing tags in the repo use two naming schemes side-by-side: `v2.8.0` for the code/image release and `local-static-provisioner-2.8.0` for the helm chart. Keep both.
- `kubernetes/k8s.io` promotion is the gating step for `registry.k8s.io/...` — until that PR merges, users can only pull the staging image.
- Don't modify vendored `release-tools/` (comes from `csi-release-tools`); override via env vars if needed.
