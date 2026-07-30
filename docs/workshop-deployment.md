# Deploying the workshop

The workshop source under `workshop/documentation` is Antora-compatible AsciiDoc. It must be rendered before publication.

## GitHub Pages

1. Open **Settings → Pages** in the repository.
2. Select **GitHub Actions** as the build source.
3. Merge or push changes affecting the workshop, or manually run **Build and publish Showroom** from the Actions tab.
4. The workflow generates HTML into `www/` and deploys that directory.

Expected project URL:

```text
https://psehgaft.github.io/ocp-ansible-agent-installer/
```

Local preview:

```bash
npm install --global @antora/cli@3.1 @antora/site-generator@3.1
antora generate default-site.yml --stacktrace
python3 -m http.server 8080 --directory www
```

## OpenShift

Build the site locally, then publish the generated `www/` directory with an NGINX binary build:

```bash
antora generate default-site.yml --stacktrace
oc new-project ocp-redfish-workshop
oc new-build --name=ocp-redfish-workshop --binary --strategy=docker
cat > www/Dockerfile <<'DOCKERFILE'
FROM registry.access.redhat.com/ubi9/nginx-124:latest
COPY . /tmp/src
RUN cp -a /tmp/src/. /opt/app-root/src/
DOCKERFILE
oc start-build ocp-redfish-workshop --from-dir=www --follow
oc new-app ocp-redfish-workshop
oc expose service/ocp-redfish-workshop
oc get route ocp-redfish-workshop -o jsonpath='https://{.spec.host}{"\n"}'
```
