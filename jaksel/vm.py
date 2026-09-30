"""JakselScript VM: kompiler bytecode + mesin virtual stack.

Arsitektur
---------
Kode sumber JakselScript (.jaksel) -> :class:`Compiler` -> :class:`CodeUnit`
(daftar instruksi bytecode) -> :class:`VM` (mesin stack yang mengeksekusinya).

Model objek dipakai bareng transpiler: kelas JakselScript diwujudkan sebagai
kelas Python asli turunan ``_JakselBase`` — warisan, MRO, ``super()``,
``property``, dan ``staticmethod`` semuanya gratis dari Python. Method
disimpan sebagai :class:`FungsiVM` yang mengimplementasikan protokol
descriptor (``__get__``) supaya ``obj.metode`` otomatis terikat ke ``ini``.

Bytecode bisa disimpan ke file ``.jsc`` (via :func:`simpan_jsc`) dan
dimuat lagi (via :func:`muat_jsc`) tanpa perlu kode sumber aslinya.

Penggunaan
----------
    from jaksel.vm import kompilasi, VM
    unit = kompilasi(sumber, nama_file="program.jaksel")
    vm = VM()
    vm.jalankan(unit)
"""

import marshal
import os

from .errors import JakselError
from .interpreter import (
    Interpreter,
    BuiltinFunction,
    JakselTugas,
    JakselPyModul,
    JakselPyObj,
    JakselPyCallable,
    _Exit,
    _py_ke_jaksel,
    _METHODS,
    _tipe_method,
    is_truthy,
    format_value,
    mirip,
)
from .transpiler import transpile_file  # noqa: F401 (transpiler tetap tersedia)

# ---------------------------------------------------------------------------
# Runtime mini VM.
#
# Helper di bawah ini mereplikasi semantik helper runtime milik transpiler
# (yang hidup di dalam string HEADER transpiler.py, jadi tidak bisa diimpor)
# dan interpreter. Bedanya: semua error di sini berupa JakselError supaya
# seragam dengan sisa VM.
# ---------------------------------------------------------------------------

class _JakselBase:
    """Kelas dasar semua kelas JakselScript yang berjalan di VM."""

    def __init__(self, *a):
        if a:
            raise JakselError(
                "kelas '%s' nggak punya 'lahir' tapi dipanggil pakai "
                "argumen, bestie." % type(self).__name__)


class _EnumBase:
    """Marker kelas enum hasil 'pilihan'."""


class _EnumMember:
    """Satu anggota enum, mis. Warna.MERAH."""

    def __init__(self, enum_name, member_name, value):
        self._enum = enum_name
        self._member = member_name
        self.value = value

    def __repr__(self):
        return "%s.%s" % (self._enum, self._member)


class _Modul:
    """Namespace hasil 'collab ... sebagai nama'."""

    def __init__(self, nama, ns):
        self._nama = nama
        self.__dict__.update(ns)

    def __repr__(self):
        return "<modul %s>" % self._nama


def _tname(v):
    if v is None:
        return "zonk"
    if isinstance(v, bool):
        return "valid/gimmick"
    if isinstance(v, int):
        return "angka bulat"
    if isinstance(v, float):
        return "angka desimal"
    if isinstance(v, str):
        return "teks"
    if isinstance(v, list):
        return "daftar"
    if isinstance(v, dict):
        return "kamus"
    if isinstance(v, _JakselBase):
        return "objek %s" % type(v).__name__
    if isinstance(v, _EnumMember):
        return "anggota enum %s.%s" % (v._enum, v._member)
    if isinstance(v, type) and issubclass(v, _JakselBase):
        return "kelas %s" % v.__name__
    if isinstance(v, type) and issubclass(v, _EnumBase):
        return "enum %s" % v.__name__
    return "nilai"


def _tambah(a, b, line=None):
    if isinstance(a, bool) or isinstance(b, bool):
        raise JakselError("valid/gimmick nggak bisa ditambah.", line)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + b
    if isinstance(a, str) and isinstance(b, str):
        return a + b
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    raise JakselError("'+' nggak bisa buat %s + %s."
                      % (_tname(a), _tname(b)), line)


