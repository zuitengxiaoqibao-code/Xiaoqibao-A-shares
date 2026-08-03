from pathlib import Path

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
    def run_window(start_application):
        seen["server_created_before_window"] = len(FakeServer.instances) > existing_count
        seen["url"] = start_application()

    monkeypatch.setattr(entrypoint, "run_window", run_window)

    previous_data = tmp_path / "data" / "legacy"
    previous_data.mkdir(parents=True)
    (previous_data / "market.sqlite3").write_text("previous", encoding="utf-8")

    result = entrypoint.main(["--portable-root", str(tmp_path)])

    server = FakeServer.instances[-1]
    assert result == 0
    assert server.started and server.stopped
    assert seen["server_created_before_window"] is False
    assert seen["url"] == server.url
    assert (tmp_path / "config").is_dir()
    assert entrypoint.os.environ["QIBAO_DATA_DIR"] == str(tmp_path / "data")
    assert entrypoint.os.environ["QIBAO_WEB_DIR"] == str(tmp_path / "web")
    assert (tmp_path / "data" / "market.sqlite3").read_text(encoding="utf-8") == "previous"
    assert not previous_data.exists()


def test_gui_enters_window_before_runtime_disk_setup(tmp_path: Path, monkeypatch) -> None:
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

    def run_window(start_application):
        order.append("window-started")
        start_application()

    monkeypatch.setattr(entrypoint, "run_window", run_window)

    assert entrypoint.main(["--portable-root", str(tmp_path)]) == 0
    assert order[:3] == ["window-started", "layout-ready", "logging-ready"]


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
    monkeypatch.setattr(entrypoint, "run_window", lambda start: start())

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
        lambda _start: (_ for _ in ()).throw(RuntimeError("window failed")),
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
