# 小七宝便携桌面基础 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付首个无需 Node.js 开发服务器、双击 `xiaoqibao.exe` 即可启动现有 React + FastAPI 功能的 Windows 便携目录。

**Architecture:** 使用 PyInstaller onedir 打包 Python 服务，React 生产资源作为便携目录中的独立 `web/` 文件夹，由 FastAPI 托管。桌面入口预绑定本地端口、启动单进程 Uvicorn、等待健康检查后打开 pywebview/WebView2 窗口，并在窗口关闭时优雅结束服务。

**Tech Stack:** Python 3.12、FastAPI 0.116、Uvicorn 0.35、pywebview/WebView2、PyInstaller 6、React 19、Vite 7、pytest、Vitest、PowerShell。

## Global Constraints

- 目标平台为 Windows 10/11，发布形式为 PyInstaller `onedir`，不得生成安装程序或使用 `onefile`。
- 成品根目录必须包含 `xiaoqibao.exe`、`_internal/`、`web/`、`config/`、`data/`、`news/`、`cache/`、`logs/`、`models/`、`exports/` 和 `backups/`。
- 运行路径必须以可执行文件目录为基准，不得依赖当前工作目录。
- 服务只监听 `127.0.0.1`，默认预绑定随机可用端口，不开放局域网访问。
- 启动不需要 Node.js、pnpm 或 Vite 开发服务器；WebView2 使用系统运行时，不捆绑 Chromium。
- 本阶段不移动、不删除现有 `.runtime`；桌面版把现有仓储临时放在 `data/legacy/`，后续存储迁移计划再按领域拆分。
- Kronos、PyTorch 和模型权重不进入主程序，`models/` 仅作为外部目录。
- 手工编辑中文文件必须使用 `apply_patch`；完成后运行中文乱码扫描、`git diff --check`、后端测试和前端生产构建。
- 工作区已有大量用户改动；每次提交只暂存本任务明确列出的文件。

## Scope Boundary

这是四个实施阶段中的第一阶段，只交付可启动、可测试、可重新构建的桌面基础和首个便携 EXE。通达信本地行情与 WebSocket、新闻/缓存/数据库迁移、大型模块拆分与最终性能验收分别进入后续独立计划；第一阶段不得以临时实现宣称完整规格已经交付。

---

## File Structure

### 新增后端运行目录模块

- `apps/api/src/qibao_api/runtime/__init__.py`：导出运行目录契约。
- `apps/api/src/qibao_api/runtime/layout.py`：便携根目录解析、目录清单和安全创建。
- `apps/api/tests/runtime/test_layout.py`：冻结态、开发态、显式根目录和目录创建测试。

### 新增静态前端模块

- `apps/api/src/qibao_api/static_frontend.py`：静态资源挂载、SPA 回退和 API 路径隔离。
- `apps/api/tests/test_static_frontend.py`：资源、深层书签、API 404 和缺失构建测试。
- `apps/api/src/qibao_api/settings.py`：新增 `web_dir`，保留当前 `data_dir` 兼容。
- `apps/api/src/qibao_api/main.py`：所有 API 路由注册完成后安装静态前端。

### 新增桌面入口包

- `apps/api/src/qibao_desktop/__init__.py`：桌面包版本。
- `apps/api/src/qibao_desktop/__main__.py`：支持 `python -m qibao_desktop` 和 PyInstaller 入口。
- `apps/api/src/qibao_desktop/paths.py`：从参数或 EXE 位置得到 `RuntimeLayout`。
- `apps/api/src/qibao_desktop/instance.py`：Windows 命名互斥体单实例。
- `apps/api/src/qibao_desktop/server.py`：本地端口、Uvicorn 线程、健康等待和停止。
- `apps/api/src/qibao_desktop/window.py`：pywebview 窗口适配器。
- `apps/api/src/qibao_desktop/logging_config.py`：滚动文件日志。
- `apps/api/src/qibao_desktop/entrypoint.py`：组合以上组件并管理完整生命周期。
- `apps/api/tests/desktop/test_paths.py`：桌面根目录和环境变量测试。
- `apps/api/tests/desktop/test_instance.py`：单实例互斥测试。
- `apps/api/tests/desktop/test_server.py`：真实本地 ASGI 健康和停止测试。
- `apps/api/tests/desktop/test_entrypoint.py`：无窗口模式和异常清理测试。

