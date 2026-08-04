from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_playbooks_exist():
    names = [
        'networking.yml', 'metallb.yml', 'sriov.yml', 'nmstate.yml', 'ptp.yml',
        'storageclasses.yml', 'volume-snapshots.yml', 'odf-day2.yml', 'ingress.yml',
        'node-configuration.yml', 'machineconfig.yml', 'chrony.yml'
    ]
    for name in names:
        assert (ROOT / 'playbooks' / 'day2' / name).exists()


def test_shared_role_supports_all_modes():
    text = (ROOT / 'roles' / 'day2_cluster_operations' / 'tasks' / 'main.yml').read_text()
    for mode in ('direct', 'render', 'gitops'):
        assert mode in text
    assert 'kubernetes.core.k8s' in text
