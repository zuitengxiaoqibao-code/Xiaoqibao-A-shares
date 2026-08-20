from pathlib import Path
import logging
from types import SimpleNamespace

from qibao_desktop import entrypoint
from qibao_desktop.instance import AlreadyRunningError


class FakeServer:
    instances = []

    def __init__(self, **_kwargs) -> None:
        self.url = "http://127.0.0.1:43210"
        self.started = False
        self.stopped = False
        self.waited = False
        self.launched = False
        self.instances.append(self)

    def start(self) -> None:
        self.started = True

    def launch(self) -> None:
        self.launched = True

    def wait_until_ready(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def wait(self) -> None:
        self.waited = True


class FakeInstance:
    def __init__(self, _name: str) -> None:
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.closed = True


class AlreadyRunningInstance:
    def __init__(self, _name: str) -> None:
        pass

    def __enter__(self):
        raise AlreadyRunningError("already running")

    def __exit__(self, *_args) -> None:
        pass


def test_entrypoint_sets_portable_paths_and_stops_after_window(
    tmp_path: Path, monkeypatch
) -> None:
    seen = {}
    monkeypatch.setattr(entrypoint, "_create_local_api_server", lambda _port: FakeServer())
    monkeypatch.setattr(entrypoint, "SingleInstance", FakeInstance)
    monkeypatch.setattr(entrypoint, "configure_desktop_logging", lambda _path: None)
    existing_count = len(FakeServer.instances)
    def run_window(start_application, **kwargs):
        seen["server_created_before_window"] = len(FakeServer.instances) > existing_count
        seen["startup_progress_reader"] = kwargs.get("startup_progress")
        seen["url"] = start_application()

    monkeypatch.setattr(entrypoint, "run_window", run_window)

    previous_data = tmp_path / "data" / "legacy"
    previous_data.mkdir(parents=True)
    (previous_data / "market.sqlite3").write_text("previous", encoding="utf-8")

    result = entrypoint.main(["--portable-root", str(tmp_path)])

    server = FakeServer.instances[-1]
    assert result == 0
    assert server.started and server.stopped
    assert seen["server_created_before_window"] is True
    assert callable(seen["startup_progress_reader"])
    assert server.launched
    assert seen["url"] == server.url
    assert (tmp_path / "config").is_dir()
    assert entrypoint.os.environ["QIBAO_DATA_DIR"] == str(tmp_path / "data")
    assert entrypoint.os.environ["QIBAO_WEB_DIR"] == str(tmp_path / "web")
    assert (tmp_path / "data" / "market.sqlite3").read_text(encoding="utf-8") == "previous"
    assert not previous_data.exists()


def test_entrypoint_applies_current_data_migrations_before_api_start(tmp_path: Path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(entrypoint, "apply_migrations", lambda root, target_version: calls.append((root, target_version)) or target_version)
    monkeypatch.setattr(entrypoint, "_create_local_api_server", lambda _port: FakeServer())
    monkeypatch.setattr(entrypoint, "SingleInstance", FakeInstance)
    monkeypatch.setattr(entrypoint, "configure_desktop_logging", lambda _path: None)
    monkeypatch.setattr(entrypoint, "run_window", lambda start, **_kwargs: start())

    assert entrypoint.main(["--portable-root", str(tmp_path)]) == 0
    assert calls == [(tmp_path, entrypoint.CURRENT_MIGRATION_VERSION)]


def test_gui_prepares_runtime_and_launches_api_before_window(
    tmp_path: Path, monkeypatch
) -> None:
    order: list[str] = []

    class TrackedLayout:
        root = tmp_path
        data_dir = tmp_path / "data"
        web_dir = tmp_path / "web"
        logs_dir = tmp_path / "logs"

        def ensure(self) -> None:
            order.append("layout-ready")

    monkeypatch.setattr(entrypoint, "desktop_layout", lambda _root: TrackedLayout())
    monkeypatch.setattr(entrypoint, "SingleInstance", FakeInstance)
    monkeypatch.setattr(
        entrypoint,
        "configure_desktop_logging",
        lambda _path: order.append("logging-ready"),
    )
    monkeypatch.setattr(entrypoint, "promote_previous_data_layout", lambda _layout: None)
    monkeypatch.setattr(entrypoint, "_create_local_api_server", lambda _port: FakeServer())

    def run_window(start_application, **_kwargs):
        order.append("window-started")
        start_application()

    monkeypatch.setattr(entrypoint, "run_window", run_window)

    assert entrypoint.main(["--portable-root", str(tmp_path)]) == 0
    assert order[:3] == ["layout-ready", "logging-ready", "window-started"]
    assert FakeServer.instances[-1].launched


def test_entrypoint_preserves_current_data_and_archives_previous_conflicts(
    tmp_path: Path, monkeypatch
) -> None:
    current_data = tmp_path / "data"
    previous_data = current_data / "legacy"
    previous_data.mkdir(parents=True)
    (current_data / "market.sqlite3").write_text("current", encoding="utf-8")
    (previous_data / "market.sqlite3").write_text("previous", encoding="utf-8")
    monkeypatch.setattr(entrypoint, "_create_local_api_server", lambda _port: FakeServer())
    monkeypatch.setattr(entrypoint, "SingleInstance", FakeInstance)
    monkeypatch.setattr(entrypoint, "configure_desktop_logging", lambda _path: None)
    monkeypatch.setattr(entrypoint, "run_window", lambda start, **_kwargs: start())

    assert entrypoint.main(["--portable-root", str(tmp_path)]) == 0

    assert (current_data / "market.sqlite3").read_text(encoding="utf-8") == "current"
    archived = list((tmp_path / "backups").glob("previous-data-*/*"))
    assert len(archived) == 1
    assert archived[0].read_text(encoding="utf-8") == "previous"
    assert not previous_data.exists()


def test_server_is_stopped_when_window_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(entrypoint, "_create_local_api_server", lambda _port: FakeServer())
    monkeypatch.setattr(entrypoint, "SingleInstance", FakeInstance)
    monkeypatch.setattr(entrypoint, "configure_desktop_logging", lambda _path: None)
    monkeypatch.setattr(
        entrypoint,
        "run_window",
        lambda _start, **_kwargs: (_ for _ in ()).throw(RuntimeError("window failed")),
    )

    assert entrypoint.main(["--portable-root", str(tmp_path)]) == 1
    assert FakeServer.instances[-1].stopped


def test_headless_mode_waits_without_opening_window(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(entrypoint, "_create_local_api_server", lambda _port: FakeServer())
    monkeypatch.setattr(entrypoint, "SingleInstance", FakeInstance)
    monkeypatch.setattr(entrypoint, "configure_desktop_logging", lambda _path: None)
    monkeypatch.setattr(
        entrypoint,
        "run_window",
        lambda _url: (_ for _ in ()).throw(AssertionError("window opened")),
    )

    assert entrypoint.main(["--portable-root", str(tmp_path), "--headless"]) == 0
    assert FakeServer.instances[-1].waited
    assert FakeServer.instances[-1].stopped


def test_second_launch_restores_existing_window(tmp_path: Path, monkeypatch) -> None:
    restored = []
    monkeypatch.setattr(entrypoint, "SingleInstance", AlreadyRunningInstance)
    monkeypatch.setattr(entrypoint, "configure_desktop_logging", lambda _path: None)
    monkeypatch.setattr(
        entrypoint,
        "activate_existing_window",
        lambda title: restored.append(title) or True,
        raising=False,
    )

    assert entrypoint.main(["--portable-root", str(tmp_path)]) == 2
    assert restored == ["一树电子商务-A股观测台"]


def test_entrypoint_accepts_an_explicit_instance_name_for_isolated_smoke(
    tmp_path: Path, monkeypatch
) -> None:
    names: list[str] = []

    class NamedInstance(FakeInstance):
        def __init__(self, name: str) -> None:
            names.append(name)
            super().__init__(name)

    monkeypatch.setattr(entrypoint, "SingleInstance", NamedInstance)
    monkeypatch.setattr(entrypoint, "_create_local_api_server", lambda _port: FakeServer())
    monkeypatch.setattr(entrypoint, "configure_desktop_logging", lambda _path: None)
    monkeypatch.setattr(entrypoint, "run_window", lambda start, **_kwargs: start())

    assert entrypoint.main([
        "--portable-root", str(tmp_path),
        "--instance-name", "xiaoqibao-smoke-test",
    ]) == 0
    assert names == ["xiaoqibao-smoke-test"]


def test_update_helper_waits_for_residual_release_processes_before_replacing(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "pending-update.json"
    manifest.write_text("{}", encoding="utf-8")
    target_root = tmp_path / "XiaoQiBao-Portable"
    target_root.mkdir()
    applied = []

    class FakeUpdate:
        def __init__(self) -> None:
            self.target_root = target_root

        def apply(self) -> int:
            applied.append(True)
            return 1

    process_states = iter([{17144}, set()])
    monkeypatch.setattr(entrypoint, "load_pending_update", lambda *_args, **_kwargs: FakeUpdate())
    monkeypatch.setattr(entrypoint, "_process_exists", lambda _pid: False)
    monkeypatch.setattr(
        entrypoint,
        "_release_process_ids",
        lambda _root, _excluded: next(process_states),
    )
    monkeypatch.setattr(entrypoint.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(entrypoint.time, "monotonic", iter([0.0, 0.1, 0.2]).__next__)
    monkeypatch.setattr(entrypoint.subprocess, "Popen", lambda *_args, **_kwargs: None)

    assert entrypoint._run_update_helper(manifest, parent_pid=42) == 0
    assert applied == [True]


def test_update_helper_keeps_manifest_and_logs_chinese_error_on_failure(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    manifest = tmp_path / "pending-update.json"
    manifest.write_text("{}", encoding="utf-8")
    target_root = tmp_path / "XiaoQiBao-Portable"
    target_root.mkdir()

    class FakeUpdate:
        def __init__(self) -> None:
            self.target_root = target_root

        def apply(self) -> int:
            raise OSError("locked")

    monkeypatch.setattr(entrypoint, "load_pending_update", lambda *_args, **_kwargs: FakeUpdate())
    monkeypatch.setattr(entrypoint, "_process_exists", lambda _pid: False)
    monkeypatch.setattr(entrypoint, "_release_process_ids", lambda _root, _excluded: set())
    monkeypatch.setattr(entrypoint.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(entrypoint.subprocess, "Popen", lambda *_args, **_kwargs: None)

    with caplog.at_level(logging.ERROR, logger="qibao_desktop.entrypoint"):
        result = entrypoint._run_update_helper(manifest, parent_pid=None)

    assert result == 4
    assert manifest.exists()
    assert "便携版更新失败" in caplog.text


def test_handoff_keeps_current_startup_when_pending_manifest_is_invalid(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    manifest = tmp_path / "pending-update.json"
    manifest.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(entrypoint, "desktop_layout", lambda _root: type(
        "Layout", (), {"root": tmp_path}
    )())
    monkeypatch.setattr(
        entrypoint,
        "load_pending_update",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("清单格式错误")),
    )

    with caplog.at_level(logging.ERROR, logger="qibao_desktop.entrypoint"):
        assert entrypoint._handoff_pending_update(tmp_path) is False

    assert manifest.exists()
    assert "待更新清单无效" in caplog.text


def test_release_process_scan_decodes_utf8_windows_paths(
    tmp_path: Path, monkeypatch
) -> None:
    target_root = tmp_path / "一树-A股观测台"
    executable = target_root / "xiaoqibao.exe"
    seen = {}

    def fake_run(*_args, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            stdout='[{"ProcessId": 17144, "ExecutablePath": "'
            + str(executable).replace("\\", "\\\\")
            + '"}]'
        )

    monkeypatch.setattr(entrypoint.subprocess, "run", fake_run)

    assert entrypoint._release_process_ids(target_root, set()) == {17144}
    assert seen["encoding"] == "utf-8"
    assert seen["errors"] == "replace"