### 新增打包文件

- `packaging/xiaoqibao.spec`：PyInstaller onedir 配置。
- `scripts/build-portable.ps1`：前端构建、EXE 构建、目录创建和体积报告。
- `scripts/run-portable-smoke.ps1`：成品健康、首页和退出冒烟。
- `apps/api/pyproject.toml`：包含 `qibao_desktop` 包、桌面依赖和命令入口。
- `README.md`：补充开发启动与便携版构建、目录和限制。

---

### Task 1: Portable Runtime Layout

**Files:**
- Create: `apps/api/src/qibao_api/runtime/__init__.py`
- Create: `apps/api/src/qibao_api/runtime/layout.py`
- Test: `apps/api/tests/runtime/test_layout.py`

**Interfaces:**
- Consumes: `pathlib.Path` 和调用方提供的便携根目录。
- Produces: `RuntimeLayout.from_root(root: Path) -> RuntimeLayout`、`RuntimeLayout.ensure() -> None`、`RuntimeLayout.directory_map() -> dict[str, Path]`。

- [ ] **Step 1: Write the failing layout tests**

```python
from pathlib import Path

from qibao_api.runtime.layout import RuntimeLayout


def test_runtime_layout_maps_every_portable_directory(tmp_path: Path) -> None:
    layout = RuntimeLayout.from_root(tmp_path / "portable")

    assert layout.root == (tmp_path / "portable").resolve()
    assert layout.web_dir == layout.root / "web"
    assert layout.config_dir == layout.root / "config"
    assert layout.data_dir == layout.root / "data"
    assert layout.legacy_data_dir == layout.root / "data" / "legacy"
    assert layout.news_dir == layout.root / "news"
    assert layout.cache_dir == layout.root / "cache"
    assert layout.logs_dir == layout.root / "logs"
    assert layout.models_dir == layout.root / "models"
    assert layout.exports_dir == layout.root / "exports"
    assert layout.backups_dir == layout.root / "backups"


def test_ensure_creates_runtime_directories_but_not_web_assets(tmp_path: Path) -> None:
    layout = RuntimeLayout.from_root(tmp_path / "portable")

    layout.ensure()

    assert not layout.web_dir.exists()
    for name, path in layout.directory_map().items():
        if name != "web":
            assert path.is_dir(), name
```

- [ ] **Step 2: Run the tests and verify the import fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests\runtime\test_layout.py -q
```

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'qibao_api.runtime'`.

- [ ] **Step 3: Implement the immutable layout**

`apps/api/src/qibao_api/runtime/layout.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeLayout:
    root: Path
    web_dir: Path
    config_dir: Path
    data_dir: Path
    legacy_data_dir: Path
    news_dir: Path
    cache_dir: Path
    logs_dir: Path
    models_dir: Path
    exports_dir: Path
    backups_dir: Path

    @classmethod
    def from_root(cls, root: Path) -> "RuntimeLayout":
        resolved = root.expanduser().resolve()
        data_dir = resolved / "data"
        return cls(
            root=resolved,
            web_dir=resolved / "web",
            config_dir=resolved / "config",
            data_dir=data_dir,
            legacy_data_dir=data_dir / "legacy",
            news_dir=resolved / "news",
            cache_dir=resolved / "cache",
            logs_dir=resolved / "logs",
            models_dir=resolved / "models",
            exports_dir=resolved / "exports",
            backups_dir=resolved / "backups",
        )

    def directory_map(self) -> dict[str, Path]:
        return {
            "web": self.web_dir,
            "config": self.config_dir,
            "data": self.data_dir,
            "legacy_data": self.legacy_data_dir,
            "news": self.news_dir,
            "cache": self.cache_dir,
            "logs": self.logs_dir,
            "models": self.models_dir,
            "exports": self.exports_dir,
            "backups": self.backups_dir,
        }

    def ensure(self) -> None:
        for name, path in self.directory_map().items():
            if name != "web":
                path.mkdir(parents=True, exist_ok=True)
```