def _arit(a, b, op, line=None):
    if (isinstance(a, bool) or isinstance(b, bool)
            or not isinstance(a, (int, float))
            or not isinstance(b, (int, float))):
        raise JakselError("'%s' cuma buat angka, bestie." % op, line)
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    raise JakselError("operator '%s' nggak dikenal." % op, line)


def _bagi(a, b, line=None):
    if (isinstance(a, bool) or isinstance(b, bool)
            or not isinstance(a, (int, float))
            or not isinstance(b, (int, float))):
        raise JakselError("'/' cuma buat angka, bestie.", line)
    if b == 0:
        raise JakselError("bagi nol? Gimmick banget.", line)
    return a / b


def _mod(a, b, line=None):
    if (isinstance(a, bool) or isinstance(b, bool)
            or not isinstance(a, (int, float))
            or not isinstance(b, (int, float))):
        raise JakselError("'%' cuma buat angka, bestie.", line)
    if b == 0:
        raise JakselError("modulo nol? Gimmick banget.", line)
    return a % b


def _neg(x, line=None):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise JakselError("minus cuma buat angka.", line)
    return -x


def _eq(a, b):
    eq = a == b and type(a) is type(b) or a == b
    if type(a) is not type(b) and not (
            isinstance(a, (int, float)) and isinstance(b, (int, float))):
        eq = False
    return eq


def _banding(a, b, op, line=None):
    if isinstance(a, bool) or isinstance(b, bool):
        raise JakselError("'%s' nggak buat valid/gimmick." % op, line)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        pass
    elif isinstance(a, str) and isinstance(b, str):
        pass
    else:
        raise JakselError("'%s' nggak bisa buat %s lawan %s."
                          % (op, _tname(a), _tname(b)), line)
    return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]


# Peta operator -> nama method overload (dunder).
_DUNDER_BIN = {
    "+": "__tambah__", "-": "__kurang__", "*": "__kali__",
    "/": "__bagi__", "%": "__sisa__",
    "==": "__sama__", "!=": "__beda__",
    "<": "__kurang_dari__", ">": "__lebih_dari__",
    "<=": "__kurang_dari_sama__", ">=": "__lebih_dari_sama__",
}


def _ov_bin(a, b, op, biasa, line=None):
    """Operator biner + overloading __tambah__ dkk.

    Method diambil lewat getattr sehingga otomatis terikat ke ``ini``
    (FungsiVM adalah descriptor). Reflected: method di operan kanan dicoba
    dengan operan kiri sebagai argumen.
    """
    dunder = _DUNDER_BIN[op]
    m = getattr(a, dunder, None)
    if callable(m):
        return m(b)
    m = getattr(b, dunder, None)
    if callable(m):
        return m(a)
    return biasa(a, b, line)


def _binop(op, a, b, line=None):
    """Implementasi opcode BINOP."""
    if op == "+":
        return _ov_bin(a, b, op, _tambah, line)
    if op == "-":
        return _ov_bin(a, b, op, lambda x, y, ln: _arit(x, y, "-", ln), line)
    if op == "*":
        return _ov_bin(a, b, op, lambda x, y, ln: _arit(x, y, "*", ln), line)
    if op == "/":
        return _ov_bin(a, b, op, _bagi, line)
    if op == "%":
        return _ov_bin(a, b, op, _mod, line)
    if op in ("==", "!="):
        dunder = _DUNDER_BIN[op]
        m = getattr(a, dunder, None)
        if callable(m):
            return bool(m(b))
        m = getattr(b, dunder, None)
        if callable(m):
            return bool(m(a))
        eq = _eq(a, b)
        return eq if op == "==" else not eq
    if op in ("<", ">", "<=", ">="):
        dunder = _DUNDER_BIN[op]
        m = getattr(a, dunder, None)
        if callable(m):
            return bool(m(b))
        m = getattr(b, dunder, None)
        if callable(m):
            return bool(m(a))
        return _banding(a, b, op, line)
    if op == "dalam":
        if isinstance(b, dict):
            return a in b
        if isinstance(b, (list, str)):
            return a in b
        raise JakselError("'dalam' cuma buat daftar/teks/kamus, bukan %s."
                          % _tname(b), line)
    raise JakselError("operator '%s' nggak dikenal." % op, line)


