from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.routes.settings import router
from qibao_api.local_sources.discovery import LocalTerminalDiscovery
from qibao_api.local_sources.repository import LocalSourceSettingsRepository
from qibao_api.settings_repository import (
    AISettings,
    AISettingsRepository,
    EffectiveAISettingsResolver,
)


def client(tmp_path: Path, fallback: AISettings | None = None) -> TestClient:
    application = FastAPI()
    repository = AISettingsRepository(tmp_path)
    application.state.ai_settings_repository = repository
    application.state.effective_ai_settings = EffectiveAISettingsResolver(
        repository, fallback=fallback
    )
    application.state.local_source_settings_repository = (
        LocalSourceSettingsRepository(tmp_path / "config" / "data-sources.json")
    )
    application.state.local_terminal_discovery = LocalTerminalDiscovery(
        system_candidates=lambda: ()
    )
    application.include_router(router)
    return TestClient(application)


def environment_settings() -> AISettings:
    return AISettings(
        base_url="http://localhost:11434/v1",
        model="environment-model",
        api_key="environment-secret",
    )


def test_ai_settings_never_return_secret(tmp_path: Path) -> None:
    subject = client(tmp_path)
    payload = {
        "base_url": "https://api.example/v1",
        "model": "model-a",
        "api_key": "secret-value",
    }

    response = subject.put("/api/v1/settings/ai", json=payload)
    body = subject.get("/api/v1/settings/ai").json()

    assert response.status_code == 200
    assert body["configured"] is True
    assert body["api_key_hint"].endswith("alue")
    assert "secret-value" not in str(response.json())
    assert "secret-value" not in str(body)


def test_unconfigured_and_deleted_settings_have_no_hint(tmp_path: Path) -> None:
    subject = client(tmp_path)
    assert subject.get("/api/v1/settings/ai").json() == {
        "configured": False,
        "base_url": None,
        "model": None,
        "api_key_hint": None,
    }
    subject.put(
        "/api/v1/settings/ai",
        json={"base_url": "https://api.example/v1", "model": "m", "api_key": "secret"},
    )

    response = subject.delete("/api/v1/settings/ai")

    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_short_api_key_is_not_returned_in_full(tmp_path: Path) -> None:
    subject = client(tmp_path)
    subject.put(
        "/api/v1/settings/ai",
        json={"base_url": "https://api.example/v1", "model": "m", "api_key": "abc"},
    )

    response = subject.get("/api/v1/settings/ai")

    assert "abc" not in response.text


def test_get_reports_environment_fallback_when_local_is_missing(tmp_path: Path) -> None:
    response = client(tmp_path, environment_settings()).get("/api/v1/settings/ai")

    assert response.json() == {
        "configured": True,
        "base_url": "http://localhost:11434/v1",
        "model": "environment-model",
        "api_key_hint": "****cret",
    }


def test_delete_local_override_reveals_environment_fallback(tmp_path: Path) -> None:
    subject = client(tmp_path, environment_settings())
    subject.put(
        "/api/v1/settings/ai",
        json={"base_url": "https://api.example/v1", "model": "local", "api_key": "local-secret"},
    )

    response = subject.delete("/api/v1/settings/ai")

    assert response.json()["model"] == "environment-model"
    assert response.json()["configured"] is True


def test_corrupt_local_file_blocks_environment_fallback(tmp_path: Path) -> None:
    (tmp_path / "ai-settings.json").write_text("{broken", encoding="utf-8")

    response = client(tmp_path, environment_settings()).get("/api/v1/settings/ai")

    assert response.json()["configured"] is False


def test_put_rejects_unsafe_url_without_returning_secret(tmp_path: Path) -> None:
    secret = "do-not-return"

    response = client(tmp_path).put(
        "/api/v1/settings/ai",
        json={
            "base_url": f"https://user:{secret}@api.example/v1",
            "model": "m",
            "api_key": secret,
        },
    )

    assert response.status_code == 422
    assert secret not in response.text