`apps/api/src/qibao_api/runtime/__init__.py`:

```python
from qibao_api.runtime.layout import RuntimeLayout

__all__ = ["RuntimeLayout"]
```

- [ ] **Step 4: Run the focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests\runtime\test_layout.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit only the runtime layout files**

```powershell
git add apps/api/src/qibao_api/runtime apps/api/tests/runtime/test_layout.py
git commit -m "feat: add portable runtime layout"
```

---

### Task 2: FastAPI Static Frontend Hosting

**Files:**
- Create: `apps/api/src/qibao_api/static_frontend.py`
- Create: `apps/api/tests/test_static_frontend.py`
- Modify: `apps/api/src/qibao_api/settings.py`
- Modify: `apps/api/src/qibao_api/main.py`

**Interfaces:**
- Consumes: 已注册 API 路由的 `FastAPI` 实例和前端构建目录。
- Produces: `install_static_frontend(app: FastAPI, web_dir: Path) -> None`；`Settings.web_dir: Path`。

- [ ] **Step 1: Write failing static hosting tests**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.static_frontend import install_static_frontend


def make_app(web_dir: Path) -> TestClient:
    app = FastAPI()

    @app.get("/api/example")
    def example() -> dict[str, bool]:
        return {"ok": True}

    install_static_frontend(app, web_dir)
    return TestClient(app)


def test_static_frontend_serves_assets_and_spa_bookmarks(tmp_path: Path) -> None:
    web = tmp_path / "web"
    assets = web / "assets"
    assets.mkdir(parents=True)
    (web / "index.html").write_text("<main>desktop</main>", encoding="utf-8")
    (assets / "app.js").write_text("window.desktop=true", encoding="utf-8")
    client = make_app(web)

    assert client.get("/").text == "<main>desktop</main>"
    assert client.get("/a-shares").text == "<main>desktop</main>"
    assert client.get("/assets/app.js").text == "window.desktop=true"
    assert client.get("/api/example").json() == {"ok": True}


def test_static_frontend_never_turns_unknown_api_into_html(tmp_path: Path) -> None:
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<main>desktop</main>", encoding="utf-8")
    response = make_app(web).get("/api/missing")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_missing_web_build_leaves_api_only_app(tmp_path: Path) -> None:
    app = FastAPI()
    install_static_frontend(app, tmp_path / "missing")

    assert TestClient(app).get("/").status_code == 404
```

- [ ] **Step 2: Run tests and verify the module is missing**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests\test_static_frontend.py -q
```

Expected: FAIL during collection for `qibao_api.static_frontend`.

- [ ] **Step 3: Implement static assets and SPA fallback**

`apps/api/src/qibao_api/static_frontend.py`:

```python
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def install_static_frontend(app: FastAPI, web_dir: Path) -> None:
    root = web_dir.expanduser().resolve()
    index = root / "index.html"
    assets = root / "assets"
    if not index.is_file():
        return
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="web-assets")

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, spa_path: str):
        if request.url.path.startswith(("/api/", "/ws/")):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (root / spa_path).resolve()
        if root in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
```

Add to `Settings`:

```python
DEFAULT_WEB_DIR = PROJECT_ROOT / "apps" / "web" / "dist"


class Settings(BaseSettings):
    web_dir: Path = DEFAULT_WEB_DIR

    @field_validator("data_dir", "web_dir", mode="after")
    @classmethod
    def resolve_project_path(cls, value: Path) -> Path:
        return value if value.is_absolute() else (PROJECT_ROOT / value).resolve()
```

