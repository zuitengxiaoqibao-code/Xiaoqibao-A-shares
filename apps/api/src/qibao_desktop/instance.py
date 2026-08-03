import ctypes
import sys
from ctypes import wintypes


ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9


class AlreadyRunningError(RuntimeError):
    pass


def _user32():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
    user32.FindWindowW.restype = wintypes.HWND
    user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.ShowWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = (wintypes.HWND,)
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    user32.SetForegroundWindow.restype = wintypes.BOOL
    return user32


def activate_existing_window(title: str) -> bool:
    if sys.platform != "win32":
        return False
    user32 = _user32()
    window = user32.FindWindowW(None, title)
    if not window:
        return False
    user32.ShowWindow(window, SW_RESTORE)
    user32.BringWindowToTop(window)
    return bool(user32.SetForegroundWindow(window))


class SingleInstance:
    def __init__(self, name: str) -> None:
        self.name = name
        self._handle = None

    @staticmethod
    def _kernel32():
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        return kernel32

    def acquire(self) -> None:
        if self._handle is not None:
            return
        if sys.platform != "win32":
            raise RuntimeError("desktop single-instance lock requires Windows")
        kernel32 = self._kernel32()
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
        kernel32 = self._kernel32()
        kernel32.ReleaseMutex(self._handle)
        kernel32.CloseHandle(self._handle)
        self._handle = None

    def __enter__(self) -> "SingleInstance":
        self.acquire()
        return self

    def __exit__(self, *_args) -> None:
        self.close()
