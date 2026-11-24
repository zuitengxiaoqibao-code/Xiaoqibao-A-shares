"""Host approved websites in a native child WebView2 inside the main form.

The remote document is a normal browser document, with its original response
headers. It never receives the local application's Python JavaScript bridge.
"""

import logging
import math
from urllib.parse import urlsplit


logger = logging.getLogger(__name__)
REVIEW_URL = "https://ysclaw.hk/discover/"
PANEL_URLS = {"intelligence": REVIEW_URL, "market_cloud": "https://a.9009009.com/"}


def panel_bounds(bounds: dict, width: int, height: int) -> tuple[int, int, int, int]:
    values = [bounds.get(key) for key in ("left", "top", "width", "height")]
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or not 0 <= value <= 1 for value in values):
        raise ValueError("Invalid review panel bounds")
    left, top, panel_width, panel_height = values
    if left + panel_width > 1.001 or top + panel_height > 1.001:
        raise ValueError("Review panel must fit inside the main window")
    x, y = round(left * width), round(top * height)
    return x, y, min(round(panel_width * width), width - x), min(round(panel_height * height), height - y)


def allowed_review_navigation(uri: str, site: str = "intelligence") -> bool:
    try:
        parsed = urlsplit(uri)
        target = PANEL_URLS.get(site)
        return (target is not None and parsed.scheme == "https" and parsed.hostname == urlsplit(target).hostname
                and parsed.port in (None, 443) and parsed.username is None and parsed.password is None)
    except ValueError:
        return False


class ReviewPanelBridge:
    def __init__(self) -> None:
        self._window = None
        self._control = None
        self._error: str | None = None
        self._bounds: dict | None = None
        self._site = "intelligence"

    def _bind(self, window) -> None:
        self._window = window

    def set_review_panel(self, bounds: dict | None, reload: bool = False, site: str = "intelligence") -> dict:
        """Only the trusted local shell calls this fixed-destination bridge."""
        if not isinstance(site, str) or site not in PANEL_URLS:
            return {"available": False, "error": "未知的内嵌网页"}
        if self._window is None or self._window.native is None:
            return {"available": False, "error": "桌面网页容器尚未就绪"}
        try:
            # The desktop renderer loads these assemblies before this method.
            from System import Action
            from System.Drawing import Color, Rectangle
            from Microsoft.Web.WebView2.WinForms import WebView2

            form = self._window.native
            result = {}

            def update() -> None:
                try:
                    if bounds is None:
                        self._bounds = None
                        if self._control is not None:
                            self._control.Visible = False
                        result.update(available=True)
                        return
                    rectangle = panel_bounds(bounds, form.ClientSize.Width, form.ClientSize.Height)
                    changed = self._site != site
                    self._site = site
                    if changed:
                        self._error = None
                    self._bounds = bounds
                    if self._control is None:
                        control = WebView2()
                        self._control = control
                        # Share the existing browser environment and runtime,
                        # but not its pywebview JS injection or host objects.
                        control.CreationProperties = form.webview.CreationProperties
                        control.DefaultBackgroundColor = Color.FromArgb(255, 9, 13, 18)
                        control.CoreWebView2InitializationCompleted += self._initialized
                        control.NavigationStarting += self._navigation_starting
                        control.NavigationCompleted += self._navigation_completed
                        form.Controls.Add(control)
                        form.Resize += self._resized
                        form.webview.NavigationStarting += self._host_navigating
                        control.EnsureCoreWebView2Async(None)
                    self._control.Bounds = Rectangle(*rectangle)
                    self._control.Visible = True
                    self._control.BringToFront()
                    core = self._control.CoreWebView2
                    if (reload or changed) and core is not None:
                        self._error = None
                        core.Navigate(PANEL_URLS[self._site])
                    result.update(available=True, error=self._error)
                except Exception:
                    logger.exception("review panel update failed")
                    result.update(available=False, error="桌面网页容器启动失败，请重试")

            form.Invoke(Action(update))
            return result
        except Exception:
            logger.exception("native review panel unavailable")
            return {"available": False, "error": "当前桌面环境不支持内嵌网页"}

    def _initialized(self, _sender, args) -> None:
        if not args.IsSuccess:
            self._error = "网页容器初始化失败，请重启应用后重试"
            logger.error("review WebView2 initialization failed: %s", args.InitializationException)
            return
        core = self._control.CoreWebView2
        core.NewWindowRequested += self._new_window_requested
        core.Navigate(PANEL_URLS[self._site])

    def _navigation_starting(self, _sender, args) -> None:
        if not allowed_review_navigation(str(args.Uri), self._site):
            args.Cancel = True

    def _navigation_completed(self, _sender, args) -> None:
        self._error = None if args.IsSuccess else "网页加载失败，请检查网络后刷新"

    def _new_window_requested(self, _sender, args) -> None:
        args.Handled = True
        if allowed_review_navigation(str(args.Uri), self._site):
            self._control.CoreWebView2.Navigate(args.Uri)

    def _host_navigating(self, _sender, _args) -> None:
        self._bounds = None
        self._control.Visible = False

    def _resized(self, _sender, _args) -> None:
        if self._bounds is not None:
            from System.Drawing import Rectangle
            form = self._window.native
            self._control.Bounds = Rectangle(*panel_bounds(self._bounds, form.ClientSize.Width, form.ClientSize.Height))
