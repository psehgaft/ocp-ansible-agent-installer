<#
.SYNOPSIS
  Windows/PowerShell equivalent of `make gui-build` + `make gui-run`.

.DESCRIPTION
  Builds the installer GUI container image and runs it on the bastion with a
  persistent data volume. Requires Podman (podman machine) or Docker Desktop
  for Windows, which run the Linux container unchanged.

  Set the access token first, in the canonical form (or the legacy
  INSTALLER_UI_ADMIN_TOKEN variable, which is mapped to an =admin token):
    $env:INSTALLER_UI_AUTH_TOKENS = "<48-hex-chars>=admin"
    .\scripts\gui-run.ps1

  Then open http://127.0.0.1:8080 in a browser.
#>
[CmdletBinding()]
param(
    [string]$Image = "ocp-ansible-agent-installer-ui:gui",
    [string]$ContainerName = "ocp-installer-ui",
    [string]$Volume = "ocp-installer-ui-data"
)

$ErrorActionPreference = "Stop"

$authTokens = $env:INSTALLER_UI_AUTH_TOKENS
if (-not $authTokens) {
    if (-not $env:INSTALLER_UI_ADMIN_TOKEN -or $env:INSTALLER_UI_ADMIN_TOKEN.Length -lt 16) {
        throw "Set INSTALLER_UI_AUTH_TOKENS (for example `"<48-hex-chars>=admin`") or INSTALLER_UI_ADMIN_TOKEN (at least 16 characters) first."
    }
    $authTokens = "$($env:INSTALLER_UI_ADMIN_TOKEN)=admin"
}

$runtime = $null
foreach ($candidate in @("podman", "docker")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) { $runtime = $candidate; break }
}
if (-not $runtime) {
    throw "Neither podman nor docker was found. Install Podman (with a podman machine) or Docker Desktop for Windows."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    & $runtime build -f Containerfile -t $Image .
    if ($LASTEXITCODE -ne 0) { throw "Container build failed." }
    & $runtime run --rm --name $ContainerName `
        -p 127.0.0.1:8080:8080 `
        -e "INSTALLER_UI_AUTH_TOKENS=$authTokens" `
        -v "${Volume}:/data" $Image
    if ($LASTEXITCODE -ne 0) { throw "Container run failed." }
}
finally {
    Pop-Location
}
