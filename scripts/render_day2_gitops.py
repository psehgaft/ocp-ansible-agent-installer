#!/usr/bin/env python3
"""Render a deterministic, secret-free OpenShift Day-2 GitOps repository."""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def safe_name(value: str) -> str:
    result = re.sub(r"[^a-z0-9.-]+", "-", value.lower()).strip("-.")
    if not result or len(result) > 63:
        raise ValueError(f"{value!r} is not a valid Kubernetes-compatible name")
    return result


def recursive_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = recursive_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def dependency_order(selected: list[str], catalog: dict[str, dict[str, Any]]) -> list[str]:
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name not in catalog:
            raise ValueError(f"Unknown operator {name!r}")
        if name in visiting:
            raise ValueError(f"Dependency cycle detected at {name!r}")
        if name in visited:
            return
        visiting.add(name)
        for dependency in catalog[name].get("dependencies", []):
            visit(dependency)
        visiting.remove(name)
        visited.add(name)
        ordered.append(name)

    for component in selected:
        visit(component)
    return ordered


def dump_yaml(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + yaml.safe_dump(document, sort_keys=False, width=1000),
        encoding="utf-8",
    )


def kustomization(resources: list[str]) -> dict[str, Any]:
    return {
        "apiVersion": "kustomize.config.k8s.io/v1beta1",
        "kind": "Kustomization",
        "resources": resources,
    }


def subscription_documents(name: str, operator: dict[str, Any], approval: str) -> list[tuple[str, dict[str, Any]]]:
    namespace = operator["namespace"]
    documents: list[tuple[str, dict[str, Any]]] = []
    shared_namespaces = {"openshift-operators", "openshift-operators-redhat"}
    if operator.get("create_namespace", namespace not in shared_namespaces):
        documents.append(("namespace.yaml", {
            "apiVersion": "v1", "kind": "Namespace", "metadata": {"name": namespace},
        }))
    create_group = operator.get("create_operator_group", namespace not in {"openshift-operators", "openshift-operators-redhat"})
    if create_group:
        documents.append(("operatorgroup.yaml", {
            "apiVersion": "operators.coreos.com/v1", "kind": "OperatorGroup",
            "metadata": {"name": safe_name(name), "namespace": namespace},
            "spec": {"targetNamespaces": [namespace]},
        }))
    spec: dict[str, Any] = {
        "name": operator["package"],
        "source": operator.get("source", "redhat-operators"),
        "sourceNamespace": operator.get("source_namespace", "openshift-marketplace"),
        "installPlanApproval": operator.get("install_plan_approval", approval),
    }
    if operator.get("channel"):
        spec["channel"] = operator["channel"]
    if operator.get("starting_csv"):
        spec["startingCSV"] = operator["starting_csv"]
    documents.append(("subscription.yaml", {
        "apiVersion": "operators.coreos.com/v1alpha1", "kind": "Subscription",
        "metadata": {"name": operator["package"], "namespace": namespace}, "spec": spec,
    }))
    return documents


def application(name: str, project: str, repo_url: str, revision: str, path: str, namespace: str, wave: int) -> dict[str, Any]:
    return {
        "apiVersion": "argoproj.io/v1alpha1", "kind": "Application",
        "metadata": {
            "name": safe_name(name), "namespace": "openshift-gitops",
            "annotations": {"argocd.argoproj.io/sync-wave": str(wave)},
        },
        "spec": {
            "project": project,
            "source": {"repoURL": repo_url, "targetRevision": revision, "path": path},
            "destination": {"server": "https://kubernetes.default.svc", "namespace": namespace},
            "syncPolicy": {
                "automated": {"prune": True, "selfHeal": True},
                "syncOptions": ["CreateNamespace=true", "ServerSideApply=true", "SkipDryRunOnMissingResource=true"],
                "retry": {"limit": 10, "backoff": {"duration": "10s", "factor": 2, "maxDuration": "10m"}},
            },
        },
    }


