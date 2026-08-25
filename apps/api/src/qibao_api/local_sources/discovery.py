import ctypes
import os
from collections.abc import Callable, Iterable
from ctypes import wintypes
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from qibao_api.local_sources.models import LocalSourceSettings
from qibao_api.gongbu.tdx_directory_discovery import (
    _inspect_root,
    rank_tdx_directories,
)


Vendor = Literal["tdx", "ths"]
Origin = Literal["manual", "process", "registry", "common"]


class SystemCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    vendor: Vendor
    path: Path
    origin: Literal["process", "registry", "common"]


class LocalTerminalStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    vendor: Vendor
    install_path: Path
    data_path: Path | None
    origin: Origin
    status: Literal["ready", "detected_only", "invalid"]
    sh_daily_count: int = 0
    sz_daily_count: int = 0
    latest_modified_at: datetime | None = None
    professional_data_status: Literal["ready", "detected_only", "unavailable"] = "unavailable"
    professional_data_files: tuple[str, ...] = ()
    selection_eligible: bool = True
    selection_note: str | None = None
    latest_trade_date: date | None = None
    day_file_count: int = 0
    readable_day_file_count: int = 0
    a_share_coverage_percent: float = 0.0
    source_score: float = 0.0
    source_reasons: tuple[str, ...] = ()


class LocalTerminalDiscoveryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    scanned_at: datetime
    terminals: tuple[LocalTerminalStatus, ...]
    active_tdx_vipdoc: Path | None
    settings: LocalSourceSettings | None = None


class LocalTerminalDiscoveryState:
    """Mutable reference used by long-lived services after a background rescan."""

    def __init__(self, current: LocalTerminalDiscoveryResult) -> None:
        self.current = current

    @property
    def terminals(self) -> tuple[LocalTerminalStatus, ...]:
        return self.current.terminals

    @property
    def active_tdx_vipdoc(self) -> Path | None:
        return self.current.active_tdx_vipdoc

    def update(self, current: LocalTerminalDiscoveryResult) -> None:
        self.current = current


def running_tdx_process_paths() -> tuple[Path, ...]:
    """Return executable paths for currently running TDX desktop clients.

    Process presence is deliberately reported separately from data-directory
    discovery and JSON-RPC reachability.  A running ``TdxW.exe`` alone does
    not prove that the read-only bridge is listening or that professional
    tables are available.
    """
    if os.name != "nt":
        return ()
    return tuple(
        path
        for path in _running_process_paths()
        if path.name.casefold() in {"tdxw.exe", "tdx.exe"}
    )


