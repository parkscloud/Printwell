"""OLE drag-and-drop target using ctypes (bypasses pywin32 COM gateway).

Handles both Explorer file drops (CF_HDROP) and Outlook attachment drops
(FileGroupDescriptorW / FileContents virtual-file protocol).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import logging
import struct
import tempfile
from ctypes import HRESULT, POINTER, WINFUNCTYPE, byref, c_ulong, c_void_p
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

# ------------------------------------------------------------------ Win32 / COM constants
S_OK = 0
E_NOINTERFACE = 0x80004002

DROPEFFECT_NONE = 0
DROPEFFECT_COPY = 1

CF_HDROP = 15
DVASPECT_CONTENT = 1
TYMED_HGLOBAL = 1
TYMED_ISTREAM = 4

_ole32 = ctypes.windll.ole32
_shell32 = ctypes.windll.shell32
_kernel32 = ctypes.windll.kernel32

_kernel32.GlobalLock.restype = c_void_p
_kernel32.GlobalLock.argtypes = [c_void_p]
_kernel32.GlobalUnlock.argtypes = [c_void_p]
_kernel32.GlobalSize.restype = ctypes.c_size_t
_kernel32.GlobalSize.argtypes = [c_void_p]

_ole32.OleInitialize.argtypes = [c_void_p]
_ole32.OleInitialize.restype = HRESULT
_ole32.RegisterDragDrop.argtypes = [wt.HWND, c_void_p]
_ole32.RegisterDragDrop.restype = HRESULT
_shell32.DragQueryFileW.argtypes = [c_void_p, wt.UINT, ctypes.c_wchar_p, wt.UINT]
_shell32.DragQueryFileW.restype = wt.UINT

# Outlook clipboard formats (lazily registered)
_cf_filedescriptorw: int | None = None
_cf_filecontents: int | None = None


def _outlook_format_ids() -> tuple[int, int]:
    global _cf_filedescriptorw, _cf_filecontents
    if _cf_filedescriptorw is None:
        reg = ctypes.windll.user32.RegisterClipboardFormatW
        _cf_filedescriptorw = reg("FileGroupDescriptorW")
        _cf_filecontents = reg("FileContents")
    return _cf_filedescriptorw, _cf_filecontents


# ------------------------------------------------------------------ COM structures

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


IID_IUnknown = GUID(0x00000000, 0x0000, 0x0000,
                     (ctypes.c_ubyte * 8)(0xC0, 0, 0, 0, 0, 0, 0, 0x46))
IID_IDropTarget = GUID(0x00000122, 0x0000, 0x0000,
                       (ctypes.c_ubyte * 8)(0xC0, 0, 0, 0, 0, 0, 0, 0x46))


class POINTL(ctypes.Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG)]


class FORMATETC(ctypes.Structure):
    _fields_ = [
        ("cfFormat", wt.WORD),
        ("ptd", c_void_p),
        ("dwAspect", wt.DWORD),
        ("lindex", wt.LONG),
        ("tymed", wt.DWORD),
    ]


class STGMEDIUM(ctypes.Structure):
    _fields_ = [
        ("tymed", wt.DWORD),
        ("data", c_void_p),
        ("pUnkForRelease", c_void_p),
    ]


_ole32.ReleaseStgMedium.argtypes = [POINTER(STGMEDIUM)]
_ole32.ReleaseStgMedium.restype = None


# ------------------------------------------------------------------ vtable types

_QI = WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), POINTER(c_void_p))
_ADDREF = WINFUNCTYPE(c_ulong, c_void_p)
_RELEASE = WINFUNCTYPE(c_ulong, c_void_p)
_DRAGENTER = WINFUNCTYPE(HRESULT, c_void_p, c_void_p, wt.DWORD, POINTL,
                         POINTER(wt.DWORD))
_DRAGOVER = WINFUNCTYPE(HRESULT, c_void_p, wt.DWORD, POINTL,
                        POINTER(wt.DWORD))
_DRAGLEAVE = WINFUNCTYPE(HRESULT, c_void_p)
_DROP = WINFUNCTYPE(HRESULT, c_void_p, c_void_p, wt.DWORD, POINTL,
                    POINTER(wt.DWORD))


class _IDropTargetVtbl(ctypes.Structure):
    _fields_ = [
        ("QueryInterface", _QI),
        ("AddRef", _ADDREF),
        ("Release", _RELEASE),
        ("DragEnter", _DRAGENTER),
        ("DragOver", _DRAGOVER),
        ("DragLeave", _DRAGLEAVE),
        ("Drop", _DROP),
    ]


class _IDropTargetObj(ctypes.Structure):
    _fields_ = [("lpVtbl", POINTER(_IDropTargetVtbl))]


# ------------------------------------------------------------------ IDataObject helpers

# IDataObject::GetData is vtable slot 3
_IDATAOBJECT_GETDATA = WINFUNCTYPE(HRESULT, c_void_p, POINTER(FORMATETC),
                                   POINTER(STGMEDIUM))
# IDataObject::QueryGetData is vtable slot 5
_IDATAOBJECT_QUERYGETDATA = WINFUNCTYPE(HRESULT, c_void_p, POINTER(FORMATETC))

# IStream::Read is vtable slot 3
_ISTREAM_READ = WINFUNCTYPE(HRESULT, c_void_p, c_void_p, c_ulong,
                            POINTER(c_ulong))


def _vtable_method(com_ptr: int, slot: int):
    """Return a raw function pointer from a COM object's vtable."""
    vtbl_ptr = ctypes.cast(com_ptr, POINTER(c_void_p))[0]
    fn_ptr = ctypes.cast(vtbl_ptr, POINTER(c_void_p * (slot + 1)))[0][slot]
    return fn_ptr


