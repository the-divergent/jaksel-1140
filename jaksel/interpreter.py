"""Interpreter JakselScript: tree-walking interpreter untuk AST."""

import csv
import datetime
import difflib
import importlib
import json
import os
import re
import subprocess
import time
import random as _random_module
import urllib.parse
import urllib.request
import urllib.error

from .errors import JakselError
from .lexer import KEYWORDS, JakselSyntaxError, lex
from .parser import (
    Assign, Attr, BinOp, Block, BreakStmt, Call, ChainComp, ClassDef, Comp,
    ContinueStmt, Destructure, DictLit, EnumDef, ExitStmt, ExportStmt,
    ExprStmt, ForStmt, FuncDef, IfExpr, IfStmt, ImportStmt, Index,
    InterpString, ListLit, Literal,
    MatchStmt, Name, NotOp, Parser, PatBind, PatDict, PatEnum, PatList, PatLit,
    PatType, PatWild, Program, PropertyDef, ReturnStmt, Slice, Spread,
    SuperExpr, ThisExpr, ThrowStmt, TryStmt, UnaryOp, VarDecl, WhileStmt, parse,
)

# Direktori paket jaksel (buat cari folder std/) — works baik dari source
# maupun hasil pip install.
_PAKET_DIR = os.path.dirname(os.path.abspath(__file__))
# Direktori paket yang dipasang user via `jaksel pasang`.
_PAKET_USER_DIR = os.path.expanduser(os.path.join("~", ".jaksel", "paket"))


# ---------------- Saran typo ("Maksudnya ...?") ----------------

def mirip(nama, kandidat):
    """Kembalikan kandidat paling mirip, atau None."""
    cocok = difflib.get_close_matches(nama, list(kandidat), n=1, cutoff=0.6)
    return cocok[0] if cocok else None


# ---------------- Sinyal kontrol ----------------

class _Return(Exception):
    def __init__(self, value):
        self.value = value


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _Exit(Exception):
    def __init__(self, code):
        self.code = code


# ---------------- Environment ----------------

class Environment:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent
        self.exports = None  # list[str] — diisi oleh 'ekspor'; None = semua

    def get(self, name, line=None):
        env = self
        semua = set()
        while env is not None:
            semua.update(env.vars.keys())
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        msg = (f"variabel '{name}' belum dikenalin, bestie. "
               f"Deklarasi dulu pakai 'bestie {name} = ...'")
        s = mirip(name, semua | set(KEYWORDS))
        if s:
            msg += f" Maksudnya '{s}'?"
        raise JakselError(msg, line)

    def set(self, name, value):
        env = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        self.vars[name] = value  # bikin baru di scope ini

    def define(self, name, value):
        self.vars[name] = value


# ---------------- Nilai fungsi & kelas ----------------

class JakselFunction:
    def __init__(self, name, params, body, closure, defaults=None,
                 is_method=False, variadic=None, is_static=False):
        # params: [nama]; defaults: {nama: nilai} dievaluasi saat definisi
        # variadic: nama parameter ...sisa (tampung kelebihan argumen)
        self.name, self.params, self.body, self.closure = name, params, body, closure
        self.defaults = defaults or {}
        self.is_method = is_method
        self.variadic = variadic
        self.is_static = is_static

    def __repr__(self):
        return f"<talent {self.name}>"


class JakselProperty:
    """properti: ambil/taruh dengan getter/setter berbentuk JakselFunction."""

    def __init__(self, name, getter, setter, owner):
        self.name = name
        self.getter = getter    # JakselFunction | None
        self.setter = setter    # JakselFunction | None
        self.owner = owner      # JakselClass

    def __repr__(self):
        return f"<properti {self.name}>"


class JakselEnumMember:
    """Satu anggota enum: Warna.MERAH. tampil() -> 'Warna.MERAH'."""

    def __init__(self, enum_name, member_name, value):
        self.enum_name = enum_name
        self.member_name = member_name
        self.value = value

    def __repr__(self):
        return f"{self.enum_name}.{self.member_name}"


class JakselClass:
    """Definisi kelas: nama, induk (warisi), method, properti, atribut kelas."""

    def __init__(self, name, parent, methods, properties=None, attrs=None):
        self.name = name
        self.parent = parent          # JakselClass | None
        self.methods = methods        # dict nama -> JakselFunction
        self.properties = properties or {}  # dict nama -> JakselProperty
        self.attrs = attrs or {}      # atribut kelas (dipakai enum & konstanta)
        self.is_enum = False          # True kalau dibuat via 'pilihan'

    def cari_method(self, name):
        """Cari method di kelas ini lalu ke atas (MRO linear)."""
        cls = self
        while cls is not None:
            if name in cls.methods:
                return cls.methods[name]
            cls = cls.parent
        return None

    def cari_property(self, name):
        """Cari properti di kelas ini lalu ke atas."""
        cls = self
        while cls is not None:
            if name in cls.properties:
                return cls.properties[name]
            cls = cls.parent
        return None

    def semua_method(self):
        out = {}
        cls = self
        while cls is not None:
            for k, v in cls.methods.items():
                out.setdefault(k, v)
            cls = cls.parent
        return out

    def __repr__(self):
        return f"<kelas {self.name}>"


class JakselModul:
    """Namespace hasil 'collab \"x\" sebagai u': atribut = nama yang diimpor."""

    def __init__(self, name, names):
        self.name = name
        self.names = names  # dict

    def __repr__(self):
        return f"<modul {self.name}>"


class JakselPyModul:
    """Bungkus modul Python hasil 'collab python \"os\"'."""

    def __init__(self, name, module):
        self.name = name
        self.module = module

    def __repr__(self):
        return f"<modul python '{self.name}'>"


class JakselPyObj:
    """Bungkus objek Python apa pun (hasil panggil fungsi Python, dsb)."""

    def __init__(self, obj, interp=None):
        self.obj = obj
        self._interp = interp  # buat callback balik ke JakselScript

    def __repr__(self):
        return f"<objek python {type(self.obj).__name__}>"


class JakselPyCallable:
    """Fungsi/method Python yang bisa dipanggil dari JakselScript."""

    def __init__(self, func, interp=None):
        self.func = func
        self._interp = interp

    def __repr__(self):
        return f"<fungsi python '{getattr(self.func, '__name__', '?')}'>"


class JakselTugas:
    """Tugas paralel hasil luncurkan(): jalan di thread sendiri."""

    def __init__(self, name):
        import threading
        self.name = name
        self._event = threading.Event()
        self._hasil = None
        self._error = None

    def selesai(self):
        return self._event.is_set()

    def __repr__(self):
        return f"<tugas '{self.name}'>"


class JakselInstance:
    """Objek hasil 'Kelas(...)'. attrs = atribut instance."""

    def __init__(self, cls):
        self.cls = cls
        self.attrs = {}
        self._interp = None  # diisi interpreter (buat method 'tampil')

    def __repr__(self):
        return f"<{self.cls.name}>"


class BoundMethod:
    """Method yang sudah diikat ke sebuah instance ('ini' kebind otomatis)."""

    def __init__(self, instance, func):
        self.instance, self.func = instance, func

    def __repr__(self):
        return f"<method '{self.func.name}' dari {self.instance.cls.name}>"


class StaticMethod:
    """Method statik: dipanggil lewat Kelas.nama(), tanpa 'ini'."""

    def __init__(self, cls, func):
        self.cls, self.func = cls, func

    def __repr__(self):
        return f"<method statik '{self.cls.name}.{self.func.name}'>"


class SuperRef:
    """Hasil evaluasi 'ortu': method dicari mulai dari kelas induk."""

    def __init__(self, instance, parent_cls):
        self.instance, self.parent_cls = instance, parent_cls

    def __repr__(self):
        return f"<ortu dari {self.instance.cls.name}>"


class BuiltinFunction:
    def __init__(self, name, func):
        self.name, self.func = name, func

    def __repr__(self):
        return f"<bawaan {self.name}>"


class MethodValue:
    """Method yang nempel ke sebuah nilai, mis. buah.tambah."""

    def __init__(self, obj, name):
        self.obj, self.name = obj, name

    def __repr__(self):
        return f"<method '{self.name}'>"


def is_truthy(v):
    if v is None or v is False:
        return False
    if v is True:
        return True
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, (str, list, dict)):
        return len(v) > 0
    return True


_FMT_GUARD = set()  # anti rekursi tak berujung kalau tampil() balikin ini


def format_value(v):
    if v is True:
        return "valid"
    if v is False:
        return "gimmick"
    if v is None:
        return "zonk"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, list):
        return "[" + ", ".join(format_value(e) for e in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f'"{k}": {format_value(x)}' for k, x in v.items()) + "}"
    if isinstance(v, JakselClass):
        return f"<kelas {v.name}>"
    if isinstance(v, JakselEnumMember):
        return f"{v.enum_name}.{v.member_name}"
    if isinstance(v, JakselModul):
        return f"<modul {v.name}>"
    if isinstance(v, JakselPyModul):
        return f"<modul python '{v.name}'>"
    if isinstance(v, JakselPyObj):
        return f"<objek python {type(v.obj).__name__}>"
    if isinstance(v, JakselPyCallable):
        return f"<fungsi python '{getattr(v.func, '__name__', '?')}'>"
    if isinstance(v, JakselTugas):
        return f"<tugas '{v.name}'>"
    if isinstance(v, JakselProperty):
        return f"<properti {v.name}>"
    if isinstance(v, JakselInstance):
        # kalau kelasnya punya method 'tampil', pakai itu buat representasi
        tampil = v.cls.cari_method("tampil")
        if tampil is not None and v._interp is not None and id(v) not in _FMT_GUARD:
            _FMT_GUARD.add(id(v))
            try:
                return format_value(v._interp._panggil_method(v, tampil, [], None))
            except Exception:
                return f"<{v.cls.name}>"
            finally:
                _FMT_GUARD.discard(id(v))
        return f"<{v.cls.name}>"
    return str(v)


# ---------------- Operator overloading ----------------
# Method __tambah__ dkk di kelas bikin operator +, -, *, ... bisa dipakai
# di objek. Kiri dicoba dulu, lalu kanan (reflected).

_OP_OVERLOAD = {
    "+": "__tambah__", "-": "__kurang__", "*": "__kali__", "/": "__bagi__",
    "%": "__sisa__", "**": "__pangkat__",
    "==": "__sama__", "!=": "__beda__",
    "<": "__kurang_dari__", "<=": "__kurang_dari_sama__",
    ">": "__lebih_dari__", ">=": "__lebih_dari_sama__",
}