def _cocok_tipe(v, k, nama_pola, line=None):
    """Pola tipe 'Tipe x': cek instanceof (termasuk enum)."""
    if isinstance(k, type) and issubclass(k, _EnumBase):
        return (isinstance(v, _EnumMember) and v._enum == k._enum_name
                if hasattr(k, "_enum_name") else False)
    if isinstance(k, type):
        return isinstance(v, k)
    raise JakselError("pola '%s' bukan kelas, bestie." % nama_pola, line)


def _cocok_enum(v, enum_name, member_name):
    """Pola enum 'Warna.MERAH': cek anggota enum yang pas."""
    return (isinstance(v, _EnumMember) and v._enum == enum_name
            and v._member == member_name)

# Impor parser secara malas di bawah (hindari siklus impor saat
# jaksel/__init__ memuat modul).
_P = None


def _parser():
    global _P
    if _P is None:
        from . import parser as _pp
        _P = _pp
    return _P


# ---------------------------------------------------------------------------
# Nilai runtime khusus VM
# ---------------------------------------------------------------------------

class _TidakAda:
    """Sentinel untuk 'tidak ada nilai paksa'."""


_TIDAK_ADA = _TidakAda()


class _MetodeStatik:
    """Penanda method statik di namespace kelas (sebelum type() jadi)."""

    def __init__(self, fungsi):
        self.fungsi = fungsi


class _Properti:
    """Properti Jaksel: getter/setter berupa FungsiVM."""

    def __init__(self, getter, setter, aman=False):
        self.getter = getter
        self.setter = setter
        self._aman = aman

    def ke_property(self):
        getter = self.getter
        setter = self.setter

        def _get(obj):
            if getter is None:
                raise AttributeError("properti cuma bisa ditulis")
            return getter.panggil_luar(obj)

        def _set(obj, val):
            if setter is None:
                raise AttributeError("properti cuma bisa dibaca")
            setter.panggil_luar(obj, val)

        return property(_get, _set if setter else None)


def _buat_repr(tampil_fn, aman):
    """Bungkus talent 'tampil' jadi __repr__ Python."""
    _dijaga = set()

    def __repr__(self):
        if id(self) in _dijaga:
            return "<%s>" % type(self).__name__
        _dijaga.add(id(self))
        try:
            return format_value(tampil_fn.panggil_luar(self))
        except Exception:  # noqa: BLE001 - fallback aman
            return "<%s>" % type(self).__name__
        finally:
            _dijaga.discard(id(self))

    return __repr__


class _ErrorJaksel(_JakselBase):
    """Kelas Error bawaan JakselScript (induk semua error)."""

    def __init__(self, *a):
        self.pesan = a[0] if len(a) == 1 else (list(a) if a else "")


# -- method bawaan tipe (daftar/teks/kamus) --

def _m_daftar_tambah(obj, args):
    obj.append(args[0])
    return None


class _tipe_method:
    """Method bawaan yang terikat ke nilai (daftar/teks/kamus)."""

    def __init__(self, obj, fn):
        self.obj = obj
        self.fn = fn

    def __call__(self, *args, **kwargs):
        return self.fn(self.obj, list(args))

    def __repr__(self):
        return "<method bawaan>"


_METHODS = {
    # (tipe, nama) -> fungsi(obj, args_list)
    (list, "tambah"): _m_daftar_tambah,
}


# ---------------------------------------------------------------------------
# CodeUnit: satu unit kode terkompilasi (program / fungsi / method / kelas)
# ---------------------------------------------------------------------------