def test_put_never_echoes_secret_from_malformed_payload(tmp_path: Path) -> None:
    secret = "malformed-secret"

    response = client(tmp_path).put(
        "/api/v1/settings/ai",
        json={
            "base_url": "https://api.example/v1",
            "model": [secret],
            "api_key": secret,
            "unexpected": secret,
        },
    )

    assert response.status_code == 422
    assert secret not in response.text


def _create_tdx(root: Path) -> Path:
    for exchange in ("sh", "sz"):
        folder = root / "vipdoc" / exchange / "lday"
        folder.mkdir(parents=True)
        (folder / f"{exchange}600000.day").write_bytes(b"daily")
    (root / "TdxW.exe").write_bytes(b"exe")
    return root


def test_data_source_settings_default_to_discovery_without_rpc(tmp_path: Path) -> None:
    response = client(tmp_path).get("/api/v1/settings/data-sources")

    assert response.status_code == 200
    body = response.json()
    assert body["settings_state"] == "default"
    assert body["settings"]["auto_discovery"] is True
    assert body["settings"]["tdx_rpc_enabled"] is False
    assert body["active_tdx_vipdoc"] is None
    assert body["restart_required"] is False
    assert body["tdx_rpc"]["status"] == "disabled"
    assert body["tdx_rpc"]["capabilities"]


