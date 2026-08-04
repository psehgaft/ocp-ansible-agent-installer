from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_every_day2_playbook_is_cataloged_for_ansible_and_gitops() -> None:
    catalog = yaml.safe_load(
        (ROOT / "framework/day2-exercises.yml").read_text(encoding="utf-8")
    )
    exercises = catalog["exercises"]
    discovered = {
        str(path.relative_to(ROOT))
        for path in (ROOT / "playbooks/day2").glob("*.yml")
    }
    declared = {item["playbook"] for item in exercises.values()}
    assert discovered == declared

    for exercise in exercises.values():
        role = exercise["role"]
        role_tasks = ROOT / f"roles/{role}/tasks/main.yml"
        assert role_tasks.is_file(), role
        assert exercise["resources_variable"]
        assert exercise["gitops_output"].startswith("rendered/day2/")
        assert (ROOT / exercise["playbook"]).is_file()
        content = role_tasks.read_text(encoding="utf-8")
        assert "day2_deployment_mode" in content
        assert "direct" in content
        assert "gitops" in content


def test_shared_day2_roles_support_ansible_and_gitops_execution() -> None:
    for role in ("day2_cluster_operations", "day2_operational_workflow"):
        content = (ROOT / f"roles/{role}/tasks/main.yml").read_text(encoding="utf-8")
        assert "day2_deployment_mode" in content
        assert "direct" in content
        assert "gitops" in content
        assert "kubernetes.core.k8s" in content
        assert "to_nice_yaml" in content


def test_bastion_bootstrap_is_complete_and_documented() -> None:
    required = (
        "playbooks/configure-bastion.yml",
        "roles/bastion_workstation/tasks/main.yml",
        "roles/bastion_workstation/defaults/main.yml",
        "roles/bastion_workstation/README.md",
    )
    for path in required:
        assert (ROOT / path).is_file()

    text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in required).lower()
    for tool in (
        "ansible-core",
        "jinja2",
        "python3",
        "oc",
        "kubectl",
        "kubelet",
        "kustomize",
        "helm",
        "podman",
        "skopeo",
        "buildah",
    ):
        assert tool in text


def test_validators_ignore_generated_dependencies() -> None:
    paths = (
        "scripts/validate_yaml.py",
        "scripts/offline_validate.py",
        ".yamllint",
    )
    for path in paths:
        content = (ROOT / path).read_text(encoding="utf-8")
        assert ".collections" in content
