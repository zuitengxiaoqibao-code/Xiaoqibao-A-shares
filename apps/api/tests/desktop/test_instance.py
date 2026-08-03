import sys

import pytest

from qibao_desktop import instance as instance_module
from qibao_desktop.instance import AlreadyRunningError, SingleInstance


@pytest.mark.skipif(sys.platform != "win32", reason="Windows mutex")
def test_named_mutex_rejects_second_instance() -> None:
    first = SingleInstance("qibao-test-exclusive")
    second = SingleInstance("qibao-test-exclusive")
    first.acquire()
    try:
        with pytest.raises(AlreadyRunningError):
            second.acquire()
    finally:
        first.close()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows window activation")
def test_activate_existing_window_restores_and_focuses_named_window(
    monkeypatch,
) -> None:
    calls = []

    class User32:
        def FindWindowW(self, class_name, title):
            calls.append(("find", class_name, title))
            return 123

        def ShowWindow(self, hwnd, command):
            calls.append(("show", hwnd, command))
            return True

        def BringWindowToTop(self, hwnd):
            calls.append(("top", hwnd))
            return True

        def SetForegroundWindow(self, hwnd):
            calls.append(("foreground", hwnd))
            return True

    monkeypatch.setattr(instance_module, "_user32", User32, raising=False)

    assert instance_module.activate_existing_window("一树电子商务-A股观测台") is True
    assert calls == [
        ("find", None, "一树电子商务-A股观测台"),
        ("show", 123, 9),
        ("top", 123),
        ("foreground", 123),
    ]