class LocalTerminalDiscovery:
    def __init__(
        self,
        *,
        system_candidates: Callable[[], Iterable[SystemCandidate]] | None = None,
        known_paths: Iterable[Path] = (),
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.system_candidates = system_candidates or discover_system_candidates
        self.known_paths = tuple(Path(path).expanduser().resolve(strict=False) for path in known_paths)
        self.clock = clock

    def inspect(self, settings: LocalSourceSettings) -> LocalTerminalDiscoveryResult:
        candidates: list[tuple[Vendor, Path, Origin]] = [
            *(('tdx', path, 'manual') for path in settings.tdx_install_paths),
            *(('ths', path, 'manual') for path in settings.ths_install_paths),
        ]
        if settings.auto_discovery:
            candidates.extend(
                ("tdx", path, "manual")
                for path in self.known_paths
                if path.exists()
            )
            candidates.extend(
                (item.vendor, item.path, item.origin)
                for item in self.system_candidates()
            )

        terminals = []
        seen = set()
        for vendor, path, origin in candidates:
            terminal = (
                _inspect_tdx(path, origin)
                if vendor == "tdx"
                else _inspect_ths(path, origin)
            )
            key_path = terminal.data_path or terminal.install_path
            key = (terminal.vendor, str(key_path).casefold())
            if key in seen:
                continue
            seen.add(key)
            terminals.append(terminal)
        tdx_terminals = [
            item for item in terminals
            if item.vendor == "tdx" and item.status == "ready" and item.data_path is not None
        ]
        ranked_by_root = {}
        if tdx_terminals:
            evidence = rank_tdx_directories(
                tuple(_inspect_root(item.install_path, ()) for item in tdx_terminals)
            )
            ranked_by_root = {str(item.root).casefold(): item for item in evidence}
            for index, item in enumerate(terminals):
                if item.vendor != "tdx" or item.data_path is None:
                    continue
                candidate = ranked_by_root.get(str(item.install_path).casefold())
                if candidate is None:
                    continue
                terminals[index] = item.model_copy(update={
                    "latest_trade_date": candidate.latest_trade_date,
                    "day_file_count": candidate.day_file_count,
                    "readable_day_file_count": candidate.readable_day_file_count,
                    "a_share_coverage_percent": candidate.a_share_coverage_percent,
                    "source_score": candidate.score,
                    "source_reasons": candidate.reasons,
                })
        eligible = [
            item for item in terminals
            if item.vendor == "tdx" and item.status == "ready" and item.selection_eligible
        ]
        has_scoring_evidence = any(item.readable_day_file_count > 0 for item in eligible)
        ranked_eligible = sorted(
            eligible,
            key=lambda item: (
                0 if (not has_scoring_evidence and item.origin == "manual") else 1,
                -item.source_score,
                -(item.latest_trade_date.toordinal() if item.latest_trade_date else 0),
                -item.readable_day_file_count,
                str(item.install_path).casefold(),
            ),
        )
        active = (ranked_eligible[0].data_path if ranked_eligible else None)
        return LocalTerminalDiscoveryResult(
            scanned_at=self.clock(),
            terminals=tuple(terminals),
            active_tdx_vipdoc=active,
            settings=settings,
        )

    def inspect_configured(self, settings: LocalSourceSettings) -> LocalTerminalDiscoveryResult:
        """Inspect only explicitly configured paths without system discovery.

        Startup can use this bounded check to expose a known local data source
        immediately.  Automatic process/registry/common-directory discovery
        remains on the background refresh path.
        """
        if settings.auto_discovery:
            raise ValueError("configured inspection requires auto_discovery=False")
        return self.inspect(settings)


def _inspect_tdx(path: Path, origin: Origin) -> LocalTerminalStatus:
    resolved = path.resolve(strict=False)
    if resolved.name.casefold() == "vipdoc":
        install_path = resolved.parent
        data_path = resolved
    else:
        install_path = resolved
        data_path = resolved / "vipdoc"
    sh_folder = data_path / "sh" / "lday"
    sz_folder = data_path / "sz" / "lday"
    if not sh_folder.is_dir() or not sz_folder.is_dir():
        return LocalTerminalStatus(
            vendor="tdx",
            install_path=install_path,
            data_path=None,
            origin=origin,
            status="invalid",
        )
    selection_eligible, selection_note = _tdx_selection_policy(
        install_path, origin
    )
    sh_files = tuple(sh_folder.glob("*.day"))
    sz_files = tuple(sz_folder.glob("*.day"))
    modified = [
        value
        for path_item in (*sh_files, *sz_files)
        if (value := _modified_at(path_item)) is not None
    ]
    professional_status, professional_files = _inspect_tdx_professional_cache(install_path)
    return LocalTerminalStatus(
        vendor="tdx",
        install_path=install_path,
        data_path=data_path,
        origin=origin,
        status="ready",
        sh_daily_count=len(sh_files),
        sz_daily_count=len(sz_files),
        latest_modified_at=max(modified, default=None),
        professional_data_status=professional_status,
        professional_data_files=professional_files,
        selection_eligible=selection_eligible,
        selection_note=selection_note,
    )


def _inspect_tdx_professional_cache(
    install_path: Path,
) -> tuple[Literal["ready", "detected_only", "unavailable"], tuple[str, ...]]:
    """Detect known local TDX professional-cache files without reading them.

    These files prove that a terminal cache exists, not that the JSON-RPC bridge
    can expose its tables.  Keep the state as ``detected_only`` until a read-only
    bridge call returns validated rows; never claim financial fields are ready
    from filenames alone.
    """
    relative_files = (
        "base.dbf",
        "shs.tnf",
        "szs.tnf",
        "sh.th2",
        "sz.th2",
        "gbbq",
    )
    cache = install_path / "T0002" / "hq_cache"
    detected = tuple(name for name in relative_files if (cache / name).is_file())
    if not detected:
        return "unavailable", ()
    return "detected_only", detected


def _tdx_selection_policy(path: Path, origin: Origin) -> tuple[bool, str | None]:
    """Keep auto-discovery from selecting directories that look synthetic.

    A manually entered path is an explicit user decision and remains eligible.
    Automatic discovery excludes only an install-directory name containing a
    clear test fixture marker; parent folders are ignored because temporary
    test runners and normal user folders can legitimately contain ``test``.
    """
    if origin == "manual":
        return True, None
    name = path.name.casefold()
    markers = ("mock", "fixture", "sample", "demo", "fake")
    if any(marker in name for marker in markers):
        return False, "自动发现已排除疑似测试/示例数据目录；如需使用请手工添加此目录"
    return True, None


def _inspect_ths(path: Path, origin: Origin) -> LocalTerminalStatus:
    resolved = path.resolve(strict=False)
    if resolved.is_file():
        resolved = resolved.parent
    executable_paths = (
        "hexin.exe",
        "hexinlauncher.exe",
        "happ.exe",
        "xiadan.exe",
        "ths.exe",
        "bin/hexin.exe",
        "bin/hexinlauncher.exe",
        "bin/happ.exe",
        "transaction/xiadan.exe",
    )
    detected = resolved.is_dir() and any(
        (resolved / relative).is_file() for relative in executable_paths
    )
    return LocalTerminalStatus(
        vendor="ths",
        install_path=resolved,
        data_path=None,
        origin=origin,
        status="detected_only" if detected else "invalid",
    )


def _modified_at(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def discover_system_candidates() -> tuple[SystemCandidate, ...]:
    values = [*_process_candidates(), *_registry_candidates(), *_common_candidates()]
    result = []
    seen = set()
    for item in values:
        key = (item.vendor, str(item.path.resolve(strict=False)).casefold())
        if key not in seen:
            seen.add(key)
            result.append(item)
    return tuple(result)


def _process_candidates() -> tuple[SystemCandidate, ...]:
    result = []
    for executable in _running_process_paths():
        name = executable.name.casefold()
        if name in {"tdxw.exe", "tdx.exe"}:
            result.append(SystemCandidate(
                vendor="tdx", path=executable.parent, origin="process"
            ))
        elif name in {
            "hexin.exe", "hexinlauncher.exe", "happ.exe", "xiadan.exe", "ths.exe"
        }:
            result.append(SystemCandidate(
                vendor="ths", path=executable.parent, origin="process"
            ))
    return tuple(result)


def _running_process_paths() -> tuple[Path, ...]:
    if os.name != "nt":
        return ()

    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if snapshot == invalid_handle:
        return ()
    entry = ProcessEntry()
    entry.dwSize = ctypes.sizeof(entry)
    targets = {"tdxw.exe", "tdx.exe", "hexin.exe", "xiadan.exe", "ths.exe"}
    paths = []
    try:
        has_entry = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while has_entry:
            if entry.szExeFile.casefold() in targets:
                process = kernel32.OpenProcess(0x1000, False, entry.th32ProcessID)
                if process:
                    try:
                        size = wintypes.DWORD(32768)
                        buffer = ctypes.create_unicode_buffer(size.value)
                        if kernel32.QueryFullProcessImageNameW(
                            process, 0, buffer, ctypes.byref(size)
                        ):
                            paths.append(Path(buffer.value))
                    finally:
                        kernel32.CloseHandle(process)
            has_entry = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return tuple(paths)


def _registry_candidates() -> tuple[SystemCandidate, ...]:
    if os.name != "nt":
        return ()
    try:
        import winreg
    except ImportError:
        return ()

    result = []
    uninstall = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for access in (winreg.KEY_READ, winreg.KEY_READ | winreg.KEY_WOW64_32KEY):
            try:
                key = winreg.OpenKey(hive, uninstall, 0, access)
            except OSError:
                continue
            with key:
                for index in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        child = winreg.OpenKey(key, winreg.EnumKey(key, index))
                        with child:
                            name = str(winreg.QueryValueEx(child, "DisplayName")[0])
                            location = str(winreg.QueryValueEx(child, "InstallLocation")[0])
                    except OSError:
                        continue
                    vendor = _name_vendor(name)
                    if vendor is not None and location.strip():
                        result.append(SystemCandidate(
                            vendor=vendor,
                            path=Path(location.strip().strip('"')),
                            origin="registry",
                        ))
    return tuple(result)


def _common_candidates() -> tuple[SystemCandidate, ...]:
    roots = {
        Path(value)
        for key in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")
        if (value := os.environ.get(key))
    }
    result = []
    for root in roots:
        try:
            children = tuple(path for path in root.iterdir() if path.is_dir())
        except OSError:
            continue
        for child in children:
            vendor = _name_vendor(child.name)
            if vendor is not None:
                result.append(SystemCandidate(
                    vendor=vendor, path=child, origin="common"
                ))
    return tuple(result)


def _name_vendor(value: str) -> Vendor | None:
    name = value.casefold()
    if any(token in name for token in ("通达信", "tongdaxin", "new_tdx", "tdx")):
        return "tdx"
    if any(token in name for token in ("同花顺", "tonghuashun", "hexin", "ths")):
        return "ths"
    return None
