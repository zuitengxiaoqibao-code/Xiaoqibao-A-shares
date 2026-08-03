import base64
import binascii
import ctypes
import os
from ctypes import wintypes
from typing import Protocol


class CredentialProtector(Protocol):
    def protect(self, value: str) -> str: ...

    def unprotect(self, value: str) -> str: ...


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD),
        ("data", ctypes.POINTER(ctypes.c_ubyte)),
    ]


class WindowsDPAPICredentialProtector:
    PREFIX = "dpapi-user-v1:"
    UI_FORBIDDEN = 0x1

    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("Windows DPAPI is unavailable on this platform")
        self._crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._crypt32.CryptProtectData.restype = wintypes.BOOL
        self._crypt32.CryptUnprotectData.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
        self._kernel32.LocalFree.restype = ctypes.c_void_p

    @staticmethod
    def _input_blob(value: bytes) -> tuple[_DataBlob, ctypes.Array]:
        buffer = ctypes.create_string_buffer(value)
        pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        return _DataBlob(len(value), pointer), buffer

    def _release(self, blob: _DataBlob) -> None:
        if blob.data:
            self._kernel32.LocalFree(ctypes.cast(blob.data, ctypes.c_void_p))

    def protect(self, value: str) -> str:
        input_blob, input_buffer = self._input_blob(value.encode("utf-8"))
        output_blob = _DataBlob()
        success = self._crypt32.CryptProtectData(
            ctypes.byref(input_blob),
            None,
            None,
            None,
            None,
            self.UI_FORBIDDEN,
            ctypes.byref(output_blob),
        )
        _ = input_buffer
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            encrypted = ctypes.string_at(output_blob.data, output_blob.size)
            return self.PREFIX + base64.b64encode(encrypted).decode("ascii")
        finally:
            self._release(output_blob)

    def unprotect(self, value: str) -> str:
        if not value.startswith(self.PREFIX):
            raise ValueError("unsupported protected credential format")
        try:
            encrypted = base64.b64decode(
                value.removeprefix(self.PREFIX), validate=True
            )
        except (ValueError, binascii.Error) as exc:
            raise ValueError("invalid protected credential") from exc
        input_blob, input_buffer = self._input_blob(encrypted)
        output_blob = _DataBlob()
        success = self._crypt32.CryptUnprotectData(
            ctypes.byref(input_blob),
            None,
            None,
            None,
            None,
            self.UI_FORBIDDEN,
            ctypes.byref(output_blob),
        )
        _ = input_buffer
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return ctypes.string_at(output_blob.data, output_blob.size).decode("utf-8")
        finally:
            self._release(output_blob)


def default_credential_protector() -> CredentialProtector | None:
    return WindowsDPAPICredentialProtector() if os.name == "nt" else None
