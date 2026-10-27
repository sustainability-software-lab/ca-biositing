"""Unit tests for GCP WIF, IAM, and Secret Manager dashboard publisher bindings."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA_DIR = REPO_ROOT / "deployment" / "cloud" / "gcp" / "infrastructure"


class FakeOutput(str):
    """Lightweight string-compatible stand-in for pulumi.Output."""

    def apply(self, fn: Any) -> Any:
        res = fn(str(self))
        return FakeOutput(res) if isinstance(res, str) else res


class ResourceRecorder:
    """Records mocked Pulumi resource instantiations during unit tests."""

    def __init__(self) -> None:
        self.resources: list[dict[str, Any]] = []

    def record(self, kind: str, resource_name: str, **kwargs: Any) -> SimpleNamespace:
        entry = {"kind": kind, "resource_name": resource_name, **kwargs}
        obj = SimpleNamespace(**entry)
        entry["instance"] = obj
        self.resources.append(entry)
        return obj

    def find(self, kind: str, resource_name: str) -> dict[str, Any]:
        for item in self.resources:
            if item["kind"] == kind and item["resource_name"] == resource_name:
                return item
        raise KeyError(
            f"Resource ({kind}, {resource_name}) not found in {self.resources}"
        )

    def by_kind(self, kind: str) -> list[dict[str, Any]]:
        return [item for item in self.resources if item["kind"] == kind]


def _install_pulumi_mocks(
    monkeypatch: pytest.MonkeyPatch, deploy_env: str = "staging"
) -> ResourceRecorder:
    """Install in-memory Pulumi/GCP module mocks into sys.modules and reload infra modules."""
    monkeypatch.setenv("DEPLOY_ENV", deploy_env)
    if str(INFRA_DIR) not in sys.path:
        monkeypatch.syspath_prepend(str(INFRA_DIR))

    recorder = ResourceRecorder()

    pulumi_mod = ModuleType("pulumi")
    pulumi_mod.Resource = object  # type: ignore[attr-defined]
    pulumi_mod.ResourceOptions = lambda **kwargs: SimpleNamespace(**kwargs)  # type: ignore[attr-defined]

    class _OutputNamespace:
        @staticmethod
        def concat(*parts: Any) -> FakeOutput:
            return FakeOutput("".join(str(p) for p in parts))

        @staticmethod
        def all(*args: Any, **kwargs: Any) -> SimpleNamespace:
            if kwargs:
                return SimpleNamespace(
                    apply=lambda fn: FakeOutput(
                        fn({k: str(v) for k, v in kwargs.items()})
                    )
                )
            return SimpleNamespace(
                apply=lambda fn: FakeOutput(fn([str(a) for a in args]))
            )

    pulumi_mod.Output = _OutputNamespace  # type: ignore[attr-defined]

    auto_mod = ModuleType("pulumi.automation")
    auto_mod.Stack = object  # type: ignore[attr-defined]
    auto_mod.ConfigValue = lambda val: val  # type: ignore[attr-defined]
    pulumi_mod.automation = auto_mod  # type: ignore[attr-defined]

    gcp_mod = ModuleType("pulumi_gcp")
    gcp_mod.organizations = SimpleNamespace(  # type: ignore[attr-defined]
        get_project=lambda project_id: SimpleNamespace(
            project_id=project_id, number="123456789012"
        )
    )

    def _cls(kind: str, custom_builder: Any = None) -> type:
        def _new(cls: type, resource_name: str, **kwargs: Any) -> Any:
            if custom_builder is not None:
                return custom_builder(resource_name, **kwargs)
            return recorder.record(kind, resource_name, **kwargs)

        return type(kind, (), {"__new__": _new})

    def _make_pool(resource_name: str, **kwargs: Any) -> SimpleNamespace:
        pool_id = kwargs["workload_identity_pool_id"]
        return recorder.record(
            "WorkloadIdentityPool",
            resource_name,
            name=FakeOutput(
                f"projects/123456789012/locations/global/workloadIdentityPools/{pool_id}"
            ),
            **kwargs,
        )

    gcp_mod.iam = SimpleNamespace(  # type: ignore[attr-defined]
        WorkloadIdentityPool=_cls("WorkloadIdentityPool", _make_pool),
        WorkloadIdentityPoolProvider=_cls("WorkloadIdentityPoolProvider"),
        WorkloadIdentityPoolProviderOidcArgs=lambda **kwargs: SimpleNamespace(**kwargs),
    )

    def _make_sa(name: str, **kwargs: Any) -> SimpleNamespace:
        account_id = kwargs["account_id"]
        email = FakeOutput(f"{account_id}@biocirv-470318.iam.gserviceaccount.com")
        sa_res = recorder.record(
            "ServiceAccount",
            name,
            email=email,
            **kwargs,
        )
        sa_res.name = FakeOutput(
            f"projects/biocirv-470318/serviceAccounts/{email}"
        )
        return sa_res

    gcp_mod.serviceaccount = SimpleNamespace(  # type: ignore[attr-defined]
        Account=_cls("ServiceAccount", _make_sa),
        IAMBinding=_cls("ServiceAccountIAMBinding"),
    )

    gcp_mod.projects = SimpleNamespace(  # type: ignore[attr-defined]
        IAMMember=_cls("ProjectIAMMember")
    )

    gcp_mod.storage = SimpleNamespace(  # type: ignore[attr-defined]
        BucketIAMMember=_cls("BucketIAMMember")
    )

    gcp_mod.sql = SimpleNamespace(  # type: ignore[attr-defined]
        DatabaseInstance=object,
        Database=object,
        User=_cls("SqlUser"),
    )

    def _make_secret(resource_name: str, **kwargs: Any) -> SimpleNamespace:
        secret_id = kwargs["secret_id"]
        return recorder.record(
            "Secret",
            resource_name,
            id=FakeOutput(f"projects/biocirv-470318/secrets/{secret_id}"),
            name=FakeOutput(f"projects/biocirv-470318/secrets/{secret_id}"),
            **kwargs,
        )

    gcp_mod.secretmanager = SimpleNamespace(  # type: ignore[attr-defined]
        Secret=_cls("Secret", _make_secret),
        SecretVersion=_cls("SecretVersion"),
        SecretIamMember=_cls("SecretIamMember"),
        SecretReplicationArgs=lambda **kwargs: SimpleNamespace(**kwargs),
        SecretReplicationAutoArgs=lambda **kwargs: SimpleNamespace(**kwargs),
    )

    random_mod = ModuleType("pulumi_random")
    random_mod.RandomPassword = _cls(  # type: ignore[attr-defined]
        "RandomPassword",
        lambda name, **kwargs: recorder.record(
            "RandomPassword", name, result=FakeOutput(f"pw-{name}"), **kwargs
        ),
    )

    monkeypatch.setitem(sys.modules, "pulumi", pulumi_mod)
    monkeypatch.setitem(sys.modules, "pulumi.automation", auto_mod)
    monkeypatch.setitem(sys.modules, "pulumi_gcp", gcp_mod)
    monkeypatch.setitem(sys.modules, "pulumi_random", random_mod)

    for mod_name in ("config", "cloud_sql", "iam", "wif", "secret_manager"):
        monkeypatch.delitem(sys.modules, mod_name, raising=False)
        loaded_mod = importlib.import_module(mod_name)
        monkeypatch.setitem(sys.modules, mod_name, loaded_mod)

    return recorder


def test_dashboards_publisher_sa_grants_only_cloudsql_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify dashboards-publisher SA_DEFINITIONS grants roles/cloudsql.client and not project-wide secretAccessor."""
    recorder = _install_pulumi_mocks(monkeypatch, deploy_env="staging")
    iam = sys.modules["iam"]

    sa_Map = {
        logical_name: (account_id, display_name, roles)
        for logical_name, account_id, display_name, roles in iam.SA_DEFINITIONS
    }
    assert "dashboards-publisher" in sa_Map
    account_id, _, roles = sa_Map["dashboards-publisher"]
    assert account_id == "biocirv-staging-dash-pub"
    assert roles == ["roles/cloudsql.client"]
    assert "roles/secretmanager.secretAccessor" not in roles

    iam.create_service_accounts()
    binding = recorder.find(
        "ProjectIAMMember", "sa-dashboards-publisher-cloudsql.client"
    )
    assert binding["role"] == "roles/cloudsql.client"
    assert (
        str(binding["member"])
        == "serviceAccount:biocirv-staging-dash-pub@biocirv-470318.iam.gserviceaccount.com"
    )


