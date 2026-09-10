import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/gui_config.py"


def helper(command: str, payload: dict | None = None, *arguments: str, env=None):
    return subprocess.run(
        [sys.executable, str(HELPER), command, "--root", str(ROOT), *arguments],
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def valid_payload() -> dict:
    schema = json.loads(helper("schema").stdout)
    values = {
        field["name"]: field["default"]
        for field in schema["variables"]
        if field["group"] != "secrets"
    }
    values["cluster_name"] = "cluster-a"
    values["iso_http_advertise_address"] = "192.0.2.100"
    hosts = []
    for index, item in enumerate(schema["host_defaults"], start=1):
        hosts.append({
            **item,
            "bmc_endpoint": f"https://192.0.2.{index}",
            "bmc_username": "Administrator",
            "bmc_password": "safe-password",
        })
    return {
        "profile": "cluster-a",
        "values": values,
        "hosts": hosts,
        "operators": ["gitops", "acm"],
        "secrets": {
            "vault_pull_secret": '{"auths":{"cloud.openshift.com":{"auth":"safe-auth"}}}',
            "vault_ssh_public_key": "ssh-ed25519 AAAA-test",
            "vault_assisted_offline_token": "safe-offline-token",
        },
        "vault_password": "safe-vault-password",
    }


def test_schema_discovers_repository_defaults_catalog_hosts_and_actions():
    result = helper("schema")
    assert result.returncode == 0, result.stderr
    schema = json.loads(result.stdout)
    source_variables = {
        key
        for path in (ROOT / "inventories/sample/group_vars/all").glob("*.yml")
        for key in yaml.safe_load(path.read_text())
    }
    assert source_variables <= {field["name"] for field in schema["variables"]}
    assert len(schema["operators"]) == 52
    assert len(schema["host_defaults"]) == 5
    assert {"validate", "install", "day2-render", "day2-deploy"} <= set(schema["actions"])
    assert all(field["default"] == "" for field in schema["variables"] if field["group"] == "secrets")


def test_validation_enforces_conditionals_host_counts_and_known_operators():
    payload = valid_payload()
    payload["values"]["deployment_mode"] = "disconnected"
    payload["values"]["disconnected_release_image"] = ""
    payload["hosts"][0]["node_ipv4_address"] = "not-an-ip"
    payload["operators"].append("unknown")
    payload["hosts"].pop()
    result = helper("validate", payload)
    assert result.returncode == 2
    errors = json.loads(result.stdout)["errors"]
    fields = {item["field"] for item in errors}
    assert "hosts[0].node_ipv4_address" in fields
    assert "compute_count" in fields
    assert "operators" in fields


def test_save_generates_inventory_and_encrypts_vault_without_plaintext(tmp_path):
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    fake_vault = binary_dir / "ansible-vault"
    fake_vault.write_text(
        "#!/bin/sh\nfile=\"$4\"\nprintf '$ANSIBLE_VAULT;1.1;AES256\\n66616b65\\n' > \"$file\"\n",
        encoding="utf-8",
    )
    fake_vault.chmod(0o755)
    data_root = tmp_path / "data"
    env = os.environ.copy()
    env["PATH"] = f"{binary_dir}:{env['PATH']}"
    result = helper("save", valid_payload(), "--data-root", str(data_root), env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    output = json.loads(result.stdout)
    inventory = Path(output["inventory"])
    vault = inventory.parent / "group_vars/vault.yml"
    assert inventory.is_file()
    assert vault.read_text().startswith("$ANSIBLE_VAULT;1.1;AES256")
    assert "safe-password" not in vault.read_text()
    assert stat.S_IMODE(vault.stat().st_mode) == 0o600
    generated = yaml.safe_load(inventory.read_text())
    master = generated["all"]["children"]["baremetal"]["children"]["control_plane"]["hosts"]["master-0"]
    assert master["bmc_username"].startswith("{{ vault_bmc_credentials")
    state = json.loads((inventory.parent / ".gui-state.json").read_text())
    assert state["inventory"] == str(inventory)


def test_profile_name_cannot_escape_data_root(tmp_path):
    payload = valid_payload()
    payload["profile"] = "../../outside"
    result = helper("save", payload, "--data-root", str(tmp_path))
    assert result.returncode == 1
    assert "Profile name" in json.loads(result.stdout)["error"]


def test_real_ansible_vault_round_trip_when_binary_is_available(tmp_path):
    ansible_vault = shutil.which("ansible-vault")
    if not ansible_vault:
        return
    data_root = tmp_path / "data"
    result = helper("save", valid_payload(), "--data-root", str(data_root))
    assert result.returncode == 0, result.stdout + result.stderr
    inventory = Path(json.loads(result.stdout)["inventory"])
    state = json.loads((inventory.parent / ".gui-state.json").read_text())
    decrypted = subprocess.run(
        [
            ansible_vault,
            "view",
            "--vault-password-file",
            state["vault_password_file"],
            str(inventory.parent / "group_vars/vault.yml"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert decrypted.returncode == 0, decrypted.stderr
    values = yaml.safe_load(decrypted.stdout)
    assert values["vault_bmc_credentials"]["master-0"]["password"] == "safe-password"
    assert "safe-auth" in values["vault_pull_secret"]
