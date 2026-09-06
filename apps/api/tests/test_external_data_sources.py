from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.external_sources import ExternalDataSourceRepository, ExternalDataSourceService
from qibao_api.routes.settings import router


class ProbeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return b'{"data":[]}'


def test_repository_exposes_builtin_sources_without_plaintext_key(tmp_path: Path):
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)

    items = repository.list_views()

    assert [item["source_id"] for item in items] == ["tickflow", "fuyao", "tushare"]
    assert all(item["configured"] is False for item in items)
    assert all("api_key" not in item for item in items)


def test_repository_saves_key_and_returns_only_hint(tmp_path: Path):
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)

    view = repository.save("tushare", api_key="secret-token-123", enabled=True)

    assert view["configured"] is True
    assert view["api_key_hint"] == "****-123"
    assert "secret-token-123" not in str(view)
    raw = (tmp_path / "external-data-sources.json").read_text(encoding="utf-8")
    assert "secret-token-123" in raw


def test_service_test_connection_reports_unavailable_without_raising(tmp_path: Path):
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)
    repository.save("tickflow", api_key="token", enabled=True)
    service = ExternalDataSourceService(repository)
    service._probe = lambda _source, _key: (False, "网络不可达")  # type: ignore[method-assign]

    result = service.test("tickflow")

    assert result["status"] == "unavailable"
    assert result["configured"] is True
    assert result["reason"] == "网络不可达"


def route_client(tmp_path: Path) -> TestClient:
    application = FastAPI()
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)
    application.state.external_data_source_repository = repository
    application.state.external_data_source_service = ExternalDataSourceService(repository)
    application.include_router(router)
    return TestClient(application)


def test_routes_expose_builtin_sources_and_never_echo_api_key(tmp_path: Path):
    subject = route_client(tmp_path)

    response = subject.get("/api/v1/settings/external-data-sources")
    assert response.status_code == 200
    assert [item["source_id"] for item in response.json()["sources"]] == ["tickflow", "fuyao", "tushare"]

    secret = "route-secret-123"
    saved = subject.put("/api/v1/settings/external-data-sources/tushare", json={"api_key": secret})
    assert saved.status_code == 200
    assert secret not in saved.text
    assert secret not in subject.get("/api/v1/settings/external-data-sources").text


def test_routes_validate_unknown_and_empty_keys(tmp_path: Path):
    subject = route_client(tmp_path)

    assert subject.put("/api/v1/settings/external-data-sources/tickflow", json={"api_key": " "}).status_code == 422
    assert subject.put("/api/v1/settings/external-data-sources/unknown", json={"api_key": "token"}).status_code == 404
    assert subject.post("/api/v1/settings/external-data-sources/unknown/test").status_code == 404


def test_route_test_reports_unconfigured_source(tmp_path: Path):
    subject = route_client(tmp_path)

    response = subject.post("/api/v1/settings/external-data-sources/fuyao/test")

    assert response.status_code == 200
    assert response.json()["status"] == "unconfigured"
    assert "API Key" in response.json()["reason"]


def test_route_test_status_is_retained_on_subsequent_reads(tmp_path: Path):
    subject = route_client(tmp_path)
    subject.put("/api/v1/settings/external-data-sources/tickflow", json={"api_key": "token"})
    subject.app.state.external_data_source_service._probe = lambda _source, _key: (False, "网络不可达")

    tested = subject.post("/api/v1/settings/external-data-sources/tickflow/test")
    reread = subject.get("/api/v1/settings/external-data-sources").json()["sources"][0]

    assert tested.json()["status"] == "unavailable"
    assert reread["status"] == "unavailable"
    assert reread["last_error"] == "网络不可达"


def test_repository_returns_key_only_for_enabled_configured_source(tmp_path: Path):
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)

    assert repository.enabled_key("tickflow") is None
    repository.save("tickflow", api_key="token", enabled=False)
    assert repository.enabled_key("tickflow") is None
    repository.save("tickflow", api_key="token", enabled=True)
    assert repository.enabled_key("tickflow") == "token"


def test_tickflow_probe_uses_documented_quote_endpoint_and_api_key_header(tmp_path: Path, monkeypatch):
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)
    service = ExternalDataSourceService(repository)
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["api_key"] = request.get_header("X-api-key")
        captured["timeout"] = timeout
        return ProbeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    definition = repository._definition("tickflow")

    ok, reason = service._probe(definition, "token")

    assert ok is True
    assert reason is None
    assert captured["url"].startswith("https://api.tickflow.org/v1/quotes?")
    assert "symbols=000001.SH" in captured["url"]
    assert captured["api_key"] == "token"


def test_tickflow_probe_normalizes_base_url_without_duplicate_version_path(tmp_path: Path, monkeypatch):
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)
    service = ExternalDataSourceService(repository)
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return ProbeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    definition = repository._definition("tickflow")
    root_definition = replace(definition, base_url="https://api.tickflow.org")

    ok, reason = service._probe(root_definition, "token")

    assert ok is True
    assert reason is None
    assert captured["url"].startswith("https://api.tickflow.org/v1/quotes?")


def test_tushare_permission_error_is_limited_not_unavailable(tmp_path: Path, monkeypatch):
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)
    repository.save("tushare", api_key="token", enabled=True)
    service = ExternalDataSourceService(repository)

    def denied_probe(_source, _key):
        return False, "permission denied: stock_basic"

    monkeypatch.setattr(service, "_probe", denied_probe)

    result = service.test("tushare")

    assert result["status"] == "limited"
    assert result["configured"] is True
    assert "permission denied" in result["reason"]


def test_repository_persists_independent_capability_checks(tmp_path: Path):
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)
    repository.save("tickflow", api_key="token", enabled=True)

    repository.update_test(
        "tickflow",
        status="limited",
        reason="部分能力没有权限",
        capability_checks=[
            {
                "key": "realtime_quotes",
                "label": "实时行情",
                "status": "ready",
                "detail": "接口响应正常",
                "reason_code": "ok",
                "tested_at": "2026-09-04T00:00:00+00:00",
            },
            {
                "key": "daily_klines",
                "label": "日线 K 线",
                "status": "limited",
                "detail": "当前 Key 没有此接口权限",
                "reason_code": "permission_denied",
                "tested_at": "2026-09-04T00:00:00+00:00",
            },
        ],
    )

    view = next(item for item in repository.list_views() if item["source_id"] == "tickflow")

    assert view["capability_checks"][0]["status"] == "ready"
    assert view["capability_checks"][1]["status"] == "limited"
    assert view["capability_checks"][1]["detail"] == "当前 Key 没有此接口权限"


def test_tickflow_test_probes_each_documented_capability(tmp_path: Path, monkeypatch):
    repository = ExternalDataSourceRepository(tmp_path / "external-data-sources.json", protector=None)
    repository.save("tickflow", api_key="token", enabled=True)
    service = ExternalDataSourceService(repository)
    captured_urls: list[str] = []

    def fake_urlopen(request, timeout):
        captured_urls.append(request.full_url)
        return ProbeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = service.test("tickflow")

    assert len(result["capability_checks"]) == 7
    assert all(item["status"] == "ready" for item in result["capability_checks"])
    assert any("/v1/klines?" in url and "period=1d" in url for url in captured_urls)
    assert any("/v1/depth?" in url for url in captured_urls)