class CodeUnit:
    """Satu fungsi/program dalam bentuk bytecode.

    ``code`` adalah list pasangan ``(op, arg)``; ``arg`` boleh int, str,
    tuple, atau None. ``lines`` sejajar dengan ``code`` (nomor baris sumber
    tiap instruksi, buat pesan error yang akurat).
    """

    __slots__ = ("nama", "params", "variadic", "ndefaults", "consts",
                 "names", "code", "lines", "_const_idx", "_name_idx",
                 "sumber_dir")

    def __init__(self, nama, params=(), variadic=None, ndefaults=0):
        self.nama = nama
        self.params = list(params)
        self.variadic = variadic
        self.ndefaults = ndefaults
        self.consts = []
        self.names = []
        self.code = []
        self.lines = []
        self._const_idx = {}
        self._name_idx = {}
        self.sumber_dir = None  # direktori sumber .jaksel (buat import relatif)

    # -- pembangunan --
    def const(self, v):
        try:
            key = ("k", type(v).__name__, v)
            if key in self._const_idx:
                return self._const_idx[key]
        except TypeError:
            key = None
        idx = len(self.consts)
        self.consts.append(v)
        if key is not None:
            self._const_idx[key] = idx
        return idx

    def name(self, s):
        if s in self._name_idx:
            return self._name_idx[s]
        idx = len(self.names)
        self.names.append(s)
        self._name_idx[s] = idx
        return idx

    def emit(self, op, arg=None, line=None):
        self.code.append((op, arg))
        self.lines.append(line)
        return len(self.code) - 1

    def patch(self, pos, target=None):
        """Patch instruksi jump di posisi pos (default target: posisi kini)."""
        if target is None:
            target = len(self.code)
        op, _ = self.code[pos]
        self.code[pos] = (op, target)

    def dis(self):
        """Disassembly teks untuk debugging."""
        out = []
        for i, (op, arg) in enumerate(self.code):
            if op == "LOAD_CONST":
                arg_s = "const[%d]=%r" % (arg, self.consts[arg])
            elif op in ("LOAD_VAR", "DEF_VAR", "STORE_VAR", "LOAD_ATTR",
                        "STORE_ATTR", "CLASS_BEGIN"):
                arg_s = "name[%d]=%s" % (arg, self.names[arg])
            elif op in ("CALL_METHOD", "SUPER_CALL"):
                arg_s = "name[%d]=%s argc=%d" % (
                    arg[0], self.names[arg[0]], arg[1])
            elif op in ("CALL_METHOD_EX", "SUPER_CALL_EX"):
                arg_s = "name[%d]=%s" % (arg, self.names[arg])
            elif op == "BINOP":
                arg_s = self.names[arg]
            elif op in ("MAKE_FUNC", "IMPORT", "CLASS_DEF", "BUILD_ENUM",
                        "MATCH_ENUM"):
                arg_s = repr(self.consts[arg])[:60]
            else:
                arg_s = "" if arg is None else repr(arg)
            ln = self.lines[i]
            out.append("%4d %-18s %-28s (baris %s)" % (i, op, arg_s, ln))
        return "\n".join(out)

    # -- serialisasi .jsc --
    def to_tuple(self):
        def _c(v):
            if isinstance(v, CodeUnit):
                return ("@kode", v.to_tuple())
            return v

        def _p(p):
            # params: [(nama, CodeUnit|None)]
            nama, default = p
            return (nama, _c(default) if default is not None else None)

        return (
            self.nama,
            tuple(_p(p) for p in self.params),
            self.variadic,
            self.ndefaults,
            tuple(_c(v) for v in self.consts),
            tuple(self.names),
            tuple((op, _c(arg) if not isinstance(arg, (int, str, tuple, type(None))) else arg)
                  for op, arg in self.code),
            tuple(self.lines),
            self.sumber_dir,
        )

    @staticmethod
    def from_tuple(t):
        # dukung format lama (8 elemen, tanpa sumber_dir) & baru (9 elemen)
        if len(t) == 8:
            (nama, params, variadic, ndefaults, consts, names, code, lines) = t
            sumber_dir = None
        else:
            (nama, params, variadic, ndefaults, consts, names, code, lines,
             sumber_dir) = t

        def _u(v):
            if isinstance(v, tuple) and len(v) == 2 and v[0] == "@kode":
                return CodeUnit.from_tuple(v[1])
            return v

        def _p(p):
            nama, default = p
            return (nama, _u(default) if default is not None else None)

        unit = CodeUnit(nama, [_p(p) for p in params], variadic, ndefaults)
        unit.consts = [_u(v) for v in consts]
        unit.names = list(names)
        unit.code = [(op, _u(arg)) for op, arg in code]
        unit.lines = list(lines)
        unit.sumber_dir = sumber_dir
        return unit


JSC_AJAIB = b"JSC1"


