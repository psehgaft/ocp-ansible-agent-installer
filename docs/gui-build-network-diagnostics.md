# GUI Container Build Network Troubleshooting

Use this guide when `podman compose build` or `docker compose build` fails while downloading Go modules, UBI packages, Python packages, or Ansible collections.

## Identify the failure

These messages point to outbound HTTPS connectivity from the image builder:

- Go: `net/http: TLS handshake timeout` from `proxy.golang.org` or `storage.googleapis.com`.
- UBI/DNF: `Curl error (28)` timeout or `Curl error (35)` SSL connection failure from `cdn-ubi.redhat.com`.
- Similar timeouts from PyPI or Ansible Galaxy.

Retries in the Containerfile handle brief interruptions. They cannot fix a blocked route, unavailable VPN, missing proxy, or a TLS-inspection CA that the build environment does not trust.

The following are generally not the cause of these messages:

- `Unable to read consumer identity` / “not registered with an entitlement server”: UBI informational warning.
- The Compose Bake/BuildKit warning: not a build failure by itself.
- `INSTALLER_UI_AUTH_TOKENS` is a separate Compose configuration requirement, not a network error.

## Test the host and the Podman machine

On Linux, run the host checks. On macOS with Podman, run both the host and VM checks because the build runs through the Linux Podman machine.

From the host:

```bash
curl -Iv --connect-timeout 15 --max-time 30 https://proxy.golang.org/
curl -Iv --connect-timeout 15 --max-time 30 https://cdn-ubi.redhat.com/
```

On macOS with Podman, test from the machine as well:

```bash
podman machine ssh curl -Iv --connect-timeout 15 --max-time 30 https://proxy.golang.org/
podman machine ssh curl -Iv --connect-timeout 15 --max-time 30 https://cdn-ubi.redhat.com/
```

A TLS connection or an HTTP response (including a 403 at a bare CDN root) confirms that the handshake reached the server. A timeout or TLS handshake error from the VM while the host succeeds means the VM's network or proxy path needs configuration. If both fail, check the host's VPN, firewall, DNS, or upstream network policy.

The build may also need access to `storage.googleapis.com`, `pypi.org`, `files.pythonhosted.org`, `galaxy.ansible.com`, and `mirror.openshift.com`.

## Configure a proxy

Use the proxy URL supplied by your network administrator. Do not commit proxy credentials to the repository.

### Linux

Set the proxy variables in the same shell that invokes Podman, then rebuild:

```bash
export HTTP_PROXY="http://proxy.example.com:3128"
export HTTPS_PROXY="http://proxy.example.com:3128"
export NO_PROXY="localhost,127.0.0.1"
podman compose build --no-cache installer-ui
```

Set lowercase `http_proxy`, `https_proxy`, and `no_proxy` too if your proxy or tooling requires them. Podman passes proxy variables from the Podman process into build steps by default.

### macOS with Podman Machine

Podman on macOS uses a remote Podman service in a Linux VM. The remote service uses proxy settings available to that service, so exporting variables only in the macOS Terminal may not configure the build.

If using Podman Desktop, configure the proxy in its proxy settings. For a terminal-managed Podman machine, configure the VM's rootless containers settings (replace the example values):

```bash
podman machine ssh
mkdir -p ~/.config/containers
cat >> ~/.config/containers/containers.conf <<'EOF'
[containers]
http_proxy = true
env = [
  "http_proxy=http://proxy.example.com:3128",
  "https_proxy=http://proxy.example.com:3128",
  "no_proxy=localhost,127.0.0.1"
]
EOF
exit
podman machine stop
podman machine start
```

If `containers.conf` already has a `[containers]` section, add the settings to that section instead of creating a duplicate. Use the proxy URL and exclusions approved for your environment. For rootful Podman, configure the corresponding system-level `containers.conf` instead.

For a TLS-inspecting proxy, its CA certificate must also be trusted by the Podman machine and by the image build environment. Podman Machine can import the host's trusted CA certificates on supported versions:

```bash
podman machine set --import-native-ca=true
podman machine stop
podman machine start
```

Follow your organization's certificate installation procedure when the CA is not installed in the macOS host trust store.

## Retry the build

After correcting connectivity or proxy trust, reload the GUI token in the current shell and rebuild:

```bash
set -a
. ./.installer-ui.vault
set +a
podman compose build --no-cache installer-ui
podman compose up -d
```

For Docker, use `docker compose` in place of `podman compose`. If the host and builder can reach the endpoints but a build still fails, keep the full output from the first failed download and check whether a particular endpoint is blocked by a firewall or proxy policy.
