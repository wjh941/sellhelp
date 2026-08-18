import ctypes
import secrets
from pathlib import Path


_SECRET_FILE = "jwt-secret.bin"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _free_dpapi_buffer(data: _DataBlob) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    kernel32.LocalFree(data.pbData)


def _crypt_protect(data: bytes) -> bytes:
    if not hasattr(ctypes, "WinDLL"):
        raise OSError("Desktop JWT secrets require Windows DPAPI")
    source_buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    source = _DataBlob(len(data), source_buffer)
    encrypted = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob), ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = ctypes.c_bool
    if not crypt32.CryptProtectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(encrypted)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(encrypted.pbData, encrypted.cbData)
    finally:
        _free_dpapi_buffer(encrypted)


def _crypt_unprotect(data: bytes) -> bytes:
    if not hasattr(ctypes, "WinDLL"):
        raise OSError("Desktop JWT secrets require Windows DPAPI")
    source_buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    source = _DataBlob(len(data), source_buffer)
    decrypted = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob), ctypes.POINTER(ctypes.c_wchar_p), ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = ctypes.c_bool
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(decrypted)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(decrypted.pbData, decrypted.cbData)
    finally:
        _free_dpapi_buffer(decrypted)


def load_desktop_jwt_secret(config_dir: Path) -> str:
    return _crypt_unprotect((config_dir / _SECRET_FILE).read_bytes()).decode("utf-8")


def ensure_desktop_jwt_secret(config_dir: Path) -> str:
    secret_path = config_dir / _SECRET_FILE
    if secret_path.exists():
        return load_desktop_jwt_secret(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_urlsafe(48)
    secret_path.write_bytes(_crypt_protect(secret.encode("utf-8")))
    return secret
