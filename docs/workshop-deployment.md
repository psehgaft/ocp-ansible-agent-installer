# Deploying the workshop

The published workshop — **OpenShift Automation Framework Workshop** — is a
single static page, `workshop/index.html`, built on the
[Open Demo Days workshop template](https://github.com/OpenDemoDays/open-demo-day-template).
It needs no build step, dependencies, or compilation: the page is available
in four languages (English by default, plus Spanish, Portuguese, and German
via `?lang=`), and its sections, cards, navigation, table of contents,
and previous/next buttons are generated from the `steps` and `cards` arrays in
that file.

The full AsciiDoc sources remain under `workshop/documentation` as reference
material and are linked from the site's Resources section.

## GitHub Pages

1. Open **Settings → Pages** in the repository.
2. Select **GitHub Actions** as the build source.
3. Merge or push changes to `workshop/index.html`, or manually run **Build and
   publish workshop site** from the Actions tab.
4. The workflow copies `workshop/index.html` to the site root of the Pages
   artifact and adds a redirect at the legacy Antora URL
   (`ocp-redfish-installer/main/`) pointing to the new home.

Published URL:

```text
https://psehgaft.github.io/ocp-ansible-agent-installer/
```

Local preview:

```bash
python3 -m http.server 8080 --directory workshop
# open http://127.0.0.1:8080/index.html (add ?lang=en for English)
```

## Editing the workshop

1. Edit `workshop/index.html`.
2. Add or change sections in the `steps` array; add a matching entry to
   `cards` for every section that must appear on the home page.
3. Keep visible text complete in every language: titles and summaries use
   the template's `lang` expressions, and each step carries its English,
   Spanish, Portuguese, and German HTML.
4. Push to `main`; GitHub Pages deploys the page automatically.

## OpenShift

Serve the static file with any web server image, for example an NGINX binary
build using `workshop/index.html` as the only site content:

```bash
oc new-project ocp-redfish-workshop
oc new-build --name=ocp-redfish-workshop --binary --strategy=docker
mkdir -p www && cp workshop/index.html www/
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