def test_create_wif_scopes_dashboard_bindings_to_workflow_and_main_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify WIF OIDC provider maps workflow_ref/ref and scopes dashboard SAs to their workflow on main."""
    recorder = _install_pulumi_mocks(monkeypatch, deploy_env="staging")
    iam = sys.modules["iam"]
    wif = sys.modules["wif"]

    iam_res = iam.create_service_accounts()
    wif.create_wif(service_accounts=iam_res.service_accounts)

    provider = recorder.find("WorkloadIdentityPoolProvider", "github-oidc-provider")
    assert provider["attribute_mapping"] == {
        "google.subject": "assertion.sub",
        "attribute.repository": "assertion.repository",
        "attribute.workflow_ref": "assertion.workflow_ref",
    }

    pub_binding = recorder.find(
        "ServiceAccountIAMBinding", "dashboards-publisher-wif-binding"
    )
    assert pub_binding["role"] == "roles/iam.workloadIdentityUser"
    assert pub_binding["members"] == [
        "principalSet://iam.googleapis.com/projects/123456789012/"
        "locations/global/workloadIdentityPools/github-actions-staging/"
        "attribute.workflow_ref/sustainability-software-lab/ca-biositing/"
        ".github/workflows/dashboard-artifacts.yml@refs/heads/main"
    ]
    assert all("attribute.repository" not in m for m in pub_binding["members"])

    reader_binding = recorder.find(
        "ServiceAccountIAMBinding", "dashboards-reader-wif-binding"
    )
    assert reader_binding["role"] == "roles/iam.workloadIdentityUser"
    assert reader_binding["members"] == [
        "principalSet://iam.googleapis.com/projects/123456789012/"
        "locations/global/workloadIdentityPools/github-actions-staging/"
        "attribute.workflow_ref/sustainability-software-lab/ca-biositing/"
        ".github/workflows/gh-pages.yml@refs/heads/main"
    ]
    assert all("attribute.repository" not in m for m in reader_binding["members"])


def test_secret_manager_staging_grants_only_readonly_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify staging stack binds only biocirv-staging-dash-pub exclusively to biocirv-staging-ro-biocirv_readonly."""
    recorder = _install_pulumi_mocks(monkeypatch, deploy_env="staging")
    iam = sys.modules["iam"]
    secret_manager = sys.modules["secret_manager"]

    iam_res = iam.create_service_accounts()
    fake_sql = SimpleNamespace(instance=SimpleNamespace(name="biocirv-staging"))
    secrets = secret_manager.create_secrets(
        fake_sql, service_accounts=iam_res.service_accounts
    )

    iam_members = recorder.by_kind("SecretIamMember")
    assert len(iam_members) == 1

    pub_secret_iam = recorder.find(
        "SecretIamMember", "ro-biocirv-readonly-dashboards-publisher-accessor"
    )
    assert pub_secret_iam["role"] == "roles/secretmanager.secretAccessor"
    assert str(pub_secret_iam["secret_id"]) == "biocirv-staging-ro-biocirv_readonly"
    assert str(pub_secret_iam["secret_id"]) != str(secrets.db_password_secret.secret_id)
    assert (
        str(pub_secret_iam["member"])
        == "serviceAccount:biocirv-staging-dash-pub@biocirv-470318.iam.gserviceaccount.com"
    )
    assert iam_res.service_accounts["dashboards-publisher"] in pub_secret_iam["opts"].depends_on


