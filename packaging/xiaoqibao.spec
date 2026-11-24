from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata


spec_dir = Path(SPECPATH)
project_root = spec_dir.parent
api_src = project_root / "apps" / "api" / "src"
icon_path = project_root / "packaging" / "assets" / "xiaoqibao.ico"
splash_path = project_root / "packaging" / "assets" / "xiaoqibao-splash.png"

# The desktop entrypoint imports its local modules statically.  The API is
# loaded by Uvicorn from the string ``qibao_api.main:app``, so keep only that
# explicit dynamic root instead of archiving every module under both packages.
# PyInstaller follows the import graph from this root and still includes all
# routers and services that the application actually imports.
hiddenimports = [
    "qibao_api.main",
    # pywebview selects the Windows backend dynamically at runtime.  Keep
    # only the backend and renderer branches used by this desktop build.
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "webview.platforms.mshtml",
    "webview.platforms.win32",
    # LocalApiServer pins these Uvicorn implementations explicitly.
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.lifespan.on",
    # mootdx is used only through its Quotes client; tools/downloaders are
    # not part of the application runtime.
    "mootdx.quotes",
    "eltdx._native",
    "axdata_core.adapters.tencent.request",
]
datas = (collect_data_files("exchange_calendars") + collect_data_files("webview")
         + collect_data_files("eltdx") + copy_metadata("eltdx") + copy_metadata("axdata"))

a = Analysis(
    [str(api_src / "qibao_desktop" / "__main__.py")],
    pathex=[str(api_src)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "pytest",
        "hypothesis",
        # Windows desktop builds use WinForms + Edge WebView2 only.
        "webview.platforms.android",
        "webview.platforms.cocoa",
        "webview.platforms.gtk",
        "webview.platforms.qt",
        "webview.platforms.cef",
        # TDX daily/quote reads do not use downloader or F10 tool helpers.
        "mootdx.tools",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
splash = Splash(
    str(splash_path),
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    minify_script=True,
    always_on_top=True,
    max_img_size=(480, 480),
    center="active",
)
exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    exclude_binaries=True,
    name="xiaoqibao",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon_path),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    splash.binaries,
    strip=False,
    upx=False,
    name="XiaoQiBao-Portable",
)
