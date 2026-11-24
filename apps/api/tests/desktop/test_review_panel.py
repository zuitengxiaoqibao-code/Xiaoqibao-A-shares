import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from qibao_desktop.review_panel import allowed_review_navigation, panel_bounds, ReviewPanelBridge


def test_panel_uses_client_ratios_for_dpi_and_resizing():
    bounds = {"left": .2, "top": .1, "width": .8, "height": .9}
    assert panel_bounds(bounds, 1500, 900) == (300, 90, 1200, 810)
    assert panel_bounds(bounds, 1000, 700) == (200, 70, 800, 630)


@pytest.mark.parametrize("value", [-1, 2, float("nan"), float("inf"), "1", True, None])
def test_panel_rejects_invalid_coordinates(value):
    with pytest.raises(ValueError):
        panel_bounds({"left": value, "top": 0, "width": 1, "height": 1}, 1000, 700)


def test_panel_rejects_out_of_window_layout():
    with pytest.raises(ValueError):
        panel_bounds({"left": .2, "top": 0, "width": .9, "height": 1}, 1000, 700)


@pytest.mark.parametrize("uri", ["https://ysclaw.hk/discover/", "https://ysclaw.hk/discover/login", "https://ysclaw.hk:443/discover/"])
def test_review_allows_its_own_https_navigation(uri):
    assert allowed_review_navigation(uri)


@pytest.mark.parametrize("uri", ["http://ysclaw.hk/discover/", "https://ysclaw.hk.evil.test/", "file:///C:/", "http://127.0.0.1:18765/", "https://ysclaw.hk:88/", "https://user:secret@ysclaw.hk/"])
def test_remote_review_cannot_navigate_into_local_files_or_services(uri):
    assert not allowed_review_navigation(uri)


def test_bridge_reports_an_unavailable_host_without_importing_windows_sdk():
    assert ReviewPanelBridge().set_review_panel(None)["available"] is False


@pytest.mark.parametrize("uri", ["https://a.9009009.com/", "https://a.9009009.com:443/help"])
def test_cloud_allows_its_own_https_navigation(uri):
    assert allowed_review_navigation(uri, "market_cloud")
    assert not allowed_review_navigation(uri, "intelligence")


@pytest.mark.parametrize("uri", ["http://a.9009009.com/", "https://a.9009009.com.evil.test/", "https://a.9009009.com:88/", "https://user:secret@a.9009009.com/", "https://ysclaw.hk/discover/", "file:///C:/", "http://127.0.0.1:18765/"])
def test_cloud_blocks_other_hosts_credentials_and_local_resources(uri):
    assert not allowed_review_navigation(uri, "market_cloud")


def test_bridge_rejects_arbitrary_website_destinations():
    bridge = ReviewPanelBridge()
    assert bridge.set_review_panel(None, site="https://evil.test/")["available"] is False
    assert bridge.set_review_panel(None, site=[])["available"] is False


def test_native_control_switches_destinations_and_reloads_only_the_active_site(monkeypatch):
    monkeypatch.setitem(sys.modules, "System", SimpleNamespace(Action=lambda callback: callback))
    monkeypatch.setitem(sys.modules, "System.Drawing", SimpleNamespace(Color=Mock(), Rectangle=lambda *values: values))
    monkeypatch.setitem(sys.modules, "Microsoft.Web.WebView2.WinForms", SimpleNamespace(WebView2=Mock()))
    core = Mock()
    control = SimpleNamespace(CoreWebView2=core, BringToFront=Mock(), Visible=False)
    form = SimpleNamespace(ClientSize=SimpleNamespace(Width=1000, Height=700), Invoke=lambda callback: callback())
    bridge = ReviewPanelBridge()
    bridge._bind(SimpleNamespace(native=form))
    bridge._control = control
    bounds = {"left": .2, "top": .1, "width": .8, "height": .9}

    assert bridge.set_review_panel(bounds, site="market_cloud")["available"] is True
    core.Navigate.assert_called_once_with("https://a.9009009.com/")
    assert control.Visible is True
    assert bridge.set_review_panel(bounds, site="market_cloud")["available"] is True
    assert core.Navigate.call_count == 1
    assert bridge.set_review_panel(None, site="market_cloud")["available"] is True
    assert control.Visible is False
    assert bridge.set_review_panel(bounds, site="intelligence")["available"] is True
    core.Navigate.assert_called_with("https://ysclaw.hk/discover/")
    assert core.Navigate.call_count == 2
    assert bridge.set_review_panel(bounds, reload=True, site="intelligence")["available"] is True
    assert core.Navigate.call_count == 3
    args = SimpleNamespace(Uri="https://a.9009009.com/", Cancel=False)
    bridge._navigation_starting(None, args)
    assert args.Cancel is True
