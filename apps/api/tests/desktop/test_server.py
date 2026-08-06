import sys
from types import SimpleNamespace
from urllib.request import urlopen

from fastapi import FastAPI

from qibao_desktop.server import LocalApiServer


def test_local_api_server_pins_only_the_desktop_protocols(monkeypatch) -> None:
    captured = {}

    class FakeConfig:
        def __init__(self, app, **kwargs):
            captured["app"] = app
            captured.update(kwargs)

    class FakeServer:
        def __init__(self, config):
            self.config = config

    monkeypatch.setattr("qibao_desktop.server.uvicorn.Config", FakeConfig)
    monkeypatch.setattr("qibao_desktop.server.uvicorn.Server", FakeServer)

    server = LocalApiServer(app="qibao_api.main:app", port=0)

    assert captured["loop"] == "asyncio"
    assert captured["http"] == "h11"
    assert captured["ws"] == "none"
    assert captured["lifespan"] == "on"
    assert captured["interface"] == "asgi3"
    server._socket.close()


def test_local_api_server_initializes_without_a_console(monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    server = LocalApiServer(app=FastAPI(), port=0, startup_timeout=5)
    server.stop()


def test_local_api_server_uses_loopback_and_stops_cleanly() -> None:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    server = LocalApiServer(app=app, port=0, startup_timeout=5)
    server.start()
    try:
        assert server.url.startswith("http://127.0.0.1:")
        with urlopen(f"{server.url}/health", timeout=2) as response:
            assert response.status == 200
    finally:
        server.stop()

    server.wait()
    assert not server.is_alive


def test_local_api_server_can_launch_before_waiting_for_startup() -> None:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    server = LocalApiServer(app=app, port=0, startup_timeout=5)
    server.launch()
    try:
        assert server.is_alive
        server.wait_until_ready()
        with urlopen(f"{server.url}/health", timeout=2) as response:
            assert response.status == 200
    finally:
        server.stop()


def test_local_api_server_waits_for_uvicorn_before_returning(monkeypatch) -> None:
    server = LocalApiServer(app=FastAPI(), port=0, startup_timeout=5)
    server._thread = SimpleNamespace(is_alive=lambda: True, ident=None)
    server._server.started = False
    monkeypatch.setattr(
        "qibao_desktop.server.time.sleep",
        lambda _seconds: setattr(server._server, "started", True),
    )

    try:
        server.wait_until_ready()
    finally:
        server._socket.close()


def test_local_api_server_returns_once_uvicorn_lifespan_is_ready(
    monkeypatch,
) -> None:
    server = LocalApiServer(app=FastAPI(), port=0, startup_timeout=5)
    server._thread = SimpleNamespace(is_alive=lambda: True, ident=1)
    server._server.started = True

    try:
        server.wait_until_ready()
    finally:
        server._socket.close()