def _data_obj_query(data_obj_ptr: int, cf: int) -> bool:
    """Check if the data object supports a clipboard format."""
    fn = _IDATAOBJECT_QUERYGETDATA(_vtable_method(data_obj_ptr, 5))
    fmt = FORMATETC(cfFormat=cf, ptd=None, dwAspect=DVASPECT_CONTENT,
                    lindex=-1, tymed=TYMED_HGLOBAL)
    try:
        return fn(data_obj_ptr, byref(fmt)) == S_OK
    except OSError:
        return False


def _data_obj_get(data_obj_ptr: int, cf: int, lindex: int = -1,
                  tymed: int = TYMED_HGLOBAL) -> STGMEDIUM | None:
    """Call IDataObject::GetData and return the STGMEDIUM, or None."""
    fn = _IDATAOBJECT_GETDATA(_vtable_method(data_obj_ptr, 3))
    fmt = FORMATETC(cfFormat=cf, ptd=None, dwAspect=DVASPECT_CONTENT,
                    lindex=lindex, tymed=tymed)
    medium = STGMEDIUM()
    try:
        hr = fn(data_obj_ptr, byref(fmt), byref(medium))
    except OSError:
        return None
    return medium if hr == S_OK else None


def _read_hglobal(hglobal: int) -> bytes:
    """Lock an HGLOBAL, copy its contents, and unlock."""
    size = _kernel32.GlobalSize(hglobal)
    ptr = _kernel32.GlobalLock(hglobal)
    if not ptr:
        return b""
    try:
        return ctypes.string_at(ptr, size)
    finally:
        _kernel32.GlobalUnlock(hglobal)


def _read_istream(stream_ptr: int) -> bytes:
    """Read all bytes from a COM IStream."""
    read_fn = _ISTREAM_READ(_vtable_method(stream_ptr, 3))
    chunks: list[bytes] = []
    buf = ctypes.create_string_buffer(65536)
    while True:
        cb_read = c_ulong(0)
        hr = read_fn(stream_ptr, buf, 65536, byref(cb_read))
        if cb_read.value == 0:
            break
        chunks.append(buf.raw[: cb_read.value])
        if hr != S_OK:
            break
    return b"".join(chunks)


def _release_stgmedium(medium: STGMEDIUM) -> None:
    _ole32.ReleaseStgMedium(byref(medium))


# ----------------------------------------------------------- file extraction

def _try_hdrop(data_obj_ptr: int) -> Path | None:
    """Get the first file path from a CF_HDROP drop (Explorer)."""
    medium = _data_obj_get(data_obj_ptr, CF_HDROP)
    if medium is None:
        return None
    try:
        hdrop = medium.data
        count = _shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        if count < 1:
            return None
        buf = ctypes.create_unicode_buffer(260)
        _shell32.DragQueryFileW(hdrop, 0, buf, 260)
        return Path(buf.value) if buf.value else None
    finally:
        _release_stgmedium(medium)


def _try_outlook(data_obj_ptr: int) -> Path | None:
    """Extract the first Outlook virtual-file attachment."""
    cf_desc, cf_contents = _outlook_format_ids()

    # 1. Get filename from FileGroupDescriptorW
    medium_desc = _data_obj_get(data_obj_ptr, cf_desc)
    if medium_desc is None:
        return None
    try:
        raw = _read_hglobal(medium_desc.data)
        filename = _parse_filegroupdescriptor_w(raw)
        if not filename:
            return None
    finally:
        _release_stgmedium(medium_desc)

    # 2. Get file contents (try HGLOBAL first, then IStream)
    file_bytes: bytes | None = None
    medium_body = _data_obj_get(data_obj_ptr, cf_contents, lindex=0,
                                tymed=TYMED_HGLOBAL | TYMED_ISTREAM)
    if medium_body is None:
        return None
    try:
        if medium_body.tymed == TYMED_HGLOBAL:
            file_bytes = _read_hglobal(medium_body.data)
        elif medium_body.tymed == TYMED_ISTREAM and medium_body.data:
            file_bytes = _read_istream(medium_body.data)
    finally:
        _release_stgmedium(medium_body)

    if not file_bytes:
        return None

    # 3. Write to temp
    temp_dir = Path(tempfile.gettempdir()) / "Printwell"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / filename
    temp_path.write_bytes(file_bytes)
    log.info("Extracted Outlook attachment to %s", temp_path)
    return temp_path