Replace the existing `data_dir`-only validator rather than defining two validators for the same field.

At the end of `main.py`, after every `include_router` call:

```python
from qibao_api.static_frontend import install_static_frontend


install_static_frontend(app, Settings().web_dir)
```

- [ ] **Step 4: Run static hosting and settings tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests\test_static_frontend.py apps\api\tests\test_settings.py apps\api\tests\test_settings_repository.py apps\api\tests\routes\test_settings.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Build the frontend and smoke the production index through FastAPI**

Run:

```powershell
pnpm.cmd --filter @qibao/web build
.\.venv\Scripts\python.exe -m pytest apps\api\tests\test_static_frontend.py -q
```

Expected: Vite build succeeds and static tests pass.

- [ ] **Step 6: Commit only static hosting files**

```powershell
git add apps/api/src/qibao_api/static_frontend.py apps/api/src/qibao_api/settings.py apps/api/src/qibao_api/main.py apps/api/tests/test_static_frontend.py
git commit -m "feat: serve production frontend from local api"
```

---

### Task 3: Local Server and Single Instance Primitives

**Files:**
- Create: `apps/api/src/qibao_desktop/__init__.py`
- Create: `apps/api/src/qibao_desktop/paths.py`
- Create: `apps/api/src/qibao_desktop/instance.py`
- Create: `apps/api/src/qibao_desktop/server.py`
- Test: `apps/api/tests/desktop/test_paths.py`
- Test: `apps/api/tests/desktop/test_instance.py`
- Test: `apps/api/tests/desktop/test_server.py`

**Interfaces:**
- Consumes: `RuntimeLayout`, Windows kernel32 and任意 ASGI 应用。
- Produces: `desktop_layout(root: Path | None) -> RuntimeLayout`、`SingleInstance.acquire()`、`LocalApiServer.start()`、`LocalApiServer.stop()`、`LocalApiServer.url`。

- [ ] **Step 1: Write failing primitive tests**

`apps/api/tests/desktop/test_paths.py`:

```python
from pathlib import Path

from qibao_desktop.paths import desktop_layout


def test_explicit_portable_root_wins(tmp_path: Path) -> None:
    layout = desktop_layout(tmp_path / "portable")
    assert layout.root == (tmp_path / "portable").resolve()
```

`apps/api/tests/desktop/test_instance.py`:

```python
import sys

import pytest

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
```

`apps/api/tests/desktop/test_server.py`:

```python
from urllib.request import urlopen

from fastapi import FastAPI

from qibao_desktop.server import LocalApiServer


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

    assert not server.is_alive
```

- [ ] **Step 2: Run tests and verify missing desktop modules**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests\desktop -q
```

Expected: collection fails for `qibao_desktop`.

- [ ] **Step 3: Implement path and package files**

`apps/api/src/qibao_desktop/__init__.py`:

```python
__version__ = "0.1.0"
```

`apps/api/src/qibao_desktop/paths.py`:

```python
import sys
from pathlib import Path

from qibao_api.runtime import RuntimeLayout


def desktop_layout(root: Path | None = None) -> RuntimeLayout:
    if root is not None:
        return RuntimeLayout.from_root(root)
    executable = Path(sys.executable if getattr(sys, "frozen", False) else __file__)
    base = executable.resolve().parent if getattr(sys, "frozen", False) else Path.cwd()
    return RuntimeLayout.from_root(base)
```

- [ ] **Step 4: Implement the Windows named mutex**

`apps/api/src/qibao_desktop/instance.py`:

```python
import ctypes
import sys
from ctypes import wintypes


ERROR_ALREADY_EXISTS = 183


class AlreadyRunningError(RuntimeError):
    pass


