# syntax=docker/dockerfile:1
FROM registry.access.redhat.com/ubi9/go-toolset:1.23 AS ui-builder
USER 0
ARG KUSTOMIZE_VERSION=5.7.1
ARG HELM_VERSION=3.17.3
ARG TARGETARCH
RUN dnf install -y curl-minimal && dnf clean all
WORKDIR /opt/build
COPY go.mod ./
COPY cmd ./cmd
COPY internal ./internal
RUN set -eux; \
    mkdir -p /opt/bin /tmp/tool-downloads; \
    target_arch="${TARGETARCH:-$(uname -m)}"; \
    case "$target_arch" in x86_64|amd64) target_arch=amd64 ;; aarch64|arm64) target_arch=arm64 ;; *) echo "Unsupported build architecture: $target_arch" >&2; exit 1 ;; esac; \
    CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /opt/bin/installer-ui ./cmd/installer-ui; \
    kustomize_archive="kustomize_v${KUSTOMIZE_VERSION}_linux_${target_arch}.tar.gz"; \
    kustomize_url="https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v${KUSTOMIZE_VERSION}"; \
    curl --proto '=https' --tlsv1.2 -fsSL "${kustomize_url}/${kustomize_archive}" -o "/tmp/tool-downloads/${kustomize_archive}"; \
    curl --proto '=https' --tlsv1.2 -fsSL "${kustomize_url}/checksums.txt" -o /tmp/tool-downloads/kustomize-checksums.txt; \
    cd /tmp/tool-downloads; \
    checksum_line="$(grep "  ${kustomize_archive}$" kustomize-checksums.txt)"; \
    printf '%s\n' "$checksum_line" | sha256sum -c -; \
    tar -xzf "${kustomize_archive}" -C /opt/bin kustomize; \
    helm_archive="helm-v${HELM_VERSION}-linux-${target_arch}.tar.gz"; \
    helm_url="https://get.helm.sh/${helm_archive}"; \
    curl --proto '=https' --tlsv1.2 -fsSL "${helm_url}" -o "/tmp/tool-downloads/${helm_archive}"; \
    curl --proto '=https' --tlsv1.2 -fsSL "${helm_url}.sha256" -o "/tmp/tool-downloads/${helm_archive}.sha256"; \
    printf '%s  %s\n' "$(cat "/tmp/tool-downloads/${helm_archive}.sha256")" "${helm_archive}" | sha256sum -c -; \
    mkdir -p /tmp/tool-downloads/helm; \
    tar -xzf "/tmp/tool-downloads/${helm_archive}" -C /tmp/tool-downloads/helm; \
    install -m 0755 "/tmp/tool-downloads/helm/linux-${target_arch}/helm" /opt/bin/helm
WORKDIR /opt/build/ui
COPY go.mod ./
COPY cmd ./cmd
COPY internal ./internal
RUN CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /opt/bin/installer-ui ./cmd/installer-ui

WORKDIR /opt/build/tools
COPY build-tools/go.mod ./go.mod
COPY build-tools/go.sum ./go.sum
RUN GOBIN=/opt/bin go install sigs.k8s.io/kustomize/kustomize/v5 && \
    GOBIN=/opt/bin go install helm.sh/helm/v3/cmd/helm

FROM registry.access.redhat.com/ubi9/ubi:9.6
ARG OPENSHIFT_VERSION=4.18.41
RUN dnf install -y \
      ca-certificates curl-minimal findutils git gzip jq openssh-clients podman \
      python3.12 python3.12-pip shadow-utils tar && \
    dnf clean all

WORKDIR /workspace
COPY requirements.txt requirements.yml ansible.cfg ./
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt && \
    ansible-galaxy collection install -r requirements.yml -p /workspace/.collections

ARG TARGETARCH
RUN set -eux; \
    target_arch="${TARGETARCH:-$(uname -m)}"; \
    case "$target_arch" in x86_64|amd64) target_arch=amd64 ;; aarch64|arm64) target_arch=arm64 ;; *) echo "Unsupported build architecture: $target_arch" >&2; exit 1 ;; esac; \
    if [ "$target_arch" = arm64 ]; then \
      client_archive="openshift-client-linux-arm64-${OPENSHIFT_VERSION}.tar.gz"; \
    else \
      client_archive="openshift-client-linux-${OPENSHIFT_VERSION}.tar.gz"; \
    fi; \
    curl --proto '=https' --tlsv1.2 -fsSL \
      "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OPENSHIFT_VERSION}/${client_archive}" \
      -o /tmp/oc.tar.gz; \
    tar -xzf /tmp/oc.tar.gz -C /usr/local/bin oc kubectl; \
    oc_mirror_archive="oc-mirror-rhel9-linux-${target_arch}.tar.gz"; \
    curl --proto '=https' --tlsv1.2 -fsSL \
      "https://mirror.openshift.com/pub/cgw/oc-mirror/latest/${oc_mirror_archive}" \
      -o /tmp/oc-mirror.tar.gz; \
    tar -xzf /tmp/oc-mirror.tar.gz -C /usr/local/bin oc-mirror; \
    chmod 0755 /usr/local/bin/oc /usr/local/bin/kubectl /usr/local/bin/oc-mirror; \
    rm -f /tmp/oc.tar.gz /tmp/oc-mirror.tar.gz

COPY --from=ui-builder /opt/bin/installer-ui /usr/local/bin/installer-ui
COPY --from=ui-builder /opt/bin/kustomize /usr/local/bin/kustomize
COPY --from=ui-builder /opt/bin/helm /usr/local/bin/helm
COPY . /workspace
COPY scripts/container-entrypoint.sh /usr/local/bin/container-entrypoint

RUN chmod 0755 /usr/local/bin/installer-ui /usr/local/bin/kustomize /usr/local/bin/helm /usr/local/bin/container-entrypoint && \
    useradd --uid 10001 --gid 0 --home-dir /data/home --shell /sbin/nologin installer && \
    mkdir -p /data /workspace/artifacts && \
    chown -R 10001:0 /data /workspace/artifacts && \
    chmod -R g=u /data /workspace/artifacts

ENV INSTALLER_UI_REPOSITORY_ROOT=/workspace \
    INSTALLER_UI_DATA_ROOT=/data \
    INSTALLER_UI_HOME=/data/home \
    INSTALLER_UI_LISTEN=0.0.0.0:8080 \
    INSTALLER_UI_PYTHON=python3.12 \
    ANSIBLE_HOME=/data/home/.ansible \
    ANSIBLE_COLLECTIONS_PATH=/workspace/.collections:/usr/share/ansible/collections \
    GIT_CONFIG_GLOBAL=/data/home/.gitconfig \
    XDG_CACHE_HOME=/data/home/.cache \
    PATH=/usr/local/bin:/usr/bin:/bin
USER 10001
EXPOSE 8080
VOLUME ["/data"]
HEALTHCHECK --interval=20s --timeout=3s --start-period=15s --retries=3 CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1
ENTRYPOINT ["/usr/local/bin/container-entrypoint"]