_TIDAK_ADA = object()  # sentinel: nggak ada overload yang cocok


def _py_ke_jaksel(v, interp=None):
    """Konversi nilai Python -> nilai JakselScript."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple)):
        return [_py_ke_jaksel(x, interp) for x in v]
    if isinstance(v, dict):
        return {str(k): _py_ke_jaksel(x, interp) for k, x in v.items()}
    if callable(v):
        return JakselPyCallable(v, interp)
    return JakselPyObj(v, interp)


def _jaksel_ke_py(v, interp=None):
    """Konversi nilai JakselScript -> nilai Python (buat argumen panggilan)."""
    if isinstance(v, JakselPyObj):
        return v.obj
    if isinstance(v, JakselPyCallable):
        return v.func
    if isinstance(v, JakselEnumMember):
        return v.value
    if isinstance(v, list):
        return [_jaksel_ke_py(x, interp) for x in v]
    if isinstance(v, dict):
        return {k: _jaksel_ke_py(x, interp) for k, x in v.items()}
    if isinstance(v, JakselFunction):
        # callback JakselScript yang bisa dipanggil dari Python
        def _cb(*args, **kwargs):
            if kwargs:
                raise JakselError(
                    "callback JakselScript nggak terima argumen bernama dari Python.")
            return _jaksel_ke_py(interp._panggil_nilai(
                v, [_py_ke_jaksel(a, interp) for a in args], None), interp)
        return _cb
    if isinstance(v, (JakselInstance, JakselClass, JakselModul, JakselTugas)):
        raise JakselError(
            f"{format_value(v)} nggak bisa dikirim ke fungsi Python, bestie.")
    return v


# ---------------- Methods ----------------
# obj.nama(args): method bawaan untuk daftar / teks / kamus.
# Tiap implementasi: fn(obj, args) -> nilai, raise JakselError (tanpa baris)
# kalau argumen/tipe nggak pas; call_method yang nempelin nomor baris.

def _nargs(nama, args, mn, mx=None):
    mx = mn if mx is None else mx
    if not mn <= len(args) <= mx:
        perlu = str(mn) if mn == mx else f"{mn}-{mx}"
        raise JakselError(f"{nama}() butuh {perlu} argumen, bestie.")


def _m_tambah(obj, args):
    _nargs("tambah", args, 1)
    obj.append(args[0])
    return obj


def _m_buang(obj, args):
    _nargs("buang", args, 0, 1)
    if not obj:
        raise JakselError("daftarnya kosong, nggak ada yang bisa dibuang.")
    idx = args[0] if args else -1
    if isinstance(idx, bool) or not isinstance(idx, int):
        raise JakselError("buang() butuh index angka bulat.")
    if idx < 0:
        idx += len(obj)
    if not 0 <= idx < len(obj):
        raise JakselError("index buang() kelewat batas, bestie.")
    return obj.pop(idx)


def _m_sisipkan(obj, args):
    _nargs("sisipkan", args, 2)
    idx = args[0]
    if isinstance(idx, bool) or not isinstance(idx, int):
        raise JakselError("sisipkan() butuh index angka bulat.")
    obj.insert(idx, args[1])
    return obj


def _m_urut(obj, args):
    _nargs("urut", args, 0)
    try:
        obj.sort()
    except TypeError:
        raise JakselError("daftarnya campur aduk, nggak bisa diurut, bestie.")
    return obj


def _m_balik(obj, args):
    _nargs("balik", args, 0)
    obj.reverse()
    return obj


def _m_gabung(obj, args):
    _nargs("gabung", args, 1)
    pemisah = args[0]
    if not isinstance(pemisah, str):
        raise JakselError("gabung() butuh pemisah teks, bestie.")
    return pemisah.join(format_value(e) for e in obj)


def _m_salin(obj, args):
    _nargs("salin", args, 0)
    return list(obj)


def _m_besar(obj, args):
    _nargs("besar", args, 0)
    return obj.upper()


def _m_kecil(obj, args):
    _nargs("kecil", args, 0)
    return obj.lower()


def _m_potong(obj, args):
    _nargs("potong", args, 0)
    return obj.strip()


def _m_ganti(obj, args):
    _nargs("ganti", args, 2)
    lama, baru = args
    if not isinstance(lama, str) or not isinstance(baru, str):
        raise JakselError("ganti() butuh dua teks, bestie.")
    return obj.replace(lama, baru)


def _m_pisah(obj, args):
    _nargs("pisah", args, 0, 1)
    if not args:
        return obj.split()
    if not isinstance(args[0], str):
        raise JakselError("pisah() butuh pemisah teks, bestie.")
    return obj.split(args[0])


def _m_mulai_dengan(obj, args):
    _nargs("mulai_dengan", args, 1)
    if not isinstance(args[0], str):
        raise JakselError("mulai_dengan() butuh teks, bestie.")
    return obj.startswith(args[0])


def _m_berakhir_dengan(obj, args):
    _nargs("berakhir_dengan", args, 1)
    if not isinstance(args[0], str):
        raise JakselError("berakhir_dengan() butuh teks, bestie.")
    return obj.endswith(args[0])


def _m_kunci(obj, args):
    _nargs("kunci", args, 0)
    return list(obj.keys())


def _m_nilai(obj, args):
    _nargs("nilai", args, 0)
    return list(obj.values())


def _m_ambil(obj, args):
    _nargs("ambil", args, 1, 2)
    key = str(args[0])
    if key in obj:
        return obj[key]
    return args[1] if len(args) == 2 else None


def _m_hapus(obj, args):
    _nargs("hapus", args, 1)
    key = str(args[0])
    if key in obj:
        return obj.pop(key)
    raise JakselError(f"kamus nggak punya kunci '{key}'.")


_METHODS = {
    "daftar": {
        "tambah": _m_tambah, "buang": _m_buang, "sisipkan": _m_sisipkan,
        "urut": _m_urut, "balik": _m_balik, "gabung": _m_gabung,
        "salin": _m_salin,
    },
    "teks": {
        "besar": _m_besar, "kecil": _m_kecil, "potong": _m_potong,
        "ganti": _m_ganti, "pisah": _m_pisah,
        "mulai_dengan": _m_mulai_dengan, "berakhir_dengan": _m_berakhir_dengan,
    },
    "kamus": {
        "kunci": _m_kunci, "nilai": _m_nilai,
        "ambil": _m_ambil, "hapus": _m_hapus,
    },
}


def _tipe_method(obj):
    if isinstance(obj, list):
        return "daftar"
    if isinstance(obj, str):
        return "teks"
    if isinstance(obj, dict):
        return "kamus"
    return None


# ---------------- Interpreter ----------------

class Interpreter:
    def __init__(self, aman=False):
        self.globals = Environment()
        self._loading = set()   # file collab yang sedang dimuat (anti sirkular)
        self._loaded = set()    # file collab yang sudah dimuat
        self._modul_cache = {}  # path absolut -> JakselModul (namespace)
        self._file_dir = "."
        self._argv = []         # argumen baris perintah program (buat args())
        self._stack = []        # jejak tumpukan: [(nama_fungsi, line)]
        self._ini = []          # stack 'ini' (instance method yang sedang jalan)
        self._debug = False     # mode debugger interaktif
        self._debug_step = False
        self._debug_breakpoints = set()
        self._debug_source = None
        self._aman = aman       # mode sandbox: blokir shell/tulis file/jaringan
        self._register_builtins()

    def _wajib_tidak_aman(self, nama):
        """Dipanggil builtin berbahaya: tolak kalau mode sandbox aktif."""
        if self._aman:
            raise JakselError(
                f"'{nama}' diblokir dalam mode aman (--aman), bestie. "
                "Kode ini nggak boleh akses shell/tulis file/jaringan.")

    def _resolve_path(self, path):
        """Path relatif di JakselScript = relatif ke folder file program,
        bukan ke current working directory. Path absolut dibiarkan."""
        if os.path.isabs(path):
            return path
        return os.path.normpath(os.path.join(self._file_dir, path))

    # -- builtins --
    def _register_builtins(self):
        def b_spill(*args):
            print(" ".join(format_value(a) for a in args))
            return None

        def b_kepo(prompt=""):
            return input(format_value(prompt))

        def b_healing(det):
            if not isinstance(det, (int, float)):
                raise JakselError("healing() butuh angka detik, bestie.")
            time.sleep(float(det))
            return None

        def b_panjang(x):
            if isinstance(x, (str, list, dict)):
                return len(x)
            raise JakselError("panjang() cuma bisa buat teks/daftar/kamus.")

        def b_angka(x):
            try:
                if isinstance(x, bool):
                    raise ValueError
                if isinstance(x, (int, float)):
                    return x
                s = str(x).strip()
                return int(s) if "." not in s else float(s)
            except (ValueError, TypeError):
                raise JakselError(f"'{format_value(x)}' nggak bisa jadi angka.")

        def b_teks(x):
            return format_value(x)

        def b_rentang(*args):
            if not 1 <= len(args) <= 3:
                raise JakselError("rentang() butuh 1-3 angka, bestie.")
            for a in args:
                if isinstance(a, bool) or not isinstance(a, int):
                    raise JakselError("rentang() cuma mau angka bulat, bestie.")
            return list(range(*args))

        def b_acak(*args):
            if len(args) == 0:
                return _random_module.random()
            if len(args) == 1:
                b = args[0]
                if isinstance(b, bool) or not isinstance(b, int):
                    raise JakselError("acak() butuh angka bulat, bestie.")
                return _random_module.randrange(b)
            if len(args) == 2:
                a, b = args
                if any(isinstance(x, bool) or not isinstance(x, int) for x in (a, b)):
                    raise JakselError("acak() butuh angka bulat, bestie.")
                return _random_module.randrange(a, b)
            raise JakselError("acak() maksimal 2 argumen, bestie.")

        def b_waktu():
            return time.time()

        def b_tanggal(*args):
            if len(args) > 1:
                raise JakselError("tanggal() maksimal 1 argumen format, bestie.")
            fmt = "%d/%m/%Y %H:%M:%S"
            if args:
                if not isinstance(args[0], str):
                    raise JakselError("format tanggal() harus teks, bestie.")
                fmt = args[0]
            return datetime.datetime.now().strftime(fmt)

        def b_petakan(daftar, f):
            if not isinstance(daftar, (list, str)):
                raise JakselError("petakan() butuh daftar/teks, bestie.")
            return [self._panggil_nilai(f, [x], None) for x in daftar]

        def b_saring(daftar, f):
            if not isinstance(daftar, (list, str)):
                raise JakselError("saring() butuh daftar/teks, bestie.")
            return [x for x in daftar
                    if is_truthy(self._panggil_nilai(f, [x], None))]

        def b_kumpulkan(daftar, f, awal):
            if not isinstance(daftar, (list, str)):
                raise JakselError("kumpulkan() butuh daftar/teks, bestie.")
            acc = awal
            for x in daftar:
                acc = self._panggil_nilai(f, [acc, x], None)
            return acc

        def b_baca_file(path):
            if not isinstance(path, str):
                raise JakselError("baca_file() butuh path teks, bestie.")
            path = self._resolve_path(path)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    return fh.read()
            except FileNotFoundError:
                raise JakselError(f"file '{path}' nggak ketemu, bestie.")
            except OSError as e:
                raise JakselError(f"gagal baca file '{path}': {e}")

        def b_tulis_file(path, teks):
            self._wajib_tidak_aman("tulis_file")
            if not isinstance(path, str) or not isinstance(teks, str):
                raise JakselError("tulis_file() butuh path & teks, bestie.")
            path = self._resolve_path(path)
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(teks)
            except OSError as e:
                raise JakselError(f"gagal tulis file '{path}': {e}")
            return True

        def b_tambah_file(path, teks):
            self._wajib_tidak_aman("tambah_file")
            if not isinstance(path, str) or not isinstance(teks, str):
                raise JakselError("tambah_file() butuh path & teks, bestie.")
            path = self._resolve_path(path)
            try:
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(teks)
            except OSError as e:
                raise JakselError(f"gagal nulis ke file '{path}': {e}")
            return True

        # ---- v0.4: scripting nyata ----
        def b_args():
            """Daftar argumen baris perintah setelah nama file program."""
            return list(self._argv)

        def b_env(*args):
            if not 1 <= len(args) <= 2:
                raise JakselError("env() butuh 1-2 argumen: env(nama, default?).")
            nama = args[0]
            if not isinstance(nama, str):
                raise JakselError("env() butuh nama variabel teks, bestie.")
            return os.environ.get(nama, args[1] if len(args) == 2 else None)

        def b_tipe(x):
            if x is None:
                return "zonk"
            if isinstance(x, bool):
                return "valid/gimmick"
            if isinstance(x, (int, float)):
                return "angka"
            if isinstance(x, str):
                return "teks"
            if isinstance(x, list):
                return "daftar"
            if isinstance(x, dict):
                return "kamus"
            if isinstance(x, (JakselFunction, BuiltinFunction,
                              BoundMethod, MethodValue)):
                return "fungsi"
            if isinstance(x, JakselClass):
                return "kelas"
            if isinstance(x, JakselInstance):
                return x.cls.name
            return "nilai"

        def b_klaim(kondisi, pesan="Klaim gagal, bestie."):
            if not is_truthy(kondisi):
                raise JakselError(format_value(pesan))
            return True

        def b_jalankan(perintah):
            self._wajib_tidak_aman("jalankan")
            """Jalankan perintah shell, kembalikan {kode, keluar, galat}."""
            if not isinstance(perintah, str):
                raise JakselError("jalankan() butuh teks perintah, bestie.")
            try:
                r = subprocess.run(perintah, shell=True, capture_output=True,
                                   text=True, timeout=60)
            except subprocess.TimeoutExpired:
                raise JakselError("perintahnya kelamaan (timeout 60 detik), bestie.")
            except OSError as e:
                raise JakselError(f"gagal jalanin perintah: {e}")
            return {"kode": r.returncode, "keluar": r.stdout, "galat": r.stderr}

        # ---- v0.4: JSON ----
        def b_json_urai(teks):
            if not isinstance(teks, str):
                raise JakselError("json_urai() butuh teks, bestie.")
            try:
                return json.loads(teks)
            except ValueError as e:
                raise JakselError(f"teksnya bukan JSON valid: {e}")

        def b_json_tulis(nilai, cantik=False):
            if not isinstance(cantik, bool):
                raise JakselError("argumen 'cantik' json_tulis() harus valid/gimmick.")
            try:
                return json.dumps(nilai, ensure_ascii=False,
                                  indent=2 if cantik else None)
            except (TypeError, ValueError) as e:
                raise JakselError(f"nilainya nggak bisa jadi JSON: {e}")

        # ---- v0.4: HTTP ----
        def _http_minta(url, data=None):
            if not isinstance(url, str):
                raise JakselError("http butuh URL teks, bestie.")
            req_data = None
            headers = {"User-Agent": "JakselScript/0.6.0"}
            if data is not None:
                if isinstance(data, dict):
                    req_data = urllib.parse.urlencode(data).encode("utf-8")
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
                elif isinstance(data, str):
                    req_data = data.encode("utf-8")
                else:
                    raise JakselError("data http_post() harus kamus/teks, bestie.")
            req = urllib.request.Request(url, data=req_data, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e:
                raise JakselError(f"HTTP {e.code} pas buka {url}, bestie.")
            except urllib.error.URLError as e:
                raise JakselError(f"gagal konek ke {url}: {e.reason}")
            except (OSError, ValueError) as e:
                raise JakselError(f"HTTP error: {e}")

        def b_http_get(url):
            self._wajib_tidak_aman("http_get")
            return _http_minta(url)

        def b_http_get_json(url):
            self._wajib_tidak_aman("http_get_json")
            return b_json_urai(_http_minta(url))

        def b_http_post(url, data=None):
            self._wajib_tidak_aman("http_post")
            return _http_minta(url, data)

        # ---- v0.4: regex ----
        def _cek_regex(teks, pola, nama):
            if not isinstance(teks, str) or not isinstance(pola, str):
                raise JakselError(f"{nama}() butuh teks & pola teks, bestie.")
            try:
                return re.compile(pola)
            except re.error as e:
                raise JakselError(f"pola regex-nya rusak, bestie: {e}")

        def b_cocok(teks, pola):
            rx = _cek_regex(teks, pola, "cocok")
            return rx.search(teks) is not None

        def b_cari(teks, pola):
            rx = _cek_regex(teks, pola, "cari")
            m = rx.search(teks)
            return m.group(0) if m else None

        def b_cari_semua(teks, pola):
            rx = _cek_regex(teks, pola, "cari_semua")
            return rx.findall(teks)

        def b_ganti_regex(teks, pola, ganti):
            rx = _cek_regex(teks, pola, "ganti_regex")
            if not isinstance(ganti, str):
                raise JakselError("ganti_regex() butuh teks pengganti, bestie.")
            return rx.sub(ganti, teks)

        # ---- v0.4: CSV ----
        def b_csv_baca(path):
            if not isinstance(path, str):
                raise JakselError("csv_baca() butuh path teks, bestie.")
            path = self._resolve_path(path)
            try:
                with open(path, "r", encoding="utf-8", newline="") as fh:
                    return [list(baris) for baris in csv.reader(fh)]
            except FileNotFoundError:
                raise JakselError(f"file '{path}' nggak ketemu, bestie.")
            except OSError as e:
                raise JakselError(f"gagal baca CSV '{path}': {e}")

        def b_csv_tulis(path, data):
            self._wajib_tidak_aman("csv_tulis")
            if not isinstance(path, str):
                raise JakselError("csv_tulis() butuh path teks, bestie.")
            if not isinstance(data, list) or any(
                    not isinstance(b, list) for b in data):
                raise JakselError(
                    "csv_tulis() butuh daftar berisi daftar baris, bestie.")
            path = self._resolve_path(path)
            try:
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    csv.writer(fh).writerows(
                        [[format_value(c) for c in baris] for baris in data])
            except OSError as e:
                raise JakselError(f"gagal tulis CSV '{path}': {e}")
            return True

        # ---- v0.4: file & folder ----
        def b_ada_file(path):
            if not isinstance(path, str):
                raise JakselError("ada_file() butuh path teks, bestie.")
            return os.path.exists(self._resolve_path(path))

        def b_daftar_file(folder="."):
            if not isinstance(folder, str):
                raise JakselError("daftar_file() butuh path folder teks, bestie.")
            try:
                return sorted(os.listdir(self._resolve_path(folder)))
            except OSError as e:
                raise JakselError(f"gagal baca folder '{folder}': {e}")

        def b_buat_folder(path):
            self._wajib_tidak_aman("buat_folder")
            if not isinstance(path, str):
                raise JakselError("buat_folder() butuh path teks, bestie.")
            path = self._resolve_path(path)
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as e:
                raise JakselError(f"gagal bikin folder '{path}': {e}")
            return True

        def b_hapus_file(path):
            self._wajib_tidak_aman("hapus_file")
            if not isinstance(path, str):
                raise JakselError("hapus_file() butuh path teks, bestie.")
            path = self._resolve_path(path)
            try:
                os.remove(path)
            except FileNotFoundError:
                raise JakselError(f"file '{path}' nggak ketemu, bestie.")
            except OSError as e:
                raise JakselError(f"gagal hapus '{path}': {e}")
            return True

        # ---- v0.4: agregat & fungsional ----
        def _cek_daftar_angka(nama, d):
            if not isinstance(d, list):
                raise JakselError(f"{nama}() butuh daftar, bestie.")
            if any(isinstance(x, bool) or not isinstance(x, (int, float))
                   for x in d):
                raise JakselError(f"{nama}() cuma mau daftar angka, bestie.")
            return d

        def b_total(d):
            return sum(_cek_daftar_angka("total", d))

        def b_terbesar(d):
            dd = _cek_daftar_angka("terbesar", d)
            if not dd:
                raise JakselError("daftarnya kosong, nggak ada yang terbesar.")
            return max(dd)

        def b_terkecil(d):
            dd = _cek_daftar_angka("terkecil", d)
            if not dd:
                raise JakselError("daftarnya kosong, nggak ada yang terkecil.")
            return min(dd)

        def b_rerata(d):
            dd = _cek_daftar_angka("rerata", d)
            if not dd:
                raise JakselError("daftarnya kosong, nggak bisa dirata-rata.")
            return sum(dd) / len(dd)

        def b_urut_dengan(daftar, kunci):
            if not isinstance(daftar, list):
                raise JakselError("urut_dengan() butuh daftar, bestie.")
            if not isinstance(kunci, (JakselFunction, BuiltinFunction,
                                      BoundMethod, MethodValue)):
                raise JakselError(
                    "urut_dengan() butuh fungsi sebagai kunci, bestie.")
            try:
                return sorted(
                    daftar, key=lambda x: self._panggil_nilai(kunci, [x], None))
            except JakselError:
                raise
            except TypeError:
                raise JakselError(
                    "hasil fungsi kunci nggak bisa dibandingin, bestie.")

        def b_pasangkan(a, b):
            if not isinstance(a, list) or not isinstance(b, list):
                raise JakselError("pasangkan() butuh dua daftar, bestie.")
            return [[x, y] for x, y in zip(a, b)]

        # ---- v0.5: tugas paralel (thread) ----
        def b_luncurkan(f, args=None):
            """luncurkan(f, [argumen]): jalankan f di thread, kembalikan tugas."""
            if not isinstance(f, (JakselFunction, BoundMethod, BuiltinFunction,
                                  JakselPyCallable)):
                raise JakselError(
                    "luncurkan() butuh fungsi/talent, bestie.", )
            daftar = args if args is not None else []
            if not isinstance(daftar, list):
                raise JakselError(
                    "argumen kedua luncurkan() harus daftar, bestie.")
            tugas = JakselTugas(getattr(f, "name", "tugas"))
            anak = _anak_interpreter(self)
            import threading

            def _jalan():
                try:
                    tugas._hasil = anak._panggil_nilai(f, list(daftar), None)
                except Exception as e:  # noqa: BLE001 - diteruskan ke tunggu()
                    tugas._error = e
                finally:
                    tugas._event.set()

            th = threading.Thread(target=_jalan, daemon=True,
                                  name=f"jaksel-{tugas.name}")
            tugas._thread = th
            th.start()
            return tugas

        def b_tunggu(tugas):
            """tunggu(tugas): tunggu sampai selesai, kembalikan hasil."""
            if not isinstance(tugas, JakselTugas):
                raise JakselError("tunggu() butuh hasil luncurkan(), bestie.")
            tugas._event.wait()
            if tugas._error is not None:
                raise tugas._error
            return tugas._hasil

        def b_tunggu_semua(daftar):
            """tunggu_semua([t1, t2]): tunggu semua, kembalikan daftar hasil."""
            if not isinstance(daftar, list) or any(
                    not isinstance(t, JakselTugas) for t in daftar):
                raise JakselError(
                    "tunggu_semua() butuh daftar tugas, bestie.")
            return [b_tunggu(t) for t in daftar]

        for name, fn in [("spill", b_spill), ("kepo", b_kepo),
                         ("healing", b_healing), ("panjang", b_panjang),
                         ("angka", b_angka), ("teks", b_teks),
                         ("rentang", b_rentang), ("acak", b_acak),
                         ("waktu", b_waktu), ("tanggal", b_tanggal),
                         ("petakan", b_petakan), ("saring", b_saring),
                         ("kumpulkan", b_kumpulkan),
                         ("baca_file", b_baca_file),
                         ("tulis_file", b_tulis_file),
                         ("tambah_file", b_tambah_file),
                         ("args", b_args), ("env", b_env),
                         ("tipe", b_tipe), ("klaim", b_klaim),
                         ("jalankan", b_jalankan),
                         ("json_urai", b_json_urai),
                         ("json_tulis", b_json_tulis),
                         ("http_get", b_http_get),
                         ("http_get_json", b_http_get_json),
                         ("http_post", b_http_post),
                         ("cocok", b_cocok), ("cari", b_cari),
                         ("cari_semua", b_cari_semua),
                         ("ganti_regex", b_ganti_regex),
                         ("csv_baca", b_csv_baca),
                         ("csv_tulis", b_csv_tulis),
                         ("ada_file", b_ada_file),
                         ("daftar_file", b_daftar_file),
                         ("buat_folder", b_buat_folder),
                         ("hapus_file", b_hapus_file),
                         ("total", b_total), ("terbesar", b_terbesar),
                         ("terkecil", b_terkecil), ("rerata", b_rerata),
                         ("urut_dengan", b_urut_dengan),
                         ("pasangkan", b_pasangkan),
                         ("luncurkan", b_luncurkan),
                         ("tunggu", b_tunggu),
                         ("tunggu_semua", b_tunggu_semua)]:
            self.globals.define(name, BuiltinFunction(name, fn))
        # kelas Error bawaan: induk semua error ala JakselScript
        self.globals.define("Error", self._buat_kelas_error())

    def _buat_kelas_error(self):
        """Kelas 'Error' bawaan: red_flag Error("pesan") / kelas X warisi Error."""
        return JakselClass("Error", None, {})

    # -- entry points --
    def run_source(self, source, filename="<repl>", file_dir=".", prog_args=None):
        program = parse(lex(source, filename))
        self._file_dir = file_dir
        self._argv = list(prog_args or [])
        self.exec_program(program, self.globals)

    def run_file(self, path, prog_args=None):
        full = os.path.abspath(path)
        with open(full, "r", encoding="utf-8") as f:
            source = f.read()
        self.run_source(source, filename=full,
                        file_dir=os.path.dirname(full), prog_args=prog_args)

    def debug_source(self, source, filename="<debug>", file_dir=".",
                     prog_args=None):
        """Jalankan program dalam mode debugger interaktif (statement-step)."""
        program = parse(lex(source, filename))
        self._file_dir = file_dir
        self._argv = list(prog_args or [])
        self._debug = True
        self._debug_step = True
        self._debug_breakpoints = set()
        self._debug_source = source
        try:
            self.exec_program(program, self.globals)
        finally:
            self._debug = False
            self._debug_step = False

    def _debug_hook(self, node, env):
        """Dipanggil sebelum tiap statement saat mode debug aktif."""
        line = getattr(node, "line", None)
        bp = self._debug_breakpoints
        if not self._debug_step and line not in bp:
            return
        lines = (self._debug_source or "").splitlines()
        kode = lines[line - 1].strip() if line and 1 <= line <= len(lines) \
            else type(node).__name__
        print(f"  [debug] baris {line}: {kode}")
        while True:
            try:
                cmd = input("debug> ").strip()
            except EOFError:
                raise _Exit(0)
            if cmd in ("", "langkah", "l", "s"):
                self._debug_step = True
                return
            if cmd in ("lanjut", "c"):
                self._debug_step = False
                return
            if cmd in ("keluar", "q"):
                raise _Exit(0)
            if cmd == "tumpuk":
                if self._stack:
                    for nama, tl in self._stack:
                        print(f"    di {nama} (baris {tl})")
                else:
                    print("    (di level utama)")
                continue
            if cmd.startswith("b ") or cmd.startswith("break "):
                try:
                    n = int(cmd.split(None, 1)[1])
                    bp.add(n)
                    print(f"  breakpoint di baris {n}")
                except (ValueError, IndexError):
                    print("  pakai: b <nomor-baris>")
                continue
            if cmd.startswith("hapus ") or cmd.startswith("cl "):
                try:
                    n = int(cmd.split(None, 1)[1])
                    bp.discard(n)
                    print(f"  breakpoint baris {n} dihapus")
                except (ValueError, IndexError):
                    print("  pakai: hapus <nomor-baris>")
                continue
            if cmd in ("daftar", "bl"):
                if bp:
                    print("  breakpoint: " + ", ".join(
                        str(n) for n in sorted(bp)))
                else:
                    print("  (belum ada breakpoint)")
                continue
            if cmd.startswith("p ") or cmd.startswith("cetak "):
                expr_src = cmd.split(" ", 1)[1]
                try:
                    sub = Parser(lex(expr_src, "<debug>"))
                    val = self.eval_expr(sub.expr(), env)
                    print("  = " + format_value(val))
                except (JakselError, JakselSyntaxError) as e:
                    print(f"  gagal: {e.raw}")
                continue
            print("  perintah: <enter>=langkah, b <baris>, hapus <baris>, "
                  "lanjut(c), p <ekspresi>, tumpuk, daftar, keluar(q)")

    def eval_line(self, source):
        """Untuk REPL: kembalikan string hasil / None."""
        program = parse(lex(source, "<repl>"))
        out = []
        for stmt in program.statements:
            if isinstance(stmt, ExprStmt):
                val = self.eval_expr(stmt.expr, self.globals)
                if val is not None:
                    out.append(format_value(val))
            else:
                self.exec_stmt(stmt, self.globals)
        return "\n".join(out) if out else None

    # -- statements --
    def exec_program(self, program, env):
        for stmt in program.statements:
            self.exec_stmt(stmt, env)

    def exec_block(self, block, env):
        child = Environment(parent=env)
        for stmt in block.statements:
            self.exec_stmt(stmt, child)

    def exec_stmt(self, node, env):
        if self._debug and getattr(node, "line", None):
            self._debug_hook(node, env)
        if isinstance(node, VarDecl):
            nilai = self.eval_expr(node.value, env)
            if isinstance(node.name, Destructure):
                self._destructure(node.name, nilai, env, definisikan=True,
                                 line=node.line)
            else:
                env.define(node.name, nilai)
        elif isinstance(node, Assign):
            self.exec_assign(node, env)
        elif isinstance(node, ExprStmt):
            self.eval_expr(node.expr, env)
        elif isinstance(node, IfStmt):
            if is_truthy(self.eval_expr(node.cond, env)):
                self.exec_block(node.then_block, env)
            else:
                done = False
                for cond, blk in node.elifs:
                    if is_truthy(self.eval_expr(cond, env)):
                        self.exec_block(blk, env)
                        done = True
                        break
                if not done and node.else_block is not None:
                    self.exec_block(node.else_block, env)
        elif isinstance(node, WhileStmt):
            while is_truthy(self.eval_expr(node.cond, env)):
                try:
                    self.exec_block(node.body, env)
                except _Continue:
                    continue
                except _Break:
                    break
        elif isinstance(node, ForStmt):
            it = self.eval_expr(node.iterable, env)
            if isinstance(it, dict):
                items = list(it.keys())
            elif isinstance(it, (list, str)):
                items = list(it)
            else:
                raise JakselError(
                    "stalk cuma bisa jalanin daftar/teks/kamus, bestie.", node.line)
            loop_env = Environment(parent=env)
            if node.idx_var:
                # stalk i, x dalam ... -> i = index
                for i, item in enumerate(items):
                    loop_env.define(node.idx_var, i)
                    loop_env.define(node.var, item)
                    try:
                        self.exec_block(node.body, loop_env)
                    except _Continue:
                        continue
                    except _Break:
                        break
            else:
                for item in items:
                    loop_env.define(node.var, item)
                    try:
                        self.exec_block(node.body, loop_env)
                    except _Continue:
                        continue
                    except _Break:
                        break
        elif isinstance(node, FuncDef):
            env.define(node.name, JakselFunction(
                node.name, [p for p, _ in node.params], node.body, env,
                {p: self.eval_expr(d, env) for p, d in node.params
                 if d is not None}, variadic=node.variadic))
        elif isinstance(node, ClassDef):
            self.exec_classdef(node, env)
        elif isinstance(node, EnumDef):
            self.exec_enumdef(node, env)
        elif isinstance(node, MatchStmt):
            self.exec_match(node, env)
        elif isinstance(node, ReturnStmt):
            raise _Return(self.eval_expr(node.value, env))
        elif isinstance(node, BreakStmt):
            raise _Break()
        elif isinstance(node, ContinueStmt):
            raise _Continue()
        elif isinstance(node, TryStmt):
            try:
                try:
                    self.exec_block(node.body, env)
                except JakselError as e:
                    err_val = getattr(e, "nilai_error", None)
                    cocok = True
                    if node.catch_class is not None:
                        target = env.get(node.catch_class, node.line)
                        if not isinstance(target, JakselClass):
                            raise JakselError(
                                f"yaudah '{node.catch_class}' bukan kelas, "
                                "bestie.", node.line)
                        cocok = (isinstance(err_val, JakselInstance)
                                 and self._instanceof(err_val.cls, target))
                    if cocok:
                        catch_env = Environment(parent=env)
                        if node.catch_var:
                            catch_env.define(
                                node.catch_var,
                                err_val if err_val is not None else str(e))
                        self.exec_block(node.catch_body, catch_env)
                    else:
                        raise
            finally:
                # 'akhirnya' selalu jalan: sukses, error, return, break...
                if node.finally_body is not None:
                    self.exec_block(node.finally_body, env)
        elif isinstance(node, ThrowStmt):
            nilai = self.eval_expr(node.value, env)
            raise self._red_flag(nilai, node.line)
        elif isinstance(node, ExitStmt):
            code = self.eval_expr(node.code, env)
            if not isinstance(code, (int, float)) or isinstance(code, bool):
                raise JakselError("cabut butuh kode angka.", node.line)
            raise _Exit(int(code))
        elif isinstance(node, ImportStmt):
            self.exec_import(node, env)
        elif isinstance(node, ExportStmt):
            # 'ekspor' di top-level modul: kumpulkan nama yang boleh di-collab.
            # Kalo di dalam fungsi, diabaikan (nggak ada efek).
            if env.exports is None:
                env.exports = []
            for n in node.names:
                if n not in env.exports:
                    env.exports.append(n)
        else:
            raise JakselError(f"statement aneh: {type(node).__name__}")

    def exec_assign(self, node, env):
        value = self.eval_expr(node.value, env)
        tgt = node.target
        if isinstance(tgt, Destructure):
            self._destructure(tgt, value, env, definisikan=False, line=node.line)
            return
        if isinstance(tgt, Name):
            env.set(tgt.id, value)
        elif isinstance(tgt, Index):
            obj = self.eval_expr(tgt.obj, env)
            idx = self.eval_expr(tgt.index, env)
            if isinstance(obj, list):
                if not isinstance(idx, int) or isinstance(idx, bool):
                    raise JakselError("index daftar harus angka bulat.", node.line)
                if idx < 0:
                    idx += len(obj)
                if not 0 <= idx < len(obj):
                    raise JakselError("index daftar kelewat batas, bestie.", node.line)
                obj[idx] = value
            elif isinstance(obj, dict):
                obj[str(idx)] = value
            else:
                raise JakselError("yang bisa di-index cuma daftar/kamus.", node.line)
        elif isinstance(tgt, Attr):
            obj = self.eval_expr(tgt.obj, env)
            if isinstance(obj, dict):
                obj[tgt.name] = value
            elif isinstance(obj, JakselInstance):
                prop = obj.cls.cari_property(tgt.name)
                if prop is not None:
                    if prop.setter is None:
                        raise JakselError(
                            f"properti '{tgt.name}' cuma bisa dibaca "
                            "(nggak ada 'taruh'), bestie.", node.line)
                    self._panggil_method(obj, prop.setter, [value], node.line)
                else:
                    obj.attrs[tgt.name] = value
            else:
                raise JakselError("atribut cuma bisa diset di kamus/objek.",
                                  node.line)

    def _destructure(self, destr, nilai, env, definisikan, line):
        """Bongkar nilai ke target destructuring.

        definisikan=True (bestie [a,b] = ...) -> env.define (boleh nama baru).
        definisikan=False ([a,b] = ...) -> env.set (harus sudah ada).
        """
        def _taro(nama, v):
            if definisikan:
                env.define(nama, v)  # bestie [a] = ... : boleh nama baru
            else:
                env.get(nama, line)  # [a] = ... : harus sudah ada
                env.set(nama, v)

        if destr.kind == "list":
            if not isinstance(nilai, (list, tuple)):
                raise JakselError(
                    "destructuring daftar butuh nilai daftar, bestie.", line)
            elems = list(nilai)
            targets = destr.items
            sisa_i = next((i for i, t in enumerate(targets)
                           if isinstance(t, str) and t.startswith("...")), None)
            if sisa_i is not None:
                if len(elems) < sisa_i:
                    raise JakselError(
                        "daftarnya kependekan buat destructuring, bestie.", line)
                for i in range(sisa_i):
                    _taro(targets[i], elems[i])
                _taro(targets[sisa_i][3:], elems[sisa_i:])
                for t in targets[sisa_i + 1:]:
                    _taro(t, None)
            else:
                if len(elems) != len(targets):
                    raise JakselError(
                        f"destructuring butuh {len(targets)} elemen, "
                        f"dapat {len(elems)}, bestie.", line)
                for t, v in zip(targets, elems):
                    _taro(t, v)
        else:  # "dict"
            if isinstance(nilai, JakselInstance):
                sumber = nilai.attrs
            elif isinstance(nilai, dict):
                sumber = nilai
            else:
                raise JakselError(
                    "destructuring kamus butuh kamus/objek, bestie.", line)
            for kunci, var in destr.items:
                if kunci not in sumber:
                    raise JakselError(
                        f"kunci '{kunci}' nggak ada di sumber, bestie.", line)
                _taro(var, sumber[kunci])

    # ---------------- cocokkan (pattern matching) ----------------

    def exec_match(self, node, env):
        nilai = self.eval_expr(node.subject, env)
        for pola, guard, body in node.arms:
            ikatan = {}
            if self._cocok_pola(pola, nilai, ikatan, env, node.line):
                arm_env = Environment(parent=env)
                for k, v in ikatan.items():
                    arm_env.define(k, v)
                if guard is not None and not is_truthy(
                        self.eval_expr(guard, arm_env)):
                    continue
                self.exec_block(body, arm_env)
                return
        raise JakselError(
            "cocokkan: nggak ada pola yang cocok, bestie. "
            "Tambahin cabang '_' biar aman.", node.line)

    def _cocok_pola(self, pola, nilai, ikatan, env, line):
        """Coba cocokkan pola ke nilai. ikatan diisi kalau cocok."""
        if isinstance(pola, PatWild):
            return True
        if isinstance(pola, PatLit):
            return nilai == pola.value and type(nilai) is type(pola.value)
        if isinstance(pola, PatBind):
            ikatan[pola.name] = nilai
            return True
        if isinstance(pola, PatType):
            target = env.get(pola.name, line)
            if isinstance(target, JakselClass):
                if getattr(target, "is_enum", False):
                    # pola 'Warna' cocok dengan anggota enum Warna mana pun
                    return (isinstance(nilai, JakselEnumMember)
                            and nilai.enum_name == target.name)
                if not isinstance(nilai, JakselInstance):
                    return False
                return self._instanceof(nilai.cls, target)
            raise JakselError(
                f"pola '{pola.name}' bukan kelas, bestie.", line)
        if isinstance(pola, PatEnum):
            return (isinstance(nilai, JakselEnumMember)
                    and nilai.enum_name == pola.enum_name
                    and nilai.member_name == pola.member_name)
        if isinstance(pola, PatList):
            if not isinstance(nilai, (list, tuple)):
                return False
            elems = list(nilai)
            subs = pola.items
            sisa_i = next((i for i, p in enumerate(subs)
                           if isinstance(p, PatBind) and p.rest), None)
            if sisa_i is None:
                if len(elems) != len(subs):
                    return False
                return all(self._cocok_pola(p, v, ikatan, env, line)
                           for p, v in zip(subs, elems))
            if len(elems) < sisa_i:
                return False
            for p, v in zip(subs[:sisa_i], elems[:sisa_i]):
                if not self._cocok_pola(p, v, ikatan, env, line):
                    return False
            ikatan[subs[sisa_i].name] = elems[sisa_i:]
            return True
        if isinstance(pola, PatDict):
            if isinstance(nilai, JakselInstance):
                sumber = nilai.attrs
            elif isinstance(nilai, dict):
                sumber = nilai
            else:
                return False
            for kunci, sub in pola.items:
                if kunci not in sumber:
                    return False
                if not self._cocok_pola(sub, sumber[kunci], ikatan, env, line):
                    return False
            return True
        return False

    # ---------------- pilihan (enum) ----------------

    def exec_enumdef(self, node, env):
        """pilihan Warna { MERAH, HIJAU = 10 } -> kelas enum + anggotanya."""
        members = {}
        nilai_otomatis = 0
        for nama, vnode in node.members:
            if vnode is not None:
                nilai = self.eval_expr(vnode, env)
                if isinstance(nilai, bool) or not isinstance(nilai, int):
                    raise JakselError(
                        f"nilai enum '{nama}' harus angka bulat, bestie.",
                        node.line)
                nilai_otomatis = nilai + 1
            else:
                nilai = nilai_otomatis
                nilai_otomatis += 1
            members[nama] = JakselEnumMember(node.name, nama, nilai)
        kelas_enum = JakselClass(node.name, None, {})
        kelas_enum.attrs.update(members)
        kelas_enum.is_enum = True
        # enum boleh dipakai di cocokkan sebagai pola tipe
        env.define(node.name, kelas_enum)

    # ---------------- error bertipe ----------------

    def _warisi_error(self, cls):
        """True kalau cls adalah Error atau turunannya."""
        c = cls
        while c is not None:
            if c.name == "Error":
                return True
            c = c.parent
        return False

    def _instanceof(self, cls, target):
        """True kalau cls adalah target atau turunannya (identitas kelas)."""
        c = cls
        while c is not None:
            if c is target:
                return True
            c = c.parent
        return False

    def _red_flag(self, nilai, line):
        """red_flag X -> JakselError. X boleh instance Error atau nilai biasa."""
        if isinstance(nilai, JakselInstance) and self._warisi_error(nilai.cls):
            pesan = nilai.attrs.get("pesan")
            teks = format_value(pesan) if pesan is not None else format_value(nilai)
            err = JakselError(f"{nilai.cls.name}: {teks}", line)
            err.nilai_error = nilai
        else:
            err = JakselError(format_value(nilai), line)
            err.nilai_error = nilai if isinstance(nilai, JakselInstance) else None
        return err

    def exec_classdef(self, node, env):
        """kelas Nama warisi Ibu { talent/properti/rahasia/statik ... }."""
        parent = None
        if node.parent:
            if node.parent == node.name:
                raise JakselError(
                    f"kelas '{node.name}' nggak bisa mewarisi dirinya sendiri "
                    "(pewarisan melingkar), bestie.", node.line)
            p = env.get(node.parent, node.line)
            if not isinstance(p, JakselClass):
                raise JakselError(
                    f"'{node.parent}' bukan kelas, nggak bisa diwarisi, bestie.",
                    node.line)
            # cegah pewarisan melingkar tak langsung (A warisi B, B turunan A)
            leluhur = p
            while leluhur is not None:
                if leluhur.name == node.name:
                    raise JakselError(
                        f"pewarisan '{node.name}' melingkar lewat "
                        f"'{p.name}', bestie.", node.line)
                leluhur = leluhur.parent
            parent = p
        methods = {}
        properties = {}
        for m in node.methods:
            if isinstance(m, PropertyDef):
                if m.name in properties or m.name in methods:
                    raise JakselError(
                        f"'{m.name}' didefinisikan dua kali di kelas "
                        f"'{node.name}'.", m.line)
                getter = (JakselFunction(m.name + ".ambil", [], m.getter_body,
                                        env, is_method=True)
                          if m.getter_body is not None else None)
                setter = (JakselFunction(m.name + ".taruh", [m.setter_param],
                                        m.setter_body, env, is_method=True)
                          if m.setter_body is not None else None)
                properties[m.name] = JakselProperty(m.name, getter, setter,
                                                    None)
                continue
            defaults = {}
            params = []
            for pname, dflt in m.params:
                params.append(pname)
                if dflt is not None:
                    defaults[pname] = self.eval_expr(dflt, env)
            if m.name in methods:
                raise JakselError(
                    f"method '{m.name}' didefinisikan dua kali di kelas "
                    f"'{node.name}'.", m.line)
            methods[m.name] = JakselFunction(
                m.name, params, m.body, env, defaults, is_method=True,
                variadic=m.variadic, is_static=m.static)
        kelas = JakselClass(node.name, parent, methods, properties)
        for prop in properties.values():
            prop.owner = kelas
        env.define(node.name, kelas)

    def _cari_collab(self, path):
        """Cari file collab: dir program -> std/ bawaan -> paket user."""
        if not path.endswith(".jaksel"):
            path += ".jaksel"
        kandidat = []
        if not os.path.isabs(path):
            kandidat.append(os.path.join(self._file_dir, path))
        else:
            kandidat.append(path)
        kandidat.append(os.path.join(_PAKET_DIR, path))
        if os.path.isdir(_PAKET_USER_DIR):
            for nama in sorted(os.listdir(_PAKET_USER_DIR)):
                kandidat.append(os.path.join(_PAKET_USER_DIR, nama, path))
        for k in kandidat:
            if os.path.isfile(k):
                return os.path.abspath(k)
        return None

    def exec_import(self, node, env):
        """collab: tiga mode.

        collab "x"                -> nama-nama modul masuk scope global (v0.4)
        collab "x" sebagai u      -> namespace: u.nama
        collab "x" ambil a, b     -> cuma a & b yang masuk scope ini
        collab python "os" ...    -> jembatan ke modul Python (sama polanya)
        """
        if node.py_module is not None:
            self._import_python(node, env)
            return
        full = self._cari_collab(node.path)
        if full is None:
            raise JakselError(
                f"file collab '{node.path}' nggak ketemu "
                "(cek dir program, std/, atau paket terpasang).", node.line)
        if full in self._loading:
            raise JakselError(f"collab sirkular terdeteksi: {node.path}", node.line)
        if full in self._loaded:
            modul = self._modul_cache.get(full)
        else:
            modul = self._muat_modul_jaksel(full, node)
        if node.alias is None and node.ambil is None:
            # mode lawas v0.4: injek langsung ke global (biar contoh lama jalan)
            for k, v in modul.names.items():
                self.globals.define(k, v)
            return
        if node.alias is not None:
            env.define(node.alias, modul)
        if node.ambil is not None:
            for nama in node.ambil:
                if nama not in modul.names:
                    raise JakselError(
                        f"modul '{node.path}' nggak punya '{nama}', bestie. "
                        f"Yang ada: {', '.join(sorted(modul.names)) or '(kosong)'}",
                        node.line)
                env.define(nama, modul.names[nama])

    def _muat_modul_jaksel(self, full, node):
        """Muat file .jaksel ke namespace baru, kembalikan JakselModul."""
        self._loading.add(full)
        try:
            with open(full, "r", encoding="utf-8") as f:
                source = f.read()
            old_dir = self._file_dir
            self._file_dir = os.path.dirname(full)
            try:
                program = parse(lex(source, full))
                modul_env = Environment(parent=self.globals)
                self.exec_program(program, modul_env)
            finally:
                self._file_dir = old_dir
        finally:
            self._loading.discard(full)
        self._loaded.add(full)
        dasar = os.path.splitext(os.path.basename(full))[0]
        semua = dict(modul_env.vars)
        if modul_env.exports is not None:
            # ekspor eksplisit: cuma nama yang ditandai yang kelihatan
            hilang = [n for n in modul_env.exports if n not in semua]
            if hilang:
                raise JakselError(
                    f"modul '{dasar}' mengekspor {', '.join(hilang)} tapi "
                    f"nama itu nggak ada, bestie.", node.line)
            semua = {k: v for k, v in semua.items()
                     if k in modul_env.exports}
        modul = JakselModul(dasar, semua)
        self._modul_cache[full] = modul
        return modul

    def _import_python(self, node, env):
        """collab python "os" [sebagai o | ambil getcwd, ...]."""
        self._wajib_tidak_aman("collab python")
        nama_modul = node.py_module
        try:
            mod = importlib.import_module(nama_modul)
        except ImportError as e:
            raise JakselError(
                f"modul python '{nama_modul}' nggak ketemu, bestie: {e}",
                node.line)
        bungkus = JakselPyModul(nama_modul, mod)
        if node.ambil is not None:
            for nama in node.ambil:
                try:
                    attr = getattr(mod, nama)
                except AttributeError:
                    raise JakselError(
                        f"modul python '{nama_modul}' nggak punya '{nama}', "
                        "bestie.", node.line)
                env.define(nama, _py_ke_jaksel(attr, self))
            return
        env.define(node.alias or nama_modul.replace(".", "_"), bungkus)

    # -- expressions --
    def eval_expr(self, node, env):
        if isinstance(node, Literal):
            return node.value
        if isinstance(node, InterpString):
            return "".join(
                part if kind == "teks" else format_value(self.eval_expr(part, env))
                for kind, part in node.parts
            )
        if isinstance(node, Name):
            return env.get(node.id, node.line)
        if isinstance(node, ThisExpr):
            if not self._ini:
                raise JakselError(
                    "'ini' cuma bisa dipakai di dalam method, bestie.", node.line)
            return self._ini[-1]
        if isinstance(node, SuperExpr):
            if not self._ini:
                raise JakselError(
                    "'ortu' cuma bisa dipakai di dalam method, bestie.", node.line)
            inst = self._ini[-1]
            if inst.cls.parent is None:
                raise JakselError(
                    f"kelas '{inst.cls.name}' nggak punya induk, "
                    "nggak bisa pakai 'ortu'.", node.line)
            return SuperRef(inst, inst.cls.parent)
        if isinstance(node, ListLit):
            return [self.eval_expr(e, env) for e in node.elements]
        if isinstance(node, Comp):
            return self.eval_comp(node, env)
        if isinstance(node, DictLit):
            return {k: self.eval_expr(v, env) for k, v in node.pairs}
        if isinstance(node, UnaryOp):
            val = self.eval_expr(node.operand, env)
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise JakselError("minus cuma buat angka.", node.line)
            return -val
        if isinstance(node, NotOp):
            return not is_truthy(self.eval_expr(node.operand, env))
        if isinstance(node, BinOp):
            return self.eval_binop(node, env)
        if isinstance(node, ChainComp):
            # 1 < x < 10 — tiap operan dievaluasi sekali, short-circuit
            left = self.eval_expr(node.first, env)
            for op, expr in zip(node.ops, node.operands):
                right = self.eval_expr(expr, env)
                if not self._bandingkan(op, left, right, node.line):
                    return False
                left = right
            return True
        if isinstance(node, IfExpr):
            cond = self.eval_expr(node.cond, env)
            if is_truthy(cond):
                return self.eval_expr(node.then, env)
            return self.eval_expr(node.else_, env)
        if isinstance(node, Call):
            return self.eval_call(node, env)
        if isinstance(node, Index):
            return self.eval_index(node, env)
        if isinstance(node, Slice):
            return self.eval_slice(node, env)
        if isinstance(node, Attr):
            obj = self.eval_expr(node.obj, env)
            if obj is None and node.optional:
                return None  # zonk?.x = zonk, nggak error
            if isinstance(obj, JakselInstance):
                return self._attr_instance(obj, node.name, node.line,
                                           node.optional)
            if isinstance(obj, SuperRef):
                return self._attr_super(obj, node.name, node.line)
            if isinstance(obj, JakselModul):
                # u.nama: nama yang diimpor modul itu
                if node.name in obj.names:
                    return obj.names[node.name]
                if node.optional:
                    return None
                raise JakselError(
                    f"modul '{obj.name}' nggak punya '{node.name}', bestie. "
                    f"Yang ada: {', '.join(sorted(obj.names)) or '(kosong)'}",
                    node.line)
            if isinstance(obj, JakselClass):
                # Kelas.nama: method statik / atribut kelas / anggota enum
                if node.name in obj.attrs:
                    return obj.attrs[node.name]
                m = obj.methods.get(node.name)
                if m is not None and m.is_static:
                    return StaticMethod(obj, m)
                if m is not None:
                    raise JakselError(
                        f"'{node.name}' itu method biasa, panggil lewat "
                        f"objek '{obj.name}' dulu, bestie.", node.line)
                if node.optional:
                    return None
                raise JakselError(
                    f"kelas '{obj.name}' nggak punya '{node.name}', bestie.",
                    node.line)
            if isinstance(obj, JakselPyModul):
                try:
                    return _py_ke_jaksel(getattr(obj.module, node.name), self)
                except AttributeError:
                    if node.optional:
                        return None
                    raise JakselError(
                        f"modul python '{obj.name}' nggak punya "
                        f"'{node.name}', bestie.", node.line)
            if isinstance(obj, JakselPyObj):
                try:
                    return _py_ke_jaksel(getattr(obj.obj, node.name), self)
                except AttributeError:
                    if node.optional:
                        return None
                    raise JakselError(
                        f"objek python nggak punya atribut '{node.name}', "
                        "bestie.", node.line)
            if isinstance(obj, dict):
                if node.name in obj:
                    return obj[node.name]
                if node.name in _METHODS["kamus"]:
                    return MethodValue(obj, node.name)
                if node.optional:
                    return None
                raise JakselError(
                    f"kamus nggak punya kunci '{node.name}'.", node.line)
            if isinstance(obj, list) and node.name in _METHODS["daftar"]:
                return MethodValue(obj, node.name)
            if isinstance(obj, str) and node.name in _METHODS["teks"]:
                return MethodValue(obj, node.name)
            raise JakselError("akses titik cuma buat kamus/objek.", node.line)
        raise JakselError(f"ekspresi aneh: {type(node).__name__}")

    def _attr_instance(self, inst, name, line, optional=False):
        """obj.atribut: atribut instance dulu, lalu properti, lalu method."""
        if name in inst.attrs:
            return inst.attrs[name]
        prop = inst.cls.cari_property(name)
        if prop is not None:
            if prop.getter is None:
                raise JakselError(
                    f"properti '{name}' cuma bisa ditulis "
                    "(nggak ada 'ambil'), bestie.", line)
            return self._panggil_method(inst, prop.getter, [], line)
        m = inst.cls.cari_method(name)
        if m is not None:
            if m.is_static:
                return StaticMethod(inst.cls, m)
            return BoundMethod(inst, m)
        saran = mirip(name, list(inst.cls.semua_method().keys())
                      + list(inst.cls.properties.keys())
                      + list(inst.attrs.keys()))
        if optional:
            return None
        msg = (f"objek '{inst.cls.name}' nggak punya atribut/method "
               f"'{name}', bestie.")
        if saran:
            msg += f" Maksudnya '{saran}'?"
        raise JakselError(msg, line)

    def _attr_super(self, ref, name, line):
        """ortu.metode: cari method mulai dari kelas induk."""
        m = ref.parent_cls.cari_method(name)
        if m is not None:
            return BoundMethod(ref.instance, m)
        raise JakselError(
            f"kelas induk '{ref.parent_cls.name}' nggak punya method "
            f"'{name}', bestie.", line)

    def _coba_overload(self, op, left, right, line):
        """Coba method __tambah__ dkk; kembalikan _TIDAK_ADA kalau nggak ada."""
        nama = _OP_OVERLOAD.get(op)
        if nama is None:
            return _TIDAK_ADA
        if isinstance(left, JakselInstance):
            m = left.cls.cari_method(nama)
            if m is not None:
                return self._panggil_method(left, m, [right], line)
        if isinstance(right, JakselInstance):
            m = right.cls.cari_method(nama)
            if m is not None:
                return self._panggil_method(right, m, [left], line)
        return _TIDAK_ADA

    def _bandingkan(self, op, left, right, line):
        """Satu operasi perbandingan: == != dalam < > <= >=."""
        if op in ("==", "!="):
            eq = left == right and type(left) is type(right) or left == right
            # samakan perilaku Python untuk bool vs angka, tapi bedakan tipe lain
            if type(left) is not type(right) and not (
                    isinstance(left, (int, float)) and isinstance(right, (int, float))):
                eq = False
            return eq if op == "==" else not eq
        if op == "dalam":
            # membership test: x dalam daftar/teks/kamus
            if isinstance(right, dict):
                return left in right
            if isinstance(right, (list, str)):
                return left in right
            raise JakselError(
                f"'dalam' cuma buat daftar/teks/kamus, "
                f"bukan {self._tname(right)}.", line)
        # < > <= >=
        if isinstance(left, bool) or isinstance(right, bool):
            raise JakselError(f"'{op}' nggak buat valid/gimmick.", line)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            pass
        elif isinstance(left, str) and isinstance(right, str):
            pass
        else:
            raise JakselError(
                f"'{op}' nggak bisa buat {self._tname(left)} lawan {self._tname(right)}.", line)
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        return left >= right

    def eval_binop(self, node, env):
        op = node.op
        if op == "dan":
            left = self.eval_expr(node.left, env)
            return left if not is_truthy(left) else self.eval_expr(node.right, env)
        if op == "atau":
            left = self.eval_expr(node.left, env)
            return left if is_truthy(left) else self.eval_expr(node.right, env)
        if op == "??":
            left = self.eval_expr(node.left, env)
            return left if left is not None else self.eval_expr(node.right, env)
        left = self.eval_expr(node.left, env)
        right = self.eval_expr(node.right, env)
        line = node.line

        # operator overloading: method __tambah__ dkk di kelas
        overload = self._coba_overload(op, left, right, line)
        if overload is not _TIDAK_ADA:
            return overload

        if op == "+":
            if isinstance(left, bool) or isinstance(right, bool):
                raise JakselError("valid/gimmick nggak bisa ditambah.", line)
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            raise JakselError(
                f"'+' nggak bisa buat {self._tname(left)} + {self._tname(right)}.", line)
        if op in ("-", "*", "/", "%"):
            if (isinstance(left, bool) or isinstance(right, bool)
                    or not isinstance(left, (int, float))
                    or not isinstance(right, (int, float))):
                raise JakselError(f"'{op}' cuma buat angka, bestie.", line)
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                if right == 0:
                    raise JakselError("bagi nol? Gimmick banget.", line)
                return left / right
            if right == 0:
                raise JakselError("modulo nol? Gimmick banget.", line)
            return left % right
        if op in ("==", "!=", "dalam", "<", ">", "<=", ">="):
            return self._bandingkan(op, left, right, line)

    @staticmethod
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
        if isinstance(v, JakselClass):
            return f"kelas {v.name}"
        if isinstance(v, JakselInstance):
            return f"objek {v.cls.name}"
        return "nilai"

    def call_method(self, obj, name, args, line, kwargs=None):
        """Panggil obj.name(args): method bawaan, modul, kelas, atau Python."""
        kwargs = kwargs or {}
        if isinstance(obj, JakselInstance):
            if name in obj.attrs:
                val = obj.attrs[name]
                if isinstance(val, (JakselFunction, BuiltinFunction,
                                    BoundMethod, StaticMethod, MethodValue,
                                    JakselPyCallable)):
                    return self._panggil_nilai(val, args, line, kwargs)
                raise JakselError(
                    f"'{name}' di objek '{obj.cls.name}' bukan fungsi, "
                    "nggak bisa dipanggil.", line)
            prop = obj.cls.cari_property(name)
            if prop is not None and prop.getter is not None:
                val = self._panggil_method(obj, prop.getter, [], line)
                return self._panggil_nilai(val, args, line, kwargs)
            m = obj.cls.cari_method(name)
            if m is not None:
                if m.is_static:
                    return self._panggil_method(None, m, args, line, kwargs)
                return self._panggil_method(obj, m, args, line, kwargs)
            saran = mirip(name, list(obj.cls.semua_method().keys())
                          + list(obj.cls.properties.keys())
                          + list(obj.attrs.keys()))
            msg = (f"objek '{obj.cls.name}' nggak punya method '{name}', bestie.")
            if saran:
                msg += f" Maksudnya '{saran}'?"
            raise JakselError(msg, line)
        if isinstance(obj, JakselModul):
            # u.nama(args): nama dari modul itu yang bisa dipanggil
            if name in obj.names:
                return self._panggil_nilai(obj.names[name], args, line, kwargs)
            raise JakselError(
                f"modul '{obj.name}' nggak punya '{name}', bestie.", line)
        if isinstance(obj, JakselClass):
            # Kelas.buat(args): cuma method statik yang boleh
            m = obj.methods.get(name)
            if m is not None and m.is_static:
                return self._panggil_method(None, m, args, line, kwargs)
            if name in obj.attrs:
                return self._panggil_nilai(obj.attrs[name], args, line, kwargs)
            raise JakselError(
                f"'{name}' bukan method statik kelas '{obj.name}', bestie. "
                "Kasih 'statik' biar bisa dipanggil lewat kelas.", line)
        if isinstance(obj, (JakselPyModul, JakselPyObj)):
            sumber = obj.module if isinstance(obj, JakselPyModul) else obj.obj
            try:
                target = getattr(sumber, name)
            except AttributeError:
                raise JakselError(
                    f"objek python nggak punya '{name}', bestie.", line)
            if not callable(target):
                raise JakselError(
                    f"'{name}' di objek python bukan fungsi, bestie.", line)
            return self._panggil_python(JakselPyCallable(target, self),
                                       args, kwargs, line)
        if isinstance(obj, SuperRef):
            m = obj.parent_cls.cari_method(name)
            if m is not None:
                return self._panggil_method(obj.instance, m, args, line, kwargs)
            raise JakselError(
                f"kelas induk '{obj.parent_cls.name}' nggak punya method "
                f"'{name}', bestie.", line)
        tipe = _tipe_method(obj)
        tabel = _METHODS.get(tipe, {}) if tipe else {}
        if tipe and name in tabel:
            if kwargs:
                raise JakselError(
                    f"method bawaan '{name}' nggak terima argumen bernama, "
                    "bestie.", line)
            try:
                return tabel[name](obj, args)
            except JakselError as e:
                raise JakselError(e.raw, line)
        # bukan method: mungkin fungsi yang disimpan sebagai nilai di kamus
        if isinstance(obj, dict) and name in obj:
            val = obj[name]
            if isinstance(val, (JakselFunction, BuiltinFunction, MethodValue,
                                JakselPyCallable)):
                return self._panggil_nilai(val, args, line, kwargs)
            raise JakselError(
                f"'{name}' di kamus bukan fungsi, nggak bisa dipanggil.", line)
        saran = mirip(name, list(tabel.keys())
                      + (list(obj.keys()) if isinstance(obj, dict) else []))
        msg = f"{self._tname(obj)} nggak punya method '{name}', bestie."
        if saran:
            msg += f" Maksudnya '{saran}'?"
        raise JakselError(msg, line)

    def _panggil_nilai(self, func, args, line, kwargs=None):
        """Panggil nilai fungsi (bawaan / talent / method / kelas / python)."""
        kwargs = kwargs or {}
        if isinstance(func, BuiltinFunction):
            if kwargs:
                raise JakselError(
                    f"builtin '{func.name}' nggak terima argumen bernama, "
                    "bestie.", line)
            try:
                return func.func(*args)
            except TypeError:
                raise JakselError(
                    f"panggil '{func.name}' argumentnya nggak pas, bestie.", line)
        if isinstance(func, JakselFunction):
            return self._panggil_func(func, args, line, func.name, kwargs)
        if isinstance(func, BoundMethod):
            return self._panggil_method(func.instance, func.func, args, line,
                                       kwargs)
        if isinstance(func, StaticMethod):
            return self._panggil_method(None, func.func, args, line, kwargs)
        if isinstance(func, MethodValue):
            return self.call_method(func.obj, func.name, args, line, kwargs)
        if isinstance(func, JakselClass):
            if kwargs:
                raise JakselError(
                    f"panggil kelas '{func.name}' nggak bisa pakai argumen "
                    "bernama, bestie.", line)
            return self._instansiasi(func, args, line)
        if isinstance(func, JakselPyCallable):
            return self._panggil_python(func, args, kwargs, line)
        raise JakselError(
            f"'{format_value(func)}' bukan fungsi, nggak bisa dipanggil.", line)

    def _panggil_func(self, func, args, line, nama_frame, kwargs=None):
        """Panggil JakselFunction: bind posisi + bernama + default + ...sisa."""
        kwargs = dict(kwargs or {})
        params = func.params
        if len(args) > len(params) and func.variadic is None:
            raise JakselError(
                f"talent '{func.name}' butuh {len(params)} argumen, "
                f"dikasih {len(args)}.", line)
        bound = {}
        for i, p in enumerate(params):
            if i < len(args):
                if p in kwargs:
                    raise JakselError(
                        f"parameter '{p}' dikasih dua kali (posisi + nama), "
                        "bestie.", line)
                bound[p] = args[i]
        for nama, v in kwargs.items():
            if nama not in params:
                raise JakselError(
                    f"talent '{func.name}' nggak punya parameter '{nama}', "
                    "bestie.", line)
            if nama in bound:
                raise JakselError(
                    f"parameter '{nama}' dikasih dua kali, bestie.", line)
            bound[nama] = v
        for p in params:
            if p not in bound:
                if p in func.defaults:
                    bound[p] = func.defaults[p]
                else:
                    raise JakselError(
                        f"talent '{func.name}' butuh argumen '{p}', bestie.",
                        line)
        call_env = Environment(parent=func.closure)
        for p in params:
            call_env.define(p, bound[p])
        if func.variadic is not None:
            call_env.define(func.variadic, list(args[len(params):]))
        self._stack.append((nama_frame, line))
        try:
            try:
                self.exec_block(func.body, call_env)
            except _Return as r:
                return r.value
            return None
        except JakselError as e:
            if e.trace is None:
                e.trace = list(self._stack)
            raise
        finally:
            self._stack.pop()

    def _panggil_method(self, inst, func, args, line, kwargs=None):
        """Panggil method; inst=None buat method statik (tanpa 'ini')."""
        nama = func.name if inst is None else f"{inst.cls.name}.{func.name}"
        if inst is None:
            return self._panggil_func(func, args, line, nama, kwargs)
        self._ini.append(inst)
        try:
            return self._panggil_func(func, args, line, nama, kwargs)
        finally:
            self._ini.pop()

    def _panggil_python(self, pyc, args, kwargs, line):
        """Panggil fungsi Python: konversi argumen & hasil otomatis."""
        py_args = [_jaksel_ke_py(a, self) for a in args]
        py_kwargs = {k: _jaksel_ke_py(v, self) for k, v in kwargs.items()}
        try:
            hasil = pyc.func(*py_args, **py_kwargs)
        except Exception as e:  # noqa: BLE001 - dibungkus jadi JakselError
            raise JakselError(
                f"error dari Python "
                f"({getattr(pyc.func, '__name__', '?')}): {e}", line)
        return _py_ke_jaksel(hasil, self)

    def _instansiasi(self, cls, args, line):
        """Kelas(args): bikin objek, panggil 'lahir' kalau ada."""
        inst = JakselInstance(cls)
        inst._interp = self
        lahir = cls.cari_method("lahir")
        if lahir is not None:
            if lahir.is_static:
                raise JakselError(
                    "method 'lahir' nggak boleh statik, bestie.", line)
            self._panggil_method(inst, lahir, args, line)
        elif cls.name == "Error":
            # Error("pesan") tanpa lahir: simpan pesan langsung
            inst.attrs["pesan"] = args[0] if len(args) == 1 else (
                list(args) if args else "")
        elif args:
            raise JakselError(
                f"kelas '{cls.name}' nggak punya 'lahir' tapi dipanggil "
                f"pakai {len(args)} argumen.", line)
        return inst

    def eval_call(self, node, env):
        if isinstance(node.func, Attr) and node.func.optional:
            # obj?.method(...): kalo obj zonk, hasilnya zonk (args nggak dievaluasi)
            obj = self.eval_expr(node.func.obj, env)
            if obj is None:
                return None
        args, kwargs = self._eval_argumen(node, env)
        if isinstance(node.func, Attr):
            # obj.method(args): jangan eval Attr sebagai akses kamus
            obj = self.eval_expr(node.func.obj, env)
            return self.call_method(obj, node.func.name, args, node.line,
                                   kwargs)
        func = self.eval_expr(node.func, env)
        return self._panggil_nilai(func, args, node.line, kwargs)

    def _eval_argumen(self, node, env):
        """Kembalikan (args, kwargs); sebar ...daftar / ...kamus."""
        args = []
        kwargs = {}
        for a in node.args:
            if isinstance(a, Spread):
                v = self.eval_expr(a.value, env)
                if isinstance(v, (list, tuple)):
                    args.extend(v)
                elif isinstance(v, dict):
                    for k, x in v.items():
                        kwargs[str(k)] = x
                else:
                    raise JakselError(
                        "'...' cuma bisa nyebar daftar/kamus, bestie.",
                        node.line)
            else:
                args.append(self.eval_expr(a, env))
        for nama, vnode in node.kwargs:
            if nama in kwargs:
                raise JakselError(
                    f"argumen '{nama}' dikasih dua kali, bestie.", node.line)
            kwargs[nama] = self.eval_expr(vnode, env)
        return args, kwargs

    def eval_comp(self, node, env):
        iterable = self.eval_expr(node.iterable, env)
        line = node.line
        if isinstance(iterable, dict):
            iterable = list(iterable.keys())
        if not isinstance(iterable, (list, str, tuple)):
            raise JakselError(
                "comprehension butuh daftar/teks/kamus.", line)
        hasil = []
        # scope sendiri biar variabel loop nggak bocor keluar
        sub = Environment(parent=env)
        for item in iterable:
            sub.define(node.var, item)
            if node.cond is not None:
                if not is_truthy(self.eval_expr(node.cond, sub)):
                    continue
            hasil.append(self.eval_expr(node.expr, sub))
        return hasil

    def eval_slice(self, node, env):
        obj = self.eval_expr(node.obj, env)
        line = node.line
        if not isinstance(obj, (list, str)):
            raise JakselError("yang bisa di-slice cuma daftar/teks.", line)

        def _int_atau_zonk(v, nama):
            if v is None:
                return None
            v = self.eval_expr(v, env)
            if isinstance(v, bool) or not isinstance(v, int):
                raise JakselError(f"batas slice '{nama}' harus angka bulat.", line)
            return v

        mulai = _int_atau_zonk(node.mulai, "mulai")
        akhir = _int_atau_zonk(node.akhir, "akhir")
        langkah = _int_atau_zonk(node.langkah, "langkah")
        try:
            return obj[mulai:akhir:langkah]
        except Exception:
            raise JakselError("slice gagal, cek batasnya.", line)

    def eval_index(self, node, env):
        obj = self.eval_expr(node.obj, env)
        idx = self.eval_expr(node.index, env)
        line = node.line
        if isinstance(obj, (list, str)):
            if isinstance(idx, bool) or not isinstance(idx, int):
                raise JakselError("index harus angka bulat.", line)
            if idx < 0:
                idx += len(obj)
            if not 0 <= idx < len(obj):
                raise JakselError("index kelewat batas, bestie.", line)
            return obj[idx]
        if isinstance(obj, dict):
            key = str(idx)
            if key in obj:
                return obj[key]
            raise JakselError(f"kamus nggak punya kunci '{key}'.", line)
        raise JakselError("yang bisa di-index cuma daftar/teks/kamus.", line)


# ---------------- Tugas paralel ----------------
# Helper buat luncurkan(): bikin interpreter anak dengan snapshot globals.

def _salin_env(env):
    """Salin rantai Environment (struktur baru, nilai dangkal).

    Dipakai tugas paralel: tulis ke variabel global di dalam tugas
    nggak bocor ke interpreter induk.
    """
    if env is None:
        return None
    baru = Environment(parent=_salin_env(env.parent))
    baru.vars.update(env.vars)
    return baru


def _anak_interpreter(induk):
    """Bikin Interpreter anak buat satu tugas luncurkan()."""
    anak = Interpreter(aman=induk._aman)
    anak._file_dir = induk._file_dir
    anak._argv = list(induk._argv)
    anak.globals = _salin_env(induk.globals)
    return anak
