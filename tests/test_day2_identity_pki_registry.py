from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_day2_playbooks_exist():
    expected = {
        "certificates.yml", "cert-manager.yml", "oauth.yml", "ldap.yml",
        "ldap-group-sync.yml", "quay.yml", "external-registries.yml",
        "mirror-sets.yml", "registry-proxy.yml", "trusted-ca.yml",
    }
    found = {path.name for path in (ROOT / "playbooks" / "day2").glob("*.yml")}
    assert expected <= found


def test_ldap_sync_safeguards_are_declared():
    content = (ROOT / "roles" / "ldap_group_sync" / "tasks" / "main.yml").read_text()
    for token in [
        "ServiceAccount", "ClusterRole", "ClusterRoleBinding", "ConfigMap",
        "Secret", "CronJob", "concurrencyPolicy", "successfulJobsHistoryLimit",
        "failedJobsHistoryLimit", "ldap_sync_test_mode", "sync-report",
    ]:
        assert token in content


def test_rendered_registry_secrets_are_blocked():
    content = (ROOT / "roles" / "day2_registry" / "tasks" / "main.yml").read_text()
    assert "Reject plaintext secrets in rendered modes" in content
    assert "external_secrets" in (ROOT / "roles" / "day2_registry" / "defaults" / "main.yml").read_text()


def test_direct_mode_uses_kubernetes_core():
    for role in ["day2_pki", "day2_identity", "ldap_group_sync", "day2_registry"]:
        content = (ROOT / "roles" / role / "tasks" / "main.yml").read_text()
        assert "kubernetes.core.k8s" in content