def assert_no_secret(document: dict[str, Any], location: str) -> None:
    if document.get("kind") == "Secret":
        raise ValueError(f"Plain Kubernetes Secret is forbidden in GitOps output: {location}")
    forbidden = {
        "password", "token", "bearertoken", "privatekey", "clientsecret",
        "accesskey", "accesskeyid", "secretaccesskey",
    }
    reference_keys = {"name", "key", "secretname", "optional"}

    def inspect(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
                is_reference = isinstance(child, dict) and {
                    re.sub(r"[^a-z0-9]", "", str(item).lower()) for item in child
                } <= reference_keys
                if normalized in forbidden and child not in (None, "") and not is_reference:
                    raise ValueError(
                        f"Possible inline secret field {path}.{key} in {location}; "
                        "use an approved secret reference"
                    )
                inspect(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                inspect(child, f"{path}[{index}]")

    inspect(document, "resource")


def render(catalog_path: Path, config_path: Path, output_root: Path) -> dict[str, Any]:
    source = load_yaml(catalog_path)
    config = load_yaml(config_path)
    catalog = copy.deepcopy(source.get("operators", {}))
    for name, value in config.get("additional_operators", {}).items():
        if name in catalog:
            raise ValueError(f"Additional operator {name!r} conflicts with the curated catalog")
        catalog[name] = value
    for name, override in config.get("operator_overrides", {}).items():
        if name not in catalog:
            raise ValueError(f"Override references unknown operator {name!r}")
        catalog[name] = recursive_merge(catalog[name], override)

    profile_name = config.get("profile", "custom")
    if profile_name != "custom" and profile_name not in source.get("profiles", {}):
        raise ValueError(f"Unknown operator profile {profile_name!r}")
    profile_operators = source.get("profiles", {}).get(profile_name, [])
    requested = list(dict.fromkeys(profile_operators + config.get("enabled_operators", [])))
    selected = dependency_order(requested, catalog)
    openshift_minor = str(config.get("openshift_minor_version", "4.18"))
    if not re.fullmatch(r"4\.\d+", openshift_minor):
        raise ValueError("openshift_minor_version must look like 4.18")
    for operator in catalog.values():
        if config.get("adapt_versioned_channels", True) and operator.get("channel"):
            operator["channel"] = operator["channel"].replace("4.18", openshift_minor)
    cluster = safe_name(config["cluster_name"])
    project = safe_name(config.get("project", f"platform-{cluster}"))
    repo_url = config["repository_url"]
    revision = config.get("target_revision", "main")
    prefix = config.get("repository_path", "clusters").strip("/")
    cluster_relative = f"{prefix}/{cluster}"
    cluster_root = output_root / cluster_relative
    ownership_marker = cluster_root / ".day2-gitops-renderer-owned"
    managed_directories = [cluster_root / item for item in ("applications", "operators", "operands")]
    if any(path.exists() for path in managed_directories) and not ownership_marker.exists():
        raise ValueError(
            f"Refusing to replace unmanaged content below {cluster_root}; "
            "move it or add the renderer ownership marker explicitly"
        )
    for managed_directory in managed_directories:
        if managed_directory.exists():
            shutil.rmtree(managed_directory)
    cluster_root.mkdir(parents=True, exist_ok=True)
    ownership_marker.write_text("Managed by scripts/render_day2_gitops.py\n", encoding="utf-8")
    applications_root = cluster_root / "applications"
    app_resources: list[str] = []
    approval = config.get("install_plan_approval", "Automatic")

    initialized_namespaces: set[str] = set()
    for index, name in enumerate(selected):
        operator = copy.deepcopy(catalog[name])
        required = {"display_name", "package", "source", "namespace"}
        missing = sorted(required - set(operator))
        if missing:
            raise ValueError(f"Operator {name!r} is missing fields: {', '.join(missing)}")
        if operator["namespace"] in initialized_namespaces:
            operator["create_namespace"] = False
            operator["create_operator_group"] = False
        initialized_namespaces.add(operator["namespace"])
        operator_root = cluster_root / "operators" / safe_name(name)
        resources: list[str] = []
        for filename, document in subscription_documents(name, operator, approval):
            dump_yaml(operator_root / filename, document)
            resources.append(filename)
        dump_yaml(operator_root / "kustomization.yaml", kustomization(resources))
        app_name = f"{cluster}-operator-{name}"
        app_file = f"operator-{safe_name(name)}.yaml"
        dump_yaml(applications_root / app_file, application(
            app_name, project, repo_url, revision,
            f"{cluster_relative}/operators/{safe_name(name)}", operator["namespace"], 10 + index,
        ))
        app_resources.append(app_file)

    operand_definitions = config.get("operands", {})
    for index, (name, manifests) in enumerate(operand_definitions.items()):
        if name not in selected and name not in source.get("platform_features", {}):
            raise ValueError(f"Operands reference unselected or unknown component {name!r}")
        if not isinstance(manifests, list) or not manifests:
            raise ValueError(f"Operands for {name!r} must be a non-empty list")
        operand_root = cluster_root / "operands" / safe_name(name)
        resources = []
        destination = "default"
        for item_index, document in enumerate(manifests, start=1):
            if not isinstance(document, dict) or not document.get("apiVersion") or not document.get("kind"):
                raise ValueError(f"Operand {name}[{item_index}] is not a Kubernetes resource")
            assert_no_secret(document, f"{name}[{item_index}]")
            destination = document.get("metadata", {}).get("namespace", destination)
            filename = f"resource-{item_index:03d}.yaml"
            dump_yaml(operand_root / filename, document)
            resources.append(filename)
        dump_yaml(operand_root / "kustomization.yaml", kustomization(resources))
        app_file = f"operand-{safe_name(name)}.yaml"
        dump_yaml(applications_root / app_file, application(
            f"{cluster}-operand-{name}", project, repo_url, revision,
            f"{cluster_relative}/operands/{safe_name(name)}", destination, 100 + index,
        ))
        app_resources.append(app_file)

    dump_yaml(applications_root / "kustomization.yaml", kustomization(app_resources))
    dump_yaml(cluster_root / "kustomization.yaml", kustomization(["applications"]))

    project_document = {
        "apiVersion": "argoproj.io/v1alpha1", "kind": "AppProject",
        "metadata": {"name": project, "namespace": "openshift-gitops"},
        "spec": {
            "description": f"GitOps-managed Day-2 resources for {cluster}",
            "sourceRepos": [repo_url],
            "destinations": [{"namespace": "*", "server": "https://kubernetes.default.svc"}],
            "clusterResourceWhitelist": [{"group": "*", "kind": "*"}],
            "namespaceResourceWhitelist": [{"group": "*", "kind": "*"}],
        },
    }
    root_document = application(
        f"{cluster}-platform-root", project, repo_url, revision,
        f"{cluster_relative}/applications", "openshift-gitops", 0,
    )
    bootstrap_root = output_root / "bootstrap" / cluster
    dump_yaml(bootstrap_root / "project.yaml", project_document)
    dump_yaml(bootstrap_root / "root-application.yaml", root_document)
    dump_yaml(bootstrap_root / "kustomization.yaml", kustomization(["project.yaml", "root-application.yaml"]))

    catalog_sources = copy.deepcopy(source.get("catalog_sources", {}))
    for source_name, source_config in catalog_sources.items():
        source_config["image"] = source_config["image"].replace("v4.18", f"v{openshift_minor}")
    for source_name, image in config.get("catalog_source_images", {}).items():
        if source_name not in catalog_sources:
            catalog_sources[source_name] = {"source_namespace": "openshift-marketplace"}
        catalog_sources[source_name]["image"] = image
    mirror_groups: dict[str, list[dict[str, Any]]] = {}
    for name in selected:
        operator = catalog[name]
        source_name = operator.get("source", "redhat-operators")
        if source_name not in catalog_sources:
            continue
        package: dict[str, Any] = {"name": operator["package"]}
        if operator.get("channel"):
            package["channels"] = [{"name": operator["channel"]}]
        mirror_groups.setdefault(source_name, []).append(package)
    mirror_document = {
        "apiVersion": "mirror.openshift.io/v2alpha1", "kind": "ImageSetConfiguration",
        "mirror": {"operators": [
            {"catalog": catalog_sources[source_name]["image"], "packages": packages}
            for source_name, packages in mirror_groups.items()
        ]},
    }
    dump_yaml(output_root / "mirror" / f"{cluster}-operators-imageset-config.yaml", mirror_document)

    summary = {
        "cluster": cluster,
        "project": project,
        "profile": profile_name,
        "openshift_minor_version": openshift_minor,
        "selected_operators": selected,
        "selected_packages": [
            {
                "component": name,
                "package": catalog[name]["package"],
                "channel": catalog[name].get("channel", ""),
                "source": catalog[name].get("source", "redhat-operators"),
                "source_namespace": catalog[name].get("source_namespace", "openshift-marketplace"),
            }
            for name in selected
        ],
        "operator_count": len(selected),
        "operand_groups": list(operand_definitions),
        "repository_path": cluster_relative,
    }
    (output_root / "render-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    print(json.dumps(render(args.catalog, args.config, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