def _parse_filegroupdescriptor_w(data: bytes) -> str | None:
    """Return the first filename from a FILEGROUPDESCRIPTORW blob."""
    if len(data) < 4:
        return None
    count = struct.unpack_from("<I", data, 0)[0]
    if count < 1:
        return None
    # cFileName is at offset 72 inside each FILEDESCRIPTORW
    name_offset = 4 + 72
    name_bytes = data[name_offset: name_offset + 520]  # WCHAR[260]
    return name_bytes.decode("utf-16-le").split("\0")[0] or None


# ------------------------------------------------------------------ drop target

class FileDropTarget:
    """OLE IDropTarget implemented with ctypes (no pywin32 gateway)."""

    def __init__(self, callback: Callable[[Path], None]) -> None:
        self._callback = callback
        self._can_drop = False
        self._ref_count = 1

        # Build the COM object: a struct whose first field is a vtable pointer.
        # The ctypes callback objects must be kept alive for the life of the
        # drop target, so we store them as instance attributes.
        self._qi_cb = _QI(self._QueryInterface)
        self._addref_cb = _ADDREF(self._AddRef)
        self._release_cb = _RELEASE(self._Release)
        self._dragenter_cb = _DRAGENTER(self._DragEnter)
        self._dragover_cb = _DRAGOVER(self._DragOver)
        self._dragleave_cb = _DRAGLEAVE(self._DragLeave)
        self._drop_cb = _DROP(self._Drop)

        self._vtbl = _IDropTargetVtbl(
            QueryInterface=self._qi_cb,
            AddRef=self._addref_cb,
            Release=self._release_cb,
            DragEnter=self._dragenter_cb,
            DragOver=self._dragover_cb,
            DragLeave=self._dragleave_cb,
            Drop=self._drop_cb,
        )
        self._obj = _IDropTargetObj(lpVtbl=ctypes.pointer(self._vtbl))

    @property
    def com_ptr(self) -> int:
        """Raw pointer to the COM object (for RegisterDragDrop)."""
        return ctypes.addressof(self._obj)

    # ----- IUnknown

    def _QueryInterface(self, this, riid, ppv):
        iid = riid[0]
        if (_guid_eq(iid, IID_IUnknown) or _guid_eq(iid, IID_IDropTarget)):
            ppv[0] = this
            self._ref_count += 1
            return S_OK
        ppv[0] = None
        return E_NOINTERFACE

    def _AddRef(self, this):
        self._ref_count += 1
        return self._ref_count

    def _Release(self, this):
        self._ref_count -= 1
        return self._ref_count

    # ----- IDropTarget

    def _DragEnter(self, this, pDataObj, grfKeyState, pt, pdwEffect):
        try:
            self._can_drop = (
                _data_obj_query(pDataObj, CF_HDROP)
                or _data_obj_query(pDataObj, _outlook_format_ids()[0])
            )
        except Exception:
            self._can_drop = False
        pdwEffect[0] = DROPEFFECT_COPY if self._can_drop else DROPEFFECT_NONE
        return S_OK

    def _DragOver(self, this, grfKeyState, pt, pdwEffect):
        pdwEffect[0] = DROPEFFECT_COPY if self._can_drop else DROPEFFECT_NONE
        return S_OK

    def _DragLeave(self, this):
        self._can_drop = False
        return S_OK

    def _Drop(self, this, pDataObj, grfKeyState, pt, pdwEffect):
        try:
            path = _try_hdrop(pDataObj) or _try_outlook(pDataObj)
            if path is not None:
                self._callback(path)
                pdwEffect[0] = DROPEFFECT_COPY
            else:
                pdwEffect[0] = DROPEFFECT_NONE
        except Exception:
            log.error("Error handling drop", exc_info=True)
            pdwEffect[0] = DROPEFFECT_NONE
        return S_OK


def _guid_eq(a: GUID, b: GUID) -> bool:
    return (a.Data1 == b.Data1 and a.Data2 == b.Data2
            and a.Data3 == b.Data3
            and bytes(a.Data4) == bytes(b.Data4))


# ----------------------------------------------------------- public API

def register_drop_target(
    hwnd: int,
    callback: Callable[[Path], None],
) -> FileDropTarget | None:
    """Register an OLE drop target on *hwnd*.

    Returns the target (caller must prevent GC) or ``None`` on failure.
    """
    try:
        _ole32.OleInitialize(None)
    except OSError:
        pass

    try:
        target = FileDropTarget(callback)
        hr = _ole32.RegisterDragDrop(hwnd, target.com_ptr)
        if hr != S_OK:
            log.warning("RegisterDragDrop returned 0x%08X", hr & 0xFFFFFFFF)
            return None
        log.info("OLE drop target registered on HWND %s", hwnd)
        return target
    except Exception:
        log.warning("Failed to register OLE drop target", exc_info=True)
        return None