def test_secret_manager_production_grants_prod_and_staging_publishers_on_readonly_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify production stack binds both prod and staging dashboards-publisher SAs to biocirv-production-ro-biocirv_readonly."""
    recorder = _install_pulumi_mocks(monkeypatch, deploy_env="production")
    iam = sys.modules["iam"]
    secret_manager = sys.modules["secret_manager"]

    iam_res = iam.create_service_accounts()
    fake_sql = SimpleNamespace(instance=SimpleNamespace(name="biocirv-production"))
    secrets = secret_manager.create_secrets(
        fake_sql, service_accounts=iam_res.service_accounts
    )

    iam_members = recorder.by_kind("SecretIamMember")
    assert len(iam_members) == 2

    prod_pub_iam = recorder.find(
        "SecretIamMember", "ro-biocirv-readonly-dashboards-publisher-accessor"
    )
    assert prod_pub_iam["role"] == "roles/secretmanager.secretAccessor"
    assert str(prod_pub_iam["secret_id"]) == "biocirv-production-ro-biocirv_readonly"
    assert str(prod_pub_iam["secret_id"]) != str(secrets.db_password_secret.secret_id)
    assert (
        str(prod_pub_iam["member"])
        == "serviceAccount:biocirv-prod-dash-pub@biocirv-470318.iam.gserviceaccount.com"
    )
    assert iam_res.service_accounts["dashboards-publisher"] in prod_pub_iam["opts"].depends_on

    staging_pub_iam = recorder.find(
        "SecretIamMember",
        "ro-biocirv-readonly-staging-dashboards-publisher-accessor",
    )
    assert staging_pub_iam["role"] == "roles/secretmanager.secretAccessor"
    assert str(staging_pub_iam["secret_id"]) == "biocirv-production-ro-biocirv_readonly"
    assert str(staging_pub_iam["secret_id"]) != str(secrets.db_password_secret.secret_id)
    assert (
        str(staging_pub_iam["member"])
        == "serviceAccount:biocirv-staging-dash-pub@biocirv-470318.iam.gserviceaccount.com"
    )


def test_deploy_pulumi_program_wires_service_accounts_into_create_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify deploy.pulumi_program() passes iam.service_accounts into create_secrets()."""
    recorder = _install_pulumi_mocks(monkeypatch, deploy_env="staging")
    pulumi_mod = sys.modules["pulumi"]
    pulumi_mod.export = lambda *args, **kwargs: None  # type: ignore[attr-defined]

    for stub_mod, attrs in {
        "apis": {
            "enable_apis": lambda: {
                k: f"api-{k}"
                for k in (
                    "iam",
                    "cloudresourcemanager",
                    "artifactregistry",
                    "sqladmin",
                    "secretmanager",
                    "storage",
                    "compute",
                    "run",
                )
            }
        },
        "artifact_registry": {
            "create_artifact_registry": lambda **kwargs: "ghcr-proxy",
            "create_quayio_registry": lambda **kwargs: "quayio-proxy",
        },
        "cloud_sql": {
            "create_cloud_sql": lambda **kwargs: SimpleNamespace(
                instance=SimpleNamespace(
                    name="biocirv-staging", connection_name="proj:reg:biocirv-staging"
                ),
                database=SimpleNamespace(name="biocirv-staging"),
                prefect_database=SimpleNamespace(name="prefect"),
            )
        },
        "storage": {
            "create_storage_resources": lambda **kwargs: SimpleNamespace(
                bucket=SimpleNamespace(name="img"),
                backup_bucket=SimpleNamespace(name="bak"),
                gasification_bucket=SimpleNamespace(name="gas"),
                dashboards_bucket=SimpleNamespace(name="dash"),
            )
        },
        "networking": {
            "create_cloud_nat": lambda **kwargs: SimpleNamespace(nat="nat")
        },
        "cloud_run": {
            "create_cloud_run_resources": lambda *args, **kwargs: SimpleNamespace(
                webservice=SimpleNamespace(uri="https://web"),
                prefect_server=SimpleNamespace(uri="https://prefect"),
                oauth2_proxy=SimpleNamespace(uri="https://auth"),
                migration_job=SimpleNamespace(name="mig"),
                seed_admin_job=SimpleNamespace(name="seed"),
            )
        },
    }.items():
        mod = ModuleType(stub_mod)
        for k, v in attrs.items():
            setattr(mod, k, v)
        monkeypatch.setitem(sys.modules, stub_mod, mod)

    monkeypatch.delitem(sys.modules, "deploy", raising=False)
    deploy_mod = importlib.import_module("deploy")
    deploy_mod.pulumi_program()

    pub_secret_iam = recorder.find(
        "SecretIamMember", "ro-biocirv-readonly-dashboards-publisher-accessor"
    )
    pub_sa = recorder.find("ServiceAccount", "sa-dashboards-publisher")
    assert pub_sa["instance"] in pub_secret_iam["opts"].depends_on
