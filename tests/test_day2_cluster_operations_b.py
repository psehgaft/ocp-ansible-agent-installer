from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_playbooks_exist():
    names = [
        'monitoring.yml', 'alertmanager.yml', 'user-workload-monitoring.yml',
        'logging.yml', 'loki.yml', 'backup-oadp.yml', 'upgrade-prechecks.yml',
        'certificate-audit.yml', 'etcd-health.yml', 'acm-hub.yml',
        'acs-policies.yml', 'rhoso-day2.yml', 'virtualization-day2.yml',
        'health-checks.yml', 'reports.yml'
    ]
    for name in names:
        assert (ROOT / 'playbooks' / 'day2' / name).exists()


def test_operational_role_is_read_only_for_checks():
    text = (ROOT / 'roles' / 'day2_operational_workflow' / 'tasks' / 'main.yml').read_text()
    assert 'changed_when: false' in text
    assert 'failed_when: false' in text
    assert 'kubernetes.core.k8s' in text


def test_reports_are_json_and_markdown():
    text = (ROOT / 'roles' / 'consolidated_report' / 'tasks' / 'main.yml').read_text()
    assert '.json' in text
    assert '.md' in text
