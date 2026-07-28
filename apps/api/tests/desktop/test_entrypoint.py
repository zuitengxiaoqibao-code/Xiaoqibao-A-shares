from pathlib import Path

from qibao_desktop import entrypoint


class FakeServer:
    instances = []

    def __init__(self, **_kwargs) -> None:
        self.url = "http://127.0.0.1:43210"
        self.started = False
        self.stopped = False
        self.waited = False
        self.instances.append(self)

    def start(self) -> None:
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


def test_entrypoint_sets_portable_paths_and_stops_after_window(
    tmp_path: Path, monkeypatch
) -> None:
    seen = {}
    monkeypatch.setattr(entrypoint, "LocalApiServer", FakeServer)
    monkeypatch.setattr(entrypoint, "SingleInstance", FakeInstance)
    monkeypatch.setattr(entrypoint, "configure_desktop_logging", lambda _path: None)
    monkeypatch.setattr(entrypoint, "run_window", lambda url: seen.setdefault("url", url))

    result = entrypoint.main(["--portable-root", str(tmp_path)])

    server = FakeServer.instances[-1]
    assert result == 0
    assert server.started and server.stopped
    assert seen["url"] == server.url
    assert (tmp_path / "config").is_dir()
    assert entrypoint.os.environ["QIBAO_DATA_DIR"] == str(tmp_path / "data" / "legacy")
    assert entrypoint.os.environ["QIBAO_WEB_DIR"] == str(tmp_path / "web")


def test_server_is_stopped_when_window_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(entrypoint, "LocalApiServer", FakeServer)
    monkeypatch.setattr(entrypoint, "SingleInstance", FakeInstance)
    monkeypatch.setattr(entrypoint, "configure_desktop_logging", lambda _path: None)
    monkeypatch.setattr(
        entrypoint,
        "run_window",
        lambda _url: (_ for _ in ()).throw(RuntimeError("window failed")),
    )

    assert entrypoint.main(["--portable-root", str(tmp_path)]) == 1
    assert FakeServer.instances[-1].stopped


def test_headless_mode_waits_without_opening_window(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(entrypoint, "LocalApiServer", FakeServer)
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
