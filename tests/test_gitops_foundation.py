from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_required_gitops_structure_exists():
    required = [
        "gitops/bootstrap/argocd/kustomization.yaml",
        "gitops/bootstrap/projects/platform-project.yaml",
        "gitops/bootstrap/root-application/root-application.yaml",
        "gitops/operators/base/kustomization.yaml",
        "gitops/platform/base/kustomization.yaml",
        "gitops/day2/base/kustomization.yaml",
        "gitops/applications/platform-applicationset.yaml",
    ]
    for path in required:
        assert (ROOT / path).exists(), path


def test_environment_overlays_use_kustomize():
    for environment in ("lab", "development", "testing", "production"):
        path = ROOT / "gitops" / "overlays" / environment / "kustomization.yaml"
        data = yaml.safe_load(path.read_text())
        assert data["kind"] == "Kustomization"
        assert "../../operators/base" in data["resources"]


def test_argocd_resources_use_sync_waves():
    paths = [
        ROOT / "gitops/bootstrap/projects/platform-project.yaml",
        ROOT / "gitops/bootstrap/root-application/root-application.yaml",
        ROOT / "gitops/applications/platform-applicationset.yaml",
    ]
    for path in paths:
        data = yaml.safe_load(path.read_text())
        assert "argocd.argoproj.io/sync-wave" in data["metadata"]["annotations"]


def test_role_blocks_plaintext_secrets_and_implicit_git_writes():
    tasks = (ROOT / "roles/gitops_foundation/tasks/main.yml").read_text()
    assert "Plaintext secrets are not permitted" in tasks
    assert "gitops_git_write_workflow_confirmed" in tasks
    assert "git commit" not in tasks
    assert "git push" not in tasks