def test_detect_validates_draft_without_persisting_it(tmp_path: Path) -> None:
    root = _create_tdx(tmp_path / "tdx")
    subject = client(tmp_path)

    response = subject.post("/api/v1/settings/data-sources/detect", json={
        "auto_discovery": False,
        "tdx_install_paths": [str(root)],
        "ths_install_paths": [],
        "tdx_rpc_enabled": False,
        "tdx_rpc_url": None,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["active_tdx_vipdoc"] == str(root / "vipdoc")
    assert body["terminals"][0]["status"] == "ready"
    assert body["terminals"][0]["sh_daily_count"] == 1
    assert subject.get("/api/v1/settings/data-sources").json()["settings_state"] == "default"


def test_put_saves_valid_paths_and_requires_restart(tmp_path: Path) -> None:
    root = _create_tdx(tmp_path / "tdx")
    subject = client(tmp_path)
    payload = {
        "auto_discovery": False,
        "tdx_install_paths": [str(root)],
        "ths_install_paths": [],
        "tdx_rpc_enabled": False,
        "tdx_rpc_url": None,
    }

    response = subject.put("/api/v1/settings/data-sources", json=payload)

    assert response.status_code == 200
    assert response.json()["restart_required"] is True
    saved = subject.get("/api/v1/settings/data-sources").json()
    assert saved["settings_state"] == "ready"
    assert saved["settings"]["tdx_install_paths"] == [str(root)]


def test_put_rejects_invalid_manual_tdx_directory(tmp_path: Path) -> None:
    invalid = tmp_path / "empty"
    invalid.mkdir()

    response = client(tmp_path).put("/api/v1/settings/data-sources", json={
        "auto_discovery": False,
        "tdx_install_paths": [str(invalid)],
        "ths_install_paths": [],
        "tdx_rpc_enabled": False,
        "tdx_rpc_url": None,
    })

    assert response.status_code == 422
    assert "通达信目录无效" in response.json()["detail"]


def test_put_rejects_non_loopback_rpc_address(tmp_path: Path) -> None:
    response = client(tmp_path).put("/api/v1/settings/data-sources", json={
        "auto_discovery": True,
        "tdx_install_paths": [],
        "ths_install_paths": [],
        "tdx_rpc_enabled": True,
        "tdx_rpc_url": "http://192.168.1.5:17709/",
    })

    assert response.status_code == 422


def test_enabled_tdx_rpc_reports_partial_capabilities_without_echoing_errors(
    tmp_path: Path, monkeypatch
) -> None:
    secret = "private-token-should-not-leak"

    class FakeRpc:
        def __init__(self, endpoint: str) -> None:
            self.endpoint = endpoint

        def available(self) -> bool:
            return True

        def call(self, method: str, params: dict) -> object:
            if method == "get_stock_list":
                return {"ErrorId": "0", "Value": [{"Code": "600000.SH", "Name": "浦发银行"}]}
            if method == "get_market_snapshot":
                return {"ErrorId": "0", "Now": "9.28"}
            if method == "get_sector_list":
                return {"ErrorId": "0", "Value": [{"Code": "BK0001", "Name": "测试板块"}]}
            raise OSError(secret)

        def close(self) -> None:
            return None

    monkeypatch.setattr("qibao_api.routes.settings.TdxJsonRpcClient", FakeRpc)
    response = client(tmp_path).put("/api/v1/settings/data-sources", json={
        "auto_discovery": True,
        "tdx_install_paths": [],
        "ths_install_paths": [],
        "tdx_rpc_enabled": True,
        "tdx_rpc_url": "http://127.0.0.1:17709/",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["tdx_rpc"]["status"] == "partial"
    assert secret not in response.text
    assert all(secret not in item["detail"] for item in body["tdx_rpc"]["capabilities"])


def test_enabled_tdx_rpc_reports_unavailable_when_bridge_cannot_connect(
    tmp_path: Path, monkeypatch
) -> None:
    class FakeRpc:
        def __init__(self, endpoint: str) -> None:
            self.endpoint = endpoint

        def available(self) -> bool:
            return False

        def call(self, method: str, params: dict) -> object:
            raise AssertionError("unreachable bridge must not be probed")

        def close(self) -> None:
            return None

    monkeypatch.setattr("qibao_api.routes.settings.TdxJsonRpcClient", FakeRpc)
    response = client(tmp_path).put("/api/v1/settings/data-sources", json={
        "auto_discovery": True,
        "tdx_install_paths": [],
        "ths_install_paths": [],
        "tdx_rpc_enabled": True,
        "tdx_rpc_url": "http://127.0.0.1:17709/",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["tdx_rpc"]["status"] == "unavailable"
    assert body["tdx_rpc"]["reachable"] is False
    assert body["tdx_rpc"]["client"]["status"] == "not_running"
    assert "未检测到通达信客户端进程" in body["tdx_rpc"]["client"]["detail"]


def test_tdx_rpc_reports_client_process_separately_from_bridge(
    tmp_path: Path, monkeypatch
) -> None:
    executable = Path(r"D:\new_tdx64\TdxW.exe")
    monkeypatch.setattr(
        "qibao_api.routes.settings.running_tdx_process_paths",
        lambda: (executable,),
    )

    response = client(tmp_path).put("/api/v1/settings/data-sources", json={
        "auto_discovery": True,
        "tdx_install_paths": [],
        "ths_install_paths": [],
        "tdx_rpc_enabled": True,
        "tdx_rpc_url": "http://127.0.0.1:17709/",
    })

    assert response.status_code == 200
    body = response.json()["tdx_rpc"]
    assert body["client"] == {
        "status": "running",
        "executable_path": str(executable),
        "detail": "检测到通达信客户端进程；这不代表 17709 JSON-RPC 桥已经监听",
    }
    assert body["reachable"] is False


def test_tdx_rpc_client_detail_uses_configured_bridge_port(
    tmp_path: Path, monkeypatch
) -> None:
    executable = Path(r"D:\new_tdx64\TdxW.exe")
    monkeypatch.setattr(
        "qibao_api.routes.settings.running_tdx_process_paths",
        lambda: (executable,),
    )

    response = client(tmp_path).put("/api/v1/settings/data-sources", json={
        "auto_discovery": True,
        "tdx_install_paths": [],
        "ths_install_paths": [],
        "tdx_rpc_enabled": True,
        "tdx_rpc_url": "http://127.0.0.1:19001/",
    })

    assert response.status_code == 200
    body = response.json()["tdx_rpc"]
    assert body["client"]["detail"] == "检测到通达信客户端进程；这不代表 19001 JSON-RPC 桥已经监听"
