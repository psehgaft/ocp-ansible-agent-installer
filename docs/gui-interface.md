# Containerized GUI Interface

The GUI interface provides a Go web application that turns the repository's
existing YAML contracts into guided forms. It creates isolated installation profiles,
encrypts credentials with Ansible Vault, and runs only an allowlisted set of
Day-0 and Day-2 playbooks. It does not replace Ansible, Assisted Installer, or
OpenShift GitOps.

## Architecture and control boundary

```mermaid
flowchart TD
    A["Browser forms"] --> B["Go API and RBAC"]
    B --> C["YAML contract helper"]
    C --> D["Generated inventory and encrypted Vault"]
    B --> E["Allowlisted run manager"]
    E --> F["Ansible and OpenShift clients"]
    F --> G["Bare metal or GitOps bootstrap"]
```

The Go service never accepts an arbitrary command or playbook path. Available
actions come from `framework/gui-actions.yml`. Defaults and operator choices
come from:

- `inventories/sample/group_vars/all/*.yml`;
- `inventories/sample/group_vars/vault.yml.example`;
- `framework/day2-operator-catalog.yml`;
- presentation and conditional-validation hints in
  `framework/gui-variable-metadata.yml`.

The metadata file does not duplicate defaults. A new top-level inventory
variable appears automatically in the UI even when it has no custom metadata.

## Included capabilities

- grouped forms for cluster, Assisted Installer API, networking, disconnected
  installation, BMC/Redfish, runtime, GitOps, and secrets;
- dynamic host cards for iLO, iDRAC, generic Redfish, and automatic detection;
- static or DHCP node networking and explicit installation disk selection;
- profiles and individual selection for all Day-2 operators;
- complete structured values represented as JSON, which is valid YAML;
- conditional and server-side validation;
- encrypted Vault creation without writing credentials into the source tree;
- `viewer`, `operator`, and `admin` bearer-token roles;
- exact confirmation phrases for mirror, boot, install, eject, and GitOps
  deployment actions;
- one active playbook at a time, cancellation, persisted run metadata, audit
  events, and restored history after restart;
- streamed playbook output with submitted secret values and common credential
  assignments redacted;
- downloadable non-sensitive configuration previews and execution reports;
- liveness health check and persistent `/data` volume.

## Build and start on Linux and macOS

The GUI runs in a Linux container, so the host can be Linux or macOS.
Compose builds the image for the architecture of the container engine. The
Containerfile detects `amd64` or `arm64` and installs matching Kustomize,
Helm, OpenShift CLI, and `oc-mirror` binaries. Intel Macs and x86_64 Linux use
`amd64`; Apple Silicon Macs and ARM64 Linux use `arm64`.

Install one container runtime:

- Linux: Podman with Compose support, or Docker Engine and the Compose plugin.
- macOS: Podman Desktop with a running Podman machine, or Docker Desktop.

For Podman on macOS, initialize and start its Linux VM once:

```bash
podman machine init
podman machine start
```

Generate an unpredictable admin token and start the GUI with Podman Compose:

```bash
export INSTALLER_UI_AUTH_TOKENS="$(openssl rand -hex 24)=admin"
podman compose up --build -d
```

For Docker Compose, use the same token variable:

```bash
export INSTALLER_UI_AUTH_TOKENS="$(openssl rand -hex 24)=admin"
docker compose up --build -d
```

Open `http://127.0.0.1:8080`, select **Access token**, and enter the token.
The named volume `installer-ui-data` retains profiles and run history across
container restarts. Stop the GUI with `podman compose down` or
`docker compose down`; this keeps the volume. Use `down --volumes` only when
you intend to delete the stored profiles and history.

The first build downloads pinned Kustomize and Helm release archives and checks
their SHA-256 digests. This avoids resolving their full Go module graphs during
the image build. If Compose prints a Docker Compose Bake/BuildKit warning, it
is informational; the build can continue. The auth token must be set in the
same shell that runs Compose.

The container fails closed when it listens on a non-loopback address without
`INSTALLER_UI_AUTH_TOKENS`. The variable accepts comma-separated `token=role`
pairs:

```bash
INSTALLER_UI_AUTH_TOKENS="viewer-token-at-least-16=viewer,operator-token-at-least-16=operator,admin-token-at-least-16=admin"
```

Use TLS at the ingress or reverse proxy. Bearer tokens must not traverse an
unencrypted external network.

## Troubleshooting the container build

An error beginning with `verifying module: sigs.k8s.io/kustomize/kustomize/v5`
comes from the former version-suffixed `go install` step. That form resolves
the requested tool in a separate module context and does not use this
repository's `go.mod` or `go.sum`. The current Containerfile instead downloads
pinned upstream release archives and verifies their SHA-256 digests.