class SingleInstance:
    def __init__(self, name: str) -> None:
        self.name = name
        self._handle = None

    def acquire(self) -> None:
        if self._handle is not None:
            return
        if sys.platform != "win32":
            raise RuntimeError("desktop single-instance lock requires Windows")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateMutexW(None, True, f"Local\\{self.name}")
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            raise AlreadyRunningError("xiaoqibao is already running")
        self._handle = handle

    def close(self) -> None:
        if self._handle is None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.ReleaseMutex(self._handle)
        kernel32.CloseHandle(self._handle)
        self._handle = None

    def __enter__(self) -> "SingleInstance":
        self.acquire()
        return self

    def __exit__(self, *_args) -> None:
        self.close()
```

- [ ] **Step 5: Implement the pre-bound Uvicorn server**

`apps/api/src/qibao_desktop/server.py`:

```python
import socket
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn


class LocalApiServer:
    def __init__(
        self,
        *,
        app,
        port: int = 0,
        startup_timeout: float = 30,
        log_level: str = "warning",
    ) -> None:
        self.startup_timeout = startup_timeout
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", port))
        self._socket.listen(128)
        self.port = int(self._socket.getsockname()[1])
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=self.port,
            log_level=log_level,
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._run,
            name="qibao-local-api",
            daemon=False,
        )

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def _run(self) -> None:
        self._server.run(sockets=[self._socket])

    def start(self) -> None:
        self._thread.start()
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if not self._thread.is_alive():
                raise RuntimeError("local API exited during startup")
            try:
                with urlopen(f"{self.url}/health", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (OSError, URLError):
                time.sleep(0.05)
        self.stop()
        raise TimeoutError("local API health check timed out")

    def stop(self) -> None:
        self._server.should_exit = True
        if self._thread.ident is not None:
            self._thread.join(timeout=10)
        try:
            self._socket.close()
        except OSError:
            pass
```

- [ ] **Step 6: Run primitive tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests\desktop\test_paths.py apps\api\tests\desktop\test_instance.py apps\api\tests\desktop\test_server.py -q
```

Expected: `3 passed` on Windows.

- [ ] **Step 7: Commit only desktop primitives**

```powershell
git add apps/api/src/qibao_desktop/__init__.py apps/api/src/qibao_desktop/paths.py apps/api/src/qibao_desktop/instance.py apps/api/src/qibao_desktop/server.py apps/api/tests/desktop/test_paths.py apps/api/tests/desktop/test_instance.py apps/api/tests/desktop/test_server.py
git commit -m "feat: add local desktop server lifecycle"
```

---

### Task 4: Desktop Window, Logging, and Entrypoint

**Files:**
- Create: `apps/api/src/qibao_desktop/window.py`
- Create: `apps/api/src/qibao_desktop/logging_config.py`
- Create: `apps/api/src/qibao_desktop/entrypoint.py`
- Create: `apps/api/src/qibao_desktop/__main__.py`
- Test: `apps/api/tests/desktop/test_entrypoint.py`
- Modify: `apps/api/pyproject.toml`

**Interfaces:**
- Consumes: `RuntimeLayout`、`SingleInstance`、`LocalApiServer` 和 pywebview。
- Produces: `run_window(url: str) -> None`、`configure_desktop_logging(logs_dir: Path) -> None`、`main(argv: list[str] | None = None) -> int`。

- [ ] **Step 1: Write failing entrypoint lifecycle tests**

```python
from pathlib import Path

from qibao_desktop import entrypoint


class FakeServer:
    instances = []

    def __init__(self, **_kwargs) -> None:
        self.url = "http://127.0.0.1:43210"
        self.started = False
        self.stopped = False
        self.instances.append(self)

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


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
```

- [ ] **Step 2: Run tests and verify entrypoint is missing**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests\desktop\test_entrypoint.py -q
```

Expected: FAIL importing `qibao_desktop.entrypoint`.

- [ ] **Step 3: Implement pywebview adapter and rolling logs**

`apps/api/src/qibao_desktop/window.py`:

```python
def run_window(url: str) -> None:
    try:
        import webview
    except ImportError as error:
        raise RuntimeError("pywebview is not installed") from error
    webview.create_window(
        "小七宝量化决策台",
        url,
        width=1500,
        height=920,
        min_size=(1080, 700),
        background_color="#06080d",
    )
    webview.start(debug=False)
```

`apps/api/src/qibao_desktop/logging_config.py`:

```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_desktop_logging(logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        logs_dir / "xiaoqibao.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
```

- [ ] **Step 4: Implement the desktop entrypoint**

`apps/api/src/qibao_desktop/entrypoint.py`:

```python
import argparse
import logging
import os
from pathlib import Path

from qibao_desktop.instance import AlreadyRunningError, SingleInstance
from qibao_desktop.logging_config import configure_desktop_logging
from qibao_desktop.paths import desktop_layout
from qibao_desktop.server import LocalApiServer
from qibao_desktop.window import run_window


logger = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xiaoqibao")
    parser.add_argument("--portable-root", type=Path)
    parser.add_argument("--port", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    layout = desktop_layout(args.portable_root)
    layout.ensure()
    configure_desktop_logging(layout.logs_dir)
    os.environ["QIBAO_PORTABLE_ROOT"] = str(layout.root)
    os.environ["QIBAO_DATA_DIR"] = str(layout.legacy_data_dir)
    os.environ["QIBAO_WEB_DIR"] = str(layout.web_dir)
    server = None
    try:
        with SingleInstance("xiaoqibao-portable"):
            server = LocalApiServer(
                app="qibao_api.main:app",
                port=args.port,
                startup_timeout=60,
            )
            server.start()
            run_window(server.url)
        return 0
    except AlreadyRunningError:
        logger.warning("xiaoqibao is already running")
        return 2
    except Exception:
        logger.exception("desktop startup failed")
        return 1
    finally:
        if server is not None:
            server.stop()
```

`apps/api/src/qibao_desktop/__main__.py`:

```python
from qibao_desktop.entrypoint import main


raise SystemExit(main())
```

- [ ] **Step 5: Add package and dependency metadata**

Update `apps/api/pyproject.toml`:

```toml
[project]
name = "qibao-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi==0.116.1",
  "httpx==0.25.2",
  "duckdb==1.3.2",
  "mootdx>=0.11,<0.12",
  "pandas==2.3.1",
  "pydantic==2.11.7",
  "pydantic-settings==2.10.1",
  "sqlalchemy==2.0.41",
  "uvicorn[standard]==0.35.0",
  "exchange-calendars==4.13.2",
  "pywebview>=5.4,<7",
]

[project.scripts]
xiaoqibao = "qibao_desktop.entrypoint:main"

[project.optional-dependencies]
dev = [
  "hypothesis==6.135.32",
  "pytest==8.4.1",
  "pytest-asyncio==1.1.0",
  "ruff==0.12.3",
  "pyinstaller>=6.14,<7",
]

[tool.hatch.build.targets.wheel]
packages = ["src/qibao_api", "src/qibao_desktop"]
```

- [ ] **Step 6: Install the editable desktop dependencies and run tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".\apps\api[dev]"
.\.venv\Scripts\python.exe -m pytest apps\api\tests\desktop -q
```

Expected: desktop dependencies install and all desktop tests pass.

- [ ] **Step 7: Commit only the entrypoint files and metadata**

```powershell
git add apps/api/src/qibao_desktop/window.py apps/api/src/qibao_desktop/logging_config.py apps/api/src/qibao_desktop/entrypoint.py apps/api/src/qibao_desktop/__main__.py apps/api/tests/desktop/test_entrypoint.py apps/api/pyproject.toml
git commit -m "feat: add portable desktop entrypoint"
```

---

### Task 5: PyInstaller onedir Build and Product Smoke

**Files:**
- Create: `packaging/xiaoqibao.spec`
- Create: `scripts/build-portable.ps1`
- Create: `scripts/run-portable-smoke.ps1`
- Modify: `README.md`

**Interfaces:**
- Consumes: `qibao_desktop.__main__`、`apps/web/dist` 和当前 Python 环境。
- Produces: `dist/XiaoQiBao-Portable/xiaoqibao.exe` 及独立运行目录。

- [ ] **Step 1: Add the onedir PyInstaller specification**

`packaging/xiaoqibao.spec`:

```python
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path(SPECPATH).parent
api_src = project_root / "apps" / "api" / "src"
hiddenimports = (
    collect_submodules("qibao_api")
    + collect_submodules("qibao_desktop")
    + collect_submodules("mootdx")
    + collect_submodules("uvicorn")
    + collect_submodules("webview")
)
datas = collect_data_files("exchange_calendars")

a = Analysis(
    [str(api_src / "qibao_desktop" / "__main__.py")],
    pathex=[str(api_src)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest", "hypothesis"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="xiaoqibao",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="XiaoQiBao-Portable",
)
```

- [ ] **Step 2: Add the deterministic build script**

`scripts/build-portable.ps1` must contain:

```powershell
param([switch]$SkipTests)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Release = Join-Path $Root "dist\XiaoQiBao-Portable"

if (-not $SkipTests) {
    & $Python -m pytest (Join-Path $Root "apps\api\tests") -q
    if ($LASTEXITCODE -ne 0) { throw "API tests failed" }
    & pnpm.cmd --dir $Root --filter "@qibao/web" test
    if ($LASTEXITCODE -ne 0) { throw "Web tests failed" }
}

& pnpm.cmd --dir $Root --filter "@qibao/web" build
if ($LASTEXITCODE -ne 0) { throw "Web build failed" }
& $Python -m PyInstaller --noconfirm --clean (Join-Path $Root "packaging\xiaoqibao.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$WebTarget = Join-Path $Release "web"
New-Item -ItemType Directory -Force -Path $WebTarget | Out-Null
Copy-Item -Path (Join-Path $Root "apps\web\dist\*") -Destination $WebTarget -Recurse -Force
foreach ($Name in @("config", "data", "news", "cache", "logs", "models", "exports", "backups")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Release $Name) | Out-Null
}

$Files = Get-ChildItem -LiteralPath $Release -Recurse -File
$Bytes = ($Files | Measure-Object Length -Sum).Sum
Write-Host ("Portable release: {0}" -f $Release)
Write-Host ("Files: {0}; Size: {1:N1} MB" -f $Files.Count, ($Bytes / 1MB))
```

- [ ] **Step 3: Add a safe product smoke script**

`scripts/run-portable-smoke.ps1`:

```powershell
param([int]$Port = 18765)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Exe = Join-Path $Root "dist\XiaoQiBao-Portable\xiaoqibao.exe"
$SmokeRoot = Join-Path $env:TEMP ("xiaoqibao-smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $SmokeRoot | Out-Null
$Process = Start-Process -FilePath $Exe -ArgumentList @(
    "--portable-root", $SmokeRoot,
    "--port", $Port,
    "--headless"
) -PassThru -WindowStyle Hidden

try {
    $Deadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        try {
            $Health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 1
            break
        } catch {
            Start-Sleep -Milliseconds 200
        }
    } while ([DateTime]::UtcNow -lt $Deadline)
    if ($null -eq $Health) { throw "Portable health check timed out" }
    $Home = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -TimeoutSec 5
    if ($Home.StatusCode -ne 200 -or $Home.Content -notmatch "root") {
        throw "Portable frontend smoke failed"
    }
    Write-Host "Portable smoke passed"
} finally {
    if (-not $Process.HasExited) { Stop-Process -Id $Process.Id }
}
```

- [ ] **Step 4: Add the tested headless smoke interface**

Add to `LocalApiServer` in `apps/api/src/qibao_desktop/server.py`:

```python
    def wait(self) -> None:
        self._thread.join()
```

Add the parser option in `apps/api/src/qibao_desktop/entrypoint.py`:

```python
    parser.add_argument("--headless", action="store_true")
```

Replace the window call in `main()` with:

```python
            if args.headless:
                server.wait()
            else:
                run_window(server.url)
```

Extend `FakeServer` in `apps/api/tests/desktop/test_entrypoint.py`:

```python
        self.waited = False

    def wait(self) -> None:
        self.waited = True
```

Add the headless test:

```python
def test_headless_mode_waits_without_opening_window(tmp_path: Path, monkeypatch) -> None:
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
```

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests\desktop\test_entrypoint.py apps\api\tests\desktop\test_server.py -q
```

Expected: all entrypoint and server tests pass.

- [ ] **Step 5: Build and inspect the portable product**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-portable.ps1
Get-ChildItem -LiteralPath .\dist\XiaoQiBao-Portable -Force
```

Expected: `xiaoqibao.exe`, `_internal`, `web` and all empty user-data directories exist; no `node_modules`, `.runtime`, model weights or Chromium directory is present.

- [ ] **Step 6: Run product smoke and process cleanup check**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-portable-smoke.ps1
Get-Process xiaoqibao -ErrorAction SilentlyContinue
```

Expected: script prints `Portable smoke passed`; no `xiaoqibao` process remains.

- [ ] **Step 7: Document the portable build**

Append to `README.md`:

````markdown
## Windows 便携版

便携版不需要安装，也不需要 Node.js 开发服务器。构建命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-portable.ps1
```

产物位于 `dist\XiaoQiBao-Portable`。双击 `xiaoqibao.exe` 启动；`_internal` 和 `web` 是程序运行文件，`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 是可独立管理的本地目录。请移动整个目录，不要只移动 EXE。

该产物不是安装程序，不写注册表、不申请管理员权限。当前阶段保留旧 `.runtime`，便携版使用 `data\legacy` 运行现有仓储；后续迁移会按数据域拆分且不会自动删除旧数据。
````

- [ ] **Step 8: Commit packaging and documentation**

```powershell
git add packaging/xiaoqibao.spec scripts/build-portable.ps1 scripts/run-portable-smoke.ps1 apps/api/src/qibao_desktop/entrypoint.py apps/api/src/qibao_desktop/server.py apps/api/tests/desktop/test_entrypoint.py README.md
git commit -m "build: produce portable Windows desktop app"
```

---

### Task 6: Foundation Regression Gate

**Files:**
- Modify only files required to fix failures introduced by Tasks 1-5.

**Interfaces:**
- Consumes: 完整桌面基础实现。
- Produces: 一个经过后端、前端、乱码、路径和成品冒烟验证的便携基础版本。

- [ ] **Step 1: Run focused desktop and static tests**

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests\desktop apps\api\tests\runtime apps\api\tests\test_static_frontend.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run the complete backend checks**

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests -q
.\.venv\Scripts\python.exe -m ruff check apps\api\src apps\api\tests scripts\restore_backup.py
```

Expected: all tests and Ruff pass. Existing unrelated baseline failures must be recorded separately and must not be hidden by changing expectations.

- [ ] **Step 3: Run the complete frontend checks**

```powershell
pnpm.cmd --filter @qibao/web test
pnpm.cmd --filter @qibao/web build
```

Expected: Vitest and Vite build pass.

- [ ] **Step 4: Run encoding and whitespace gates**

```powershell
rg -n "�|Ã|Â|â|\?\?\?" apps/api/src/qibao_desktop apps/api/src/qibao_api/runtime apps/api/src/qibao_api/static_frontend.py README.md
git diff --check
```

Expected: ripgrep returns no matches and `git diff --check` returns no output.

- [ ] **Step 5: Rebuild and smoke the final foundation artifact**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-portable.ps1 -SkipTests
powershell -ExecutionPolicy Bypass -File .\scripts\run-portable-smoke.ps1
```

Expected: build and smoke pass, `dist/XiaoQiBao-Portable/xiaoqibao.exe` exists and no process remains.

- [ ] **Step 6: Record the phase result without staging unrelated files**

```powershell
git status --short
git log -6 --oneline
```

Expected: the phase commits are visible; existing unrelated dirty files remain untouched and unstaged.
