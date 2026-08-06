import sys
from types import SimpleNamespace

from qibao_desktop.window import run_window


class FakeWindow:
    def __init__(self) -> None:
        self.scripts: list[str] = []
        self.loaded_url: str | None = None

    def evaluate_js(self, script: str) -> None:
        self.scripts.append(script)

    def load_url(self, url: str) -> None:
        self.loaded_url = url


def test_window_shell_is_created_before_waiting_for_api(monkeypatch) -> None:
    window = FakeWindow()
    order: list[str] = []

    monkeypatch.setitem(
        sys.modules,
        "pyi_splash",
        SimpleNamespace(close=lambda: order.append("boot-splash-closed")),
    )

    def create_window(title: str, **options):
        order.append("window-created")
        assert title == "一树电子商务-A股观测台"
        assert "正在启动一树电子商务-A股观测台" in options["html"]
        assert "一树-A股观测台" in options["html"]
        assert "1%" in options["html"]
        assert "homepage-progress-tracer" in options["html"]
        return window

    def start(callback, **_options):
        order.append("webview-started")
        callback()

    monkeypatch.setitem(
        sys.modules,
        "webview",
        SimpleNamespace(create_window=create_window, start=start),
    )

    def start_application() -> str:
        order.append("api-ready")
        return "http://127.0.0.1:43210"

    run_window(start_application)

    assert order == [
        "window-created",
        "webview-started",
        "boot-splash-closed",
        "api-ready",
    ]
    assert window.loaded_url == "http://127.0.0.1:43210/?desktopBoot=42"
    assert any("24" in script and "桌面窗口已显示" in script for script in window.scripts)
    assert any("42" in script and "本地 API 已就绪" in script for script in window.scripts)


def test_window_keeps_startup_shell_visible_when_api_fails(monkeypatch) -> None:
    window = FakeWindow()
    monkeypatch.setitem(
        sys.modules,
        "webview",
        SimpleNamespace(
            create_window=lambda *_args, **_options: window,
            start=lambda callback, **_options: callback(),
        ),
    )

    def fail() -> None:
        raise RuntimeError("health timeout")

    run_window(fail)

    assert window.loaded_url is None
    assert "启动失败" in window.scripts[-1]
    assert "health timeout" in window.scripts[-1]