If DNF reports a conflict between `coreutils` and `coreutils-single`, update
to the corrected Containerfile: UBI already includes `sha256sum`, so the build
does not need to replace that package.

After updating the checkout, rebuild the GUI image:

```bash
podman compose build --no-cache installer-ui
podman compose up -d
```

Use `docker compose` in place of `podman compose` when running Docker. The
Compose Bake/BuildKit warning in Docker's output is separate from the earlier
module verification failure and is not itself a build failure. Keep checksum
verification enabled; do not work around this error by disabling Go's checksum
database.

## Container runtime contents

The image builds and tests the Go application, installs the repository's
Python and Ansible requirements and collections, and includes:

- `ansible-playbook` and `ansible-vault`;
- `oc` and `kubectl` for the configured OpenShift 4.18 z-stream;
- `oc-mirror` v2;
- Git and OpenSSH clients;
- Kustomize and Helm;
- Podman for workflows that require container operations;
- the complete repository and the compiled `installer-ui` binary.

`OPENSHIFT_VERSION` is a Containerfile build argument and defaults to
`4.18.41`. Rebuild the image with the z-stream validated for the target
environment.

## Persistent and sensitive data

Generated profiles use this layout:

```text
/data/
├── artifacts/<profile>/
├── inventories/<profile>/
│   ├── hosts.yml
│   ├── .gui-state.json
│   └── group_vars/
│       ├── all/gui-values.yml
│       └── vault.yml
├── runs/<run-id>/
│   ├── run.json
│   └── events.ndjson
├── secrets/<profile>.vault-password
└── audit.ndjson
```

Files containing credentials or execution details use mode `0600`; profile
directories use mode `0700`. By default, the Vault password entered in the UI
is stored under `/data/secrets` so a saved profile remains executable after a
restart. For production, mount a read-only password file and set:

```bash
INSTALLER_UI_VAULT_PASSWORD_FILE=/run/secrets/ansible-vault-password
```

With that setting, the submitted Vault password is ignored and no managed
password file is created.

Never place the persistent data volume in Git. Back it up and protect it using
the same controls as other deployment credentials.

## Roles and actions

| Action | Minimum role | Confirmation |
|---|---:|---:|
| Validate configuration | viewer | None |
| Run preflight | operator | None |
| Discover BMC inventory | operator | None |
| Prepare release mirror | operator | `MIRROR` |
| Boot discovery ISO | admin | `BOOT` |
| Install OpenShift | admin | `INSTALL` |
| Eject virtual media | admin | `EJECT` |
| Render Day-2 GitOps | operator | None |
| Publish and bootstrap GitOps | admin | `GITOPS` |

The Day-2 double-confirmation variables still apply to Git push. The GUI
confirmation authorizes the action but does not silently set
`day2_gitops_git_push_enabled` or `day2_gitops_git_push_confirmed`.

## Network and Podman considerations

The container must reach BMC endpoints, Assisted Installer, DNS, registries,
the desired-state Git repository, and the OpenShift API as required by the
selected workflow. Ensure routing and firewall policy permit those paths.

The `local_http` ISO delivery mode uses Podman. Nested rootless Podman may need
`/dev/fuse` and additional user-namespace configuration. In tightly restricted
environments, use `existing_http` and serve the ISO from an approved external
endpoint, or connect the container client to an approved host Podman service.
Do not grant `--privileged` merely to simplify the UI deployment.

## Development and validation

```bash
make gui-test
python3 scripts/gui_config.py schema --root . | jq '.variables | length'
podman build --target ui-builder -f Containerfile .
```

The GUI interface CI workflow runs formatting, `go vet`, Go race-enabled tests,
Python tests, a binary/API smoke test, and the full container build. Existing
repository validation workflows continue to run unchanged.

## End-to-end procedures

Use the canonical [OpenShift deployment scenarios](deployment-scenarios.md) for
complete, ordered procedures for connected and disconnected installation with
the CLI or GUI, followed by Day-2 GitOps through either interface.


## References

- [Kustomize v5.7.1 release artifacts and checksums](https://github.com/kubernetes-sigs/kustomize/releases/tag/kustomize/v5.7.1)
- [Helm installation and binary verification](https://helm.sh/docs/intro/install/)
- [Podman machine on macOS](https://docs.podman.io/en/latest/markdown/podman-machine.1.html)
- [Docker Compose build specification](https://docs.docker.com/compose/compose-file/build/)
- [OpenShift CLI downloads and supported architectures](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html)
