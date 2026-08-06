import sys
from types import SimpleNamespace
from urllib.request import urlopen

from fastapi import FastAPI

from qibao_desktop.server import LocalApiServer


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


def test_local_api_server_can_launch_before_waiting_for_health() -> None:
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


def test_local_api_server_does_not_probe_health_before_uvicorn_started(
    monkeypatch,
) -> None:
    server = LocalApiServer(app=FastAPI(), port=0, startup_timeout=5)
    server._thread = SimpleNamespace(is_alive=lambda: True, ident=None)
    server._server.started = False
    calls: list[str] = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

    def open_health(*_args, **_kwargs):
        assert server._server.started
        calls.append("health")
        return Response()

    monkeypatch.setattr("qibao_desktop.server.urlopen", open_health)
    monkeypatch.setattr(
        "qibao_desktop.server.time.sleep",
        lambda _seconds: setattr(server._server, "started", True),
    )

    try:
        server.wait_until_ready()
    finally:
        server._socket.close()

    assert calls == ["health"]