def simpan_jsc(unit, path):
    """Simpan CodeUnit terkompilasi ke file .jsc."""
    with open(path, "wb") as f:
        f.write(JSC_AJAIB)
        f.write(marshal.dumps(unit.to_tuple()))


def muat_jsc(path):
    """Muat CodeUnit dari file .jsc."""
    with open(path, "rb") as f:
        ajaib = f.read(len(JSC_AJAIB))
        if ajaib != JSC_AJAIB:
            raise JakselError(f"file '{path}' bukan bytecode .jsc yang valid.")
        return CodeUnit.from_tuple(marshal.loads(f.read()))


def kompilasi(sumber, nama_file="<utama>"):
    """Kompilasi sumber JakselScript -> CodeUnit. (dipakai CLI & tes)"""
    import os as _os
    from .lexer import lex
    from .vm_compiler import Compiler
    prog = _parser().parse(lex(sumber, nama_file))
    unit = Compiler(nama_modul=nama_file).kompilasi_program(prog)
    # ingat direktori sumber biar import relatif jalan dari .jsc juga
    if nama_file != "<utama>":
        unit.sumber_dir = _os.path.dirname(_os.path.abspath(nama_file))
    return unit


def jalan_vm(unit, aman=False, file_dir=".", prog_args=None):
    """Jalankan CodeUnit di VM baru. Kembalikan nilai akhir."""
    # import di sini agar tidak melingkar saat modul dimuat
    from .vm_mesin import VM
    return VM(aman=aman, file_dir=file_dir,
              prog_args=prog_args).jalankan(unit)


# ---------------------------------------------------------------------------
# Frame: satu bingkai eksekusi
# ---------------------------------------------------------------------------

class Frame:
    """Satu frame eksekusi: unit + pc + stack + variabel."""

    __slots__ = ("unit", "pc", "stack", "vars", "parent", "fungsi",
                 "nama", "nilai_kembali_paksa")

    def __init__(self, unit, vars, parent, fungsi, nama):
        self.unit = unit
        self.pc = 0
        self.stack = []
        self.vars = vars
        self.parent = parent      # frame leksikal (closure); None = global
        self.fungsi = fungsi      # FungsiVM yang sedang jalan (atau None)
        self.nama = nama
        self.nilai_kembali_paksa = _TIDAK_ADA

    def define(self, nama, nilai):
        self.vars[nama] = nilai


# ---------------------------------------------------------------------------
# FungsiVM: fungsi JakselScript hasil kompilasi
# ---------------------------------------------------------------------------

class _MethodTerikat:
    """Method yang sudah terikat ke objek (hasil obj.metode)."""

    __slots__ = ("fungsi", "obj")

    def __init__(self, obj, fungsi):
        self.obj = obj
        self.fungsi = fungsi

    def __call__(self, *args, **kwargs):
        return self.fungsi.panggil_luar(self.obj, *args, **kwargs)

    def __repr__(self):
        return "<method '%s' terikat>" % self.fungsi.name


class FungsiVM:
    """Fungsi/talent/method JakselScript yang berjalan di atas VM.

    Mengimplementasikan protokol descriptor: ``obj.metode`` otomatis
    mengikat ``obj`` sebagai argumen pertama (``ini``).
    """

    def __init__(self, unit, closure=None):
        self.unit = unit
        self._closure = closure       # Frame leksikal saat dibuat (atau None)
        self._kelas_pemilik = None     # diisi saat kelas dibangun (ortu)
        self._aman = False             # mode sandbox (diisi MAKE_FUNC)

    @property
    def name(self):
        return self.unit.nama

    @property
    def nama(self):
        return self.unit.nama

    # -- protokol descriptor: obj.m -> terikat ke obj --
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return _MethodTerikat(obj, self)

    def panggil_luar(self, *args, **kwargs):
        """Dipanggil dari dunia Python (property, __repr__, overload,
        callback, thread): buat VM baru dan jalankan sampai selesai."""
        # import di sini agar tidak melingkar saat modul dimuat
        from .vm_mesin import VM
        v = VM(aman=self._aman)
        return v._jalankan_fungsi_luar(self, list(args), dict(kwargs))

    def __call__(self, *args, **kwargs):
        return self.panggil_luar(*args, **kwargs)

    def __repr__(self):
        return "<talent '%s'>" % self.unit.nama
