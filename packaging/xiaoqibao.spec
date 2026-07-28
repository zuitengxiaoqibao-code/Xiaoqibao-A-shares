from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


spec_dir = Path(SPECPATH)
project_root = spec_dir.parent
api_src = project_root / "apps" / "api" / "src"
icon_path = project_root / "packaging" / "assets" / "xiaoqibao.ico"

hiddenimports = (
    collect_submodules("qibao_api")
    + collect_submodules("qibao_desktop")
    + collect_submodules("mootdx")
    + collect_submodules("uvicorn")
    + collect_submodules("webview")
)
datas = collect_data_files("exchange_calendars") + collect_data_files("webview")

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
    icon=str(icon_path),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="XiaoQiBao-Portable",
)
