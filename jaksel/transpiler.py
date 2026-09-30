"""Transpiler JakselScript -> Python.

Menerjemahkan AST JakselScript menjadi kode Python yang ekuivalen secara
semantik (termasuk pesan error gaya Jaksel dan perilaku yolo/yaudah).
"""

import os

from .lexer import lex
from .parser import (
    Assign, Attr, BinOp, Block, BreakStmt, Call, ChainComp, ClassDef, Comp,
    ContinueStmt, Destructure, DictLit, EnumDef, ExitStmt, ExportStmt,
    ExprStmt, ForStmt, FuncDef, IfExpr, IfStmt, ImportStmt, Index,
    InterpString, ListLit, Literal, MatchStmt, Name, Node, NotOp, PatBind,
    PatDict, PatEnum, PatList, PatLit, PatType, PatWild, Program, PropertyDef,
    ReturnStmt, Slice, Spread, SuperExpr, ThisExpr, ThrowStmt, TryStmt,
    UnaryOp, VarDecl, WhileStmt, parse,
)

HEADER = '''\
"""Hasil terjemahan JakselScript -> Python. Jangan diedit manual, bestie."""
import csv as _csv
import datetime as _datetime
import difflib as _difflib
import json as _json
import os as _os
import random as _random
import re as _re
import subprocess as _subprocess
import sys as _sys
import threading as _threading
import time as _time
import urllib.parse as _urlparse
import urllib.request as _urlreq
import urllib.error as _urlerr


class _RedFlag(Exception):
    """Error JakselScript. .nilai membawa nilai asli 'red_flag'
    (dipakai cabang 'yaudah <Tipe> e' buat ngecek tipe error)."""

    def __init__(self, pesan, nilai=None):
        super().__init__(pesan)
        self.nilai = nilai


class _JakselBase:
    """Kelas dasar semua kelas JakselScript hasil transpile."""

    def __init__(self, *a):
        if a:
            raise _RedFlag("kelas '%s' nggak punya 'lahir' tapi dipanggil "
                           "pakai argumen, bestie." % type(self).__name__)


class _JakselError(_JakselBase):
    """Kelas dasar hierarki error: Error, HttpError, dkk.

    Error("pesan") -> .pesan = "pesan"; Error(a, b) -> .pesan = [a, b]."""

    def __init__(self, *a):
        self.pesan = a[0] if len(a) == 1 else (list(a) if a else "")


def _red_flag_nilai(v):
    """Lempar nilai red_flag dengan pesan + nilai asli (kayak interpreter)."""
    if isinstance(v, _JakselError):
        raise _RedFlag("%s: %s" % (type(v).__name__, _fmt(v.pesan)), v)
    if isinstance(v, _JakselBase):
        raise _RedFlag(_fmt(v), v)
    raise _RedFlag(_fmt(v), None)


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


def _tipe(v):
    if v is None:
        return "zonk"
    if isinstance(v, bool):
        return "valid/gimmick"
    if isinstance(v, (int, float)):
        return "angka"
    if isinstance(v, str):
        return "teks"
    if isinstance(v, list):
        return "daftar"
    if isinstance(v, dict):
        return "kamus"
    if isinstance(v, _JakselBase):
        return type(v).__name__
    if isinstance(v, type) and issubclass(v, _JakselBase):
        return "kelas"
    if callable(v):
        return "fungsi"
    return "nilai"


def _fmt(v, _guard=None):
    if v is True:
        return "valid"
    if v is False:
        return "gimmick"
    if v is None:
        return "zonk"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(e, _guard) for e in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f'"{k}": {_fmt(x, _guard)}' for k, x in v.items()) + "}"
    if isinstance(v, _JakselBase):
        _guard = _guard or set()
        if id(v) in _guard:
            return "<%s>" % type(v).__name__
        _tampil = getattr(v, "tampil", None)
        if callable(_tampil):
            _guard.add(id(v))
            try:
                return _fmt(_tampil(), _guard)
            except Exception:
                return "<%s>" % type(v).__name__
            finally:
                _guard.discard(id(v))
        return "<%s>" % type(v).__name__
    if isinstance(v, _EnumMember):
        return repr(v)
    if isinstance(v, type) and issubclass(v, _JakselBase):
        return "<kelas %s>" % v.__name__
    if isinstance(v, type) and issubclass(v, _EnumBase):
        return "<enum %s>" % v.__name__
    return str(v)


def _spill(*args):
    print(" ".join(_fmt(a) for a in args))


def _angka(x):
    try:
        if isinstance(x, bool):
            raise ValueError
        if isinstance(x, (int, float)):
            return x
        s = str(x).strip()
        return int(s) if "." not in s else float(s)
    except (ValueError, TypeError):
        raise _RedFlag("'%s' nggak bisa jadi angka." % _fmt(x))


def _panjang(x):
    if isinstance(x, (str, list, dict)):
        return len(x)
    raise _RedFlag("panjang() cuma bisa buat teks/daftar/kamus.")


def _healing(det):
    if isinstance(det, bool) or not isinstance(det, (int, float)):
        raise _RedFlag("healing() butuh angka detik, bestie.")
    _time.sleep(float(det))


class _Tugas:
    """Hasil luncurkan(): thread + hasil."""

    def __init__(self, nama, fn, args):
        self.name = nama
        self._hasil = None
        self._error = None
        self._event = _threading.Event()

        def _jalan():
            try:
                self._hasil = fn(*args)
            except Exception as e:
                self._error = e
            finally:
                self._event.set()

        self._thread = _threading.Thread(target=_jalan, daemon=True,
                                         name="jaksel-%s" % nama)
        self._thread.start()


def _luncurkan(fn, args=None):
    if not callable(fn):
        raise _RedFlag("luncurkan() butuh fungsi/talent, bestie.")
    daftar = args if args is not None else []
    if not isinstance(daftar, list):
        raise _RedFlag("argumen kedua luncurkan() harus daftar, bestie.")
    return _Tugas(getattr(fn, "__name__", "tugas"), fn, list(daftar))


def _tunggu(tugas):
    if not isinstance(tugas, _Tugas):
        raise _RedFlag("tunggu() butuh hasil luncurkan(), bestie.")
    tugas._event.wait()
    if tugas._error is not None:
        raise tugas._error
    return tugas._hasil


def _tunggu_semua(daftar):
    if not isinstance(daftar, list) or any(
            not isinstance(t, _Tugas) for t in daftar):
        raise _RedFlag("tunggu_semua() butuh daftar tugas, bestie.")
    return [_tunggu(t) for t in daftar]


def _cocok_tipe(v, k, nama_pola):
    """Pola tipe 'Tipe x': cek instanceof (termasuk enum)."""
    if isinstance(k, type) and issubclass(k, _EnumBase):
        return (isinstance(v, _EnumMember) and v._enum == k._enum_name
                if hasattr(k, "_enum_name") else False)
    if isinstance(k, type):
        return isinstance(v, k)
    raise _RedFlag("pola '%s' bukan kelas, bestie." % nama_pola)


def _cocok_enum(v, enum_name, member_name):
    """Pola enum 'Warna.MERAH': cek anggota enum yang pas."""
    return (isinstance(v, _EnumMember) and v._enum == enum_name
            and v._member == member_name)


def _ambil_modul(ns, path, nama):
    """Ambil satu nama dari namespace modul (collab ... ambil nama)."""
    if nama not in ns:
        raise _RedFlag("modul '%s' nggak punya '%s', bestie. Yang ada: %s"
                       % (path, nama, ", ".join(sorted(ns)) or "(kosong)"))
    return ns[nama]


def _ambil_modul_py(mod, nama, path):
    """Ambil satu nama dari modul Python (collab python ... ambil nama)."""
    if not hasattr(mod, nama):
        raise _RedFlag("modul python '%s' nggak punya '%s', bestie."
                       % (path, nama))
    return getattr(mod, nama)


def _acak(*args):
    if len(args) == 0:
        return _random.random()
    if len(args) == 1:
        b = args[0]
        if isinstance(b, bool) or not isinstance(b, int):
            raise _RedFlag("acak() butuh angka bulat, bestie.")
        return _random.randrange(b)
    if len(args) == 2:
        a, b = args
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (a, b)):
            raise _RedFlag("acak() butuh angka bulat, bestie.")
        return _random.randrange(a, b)
    raise _RedFlag("acak() maksimal 2 argumen, bestie.")


def _tambah(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        raise _RedFlag("valid/gimmick nggak bisa ditambah.")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + b
    if isinstance(a, str) and isinstance(b, str):
        return a + b
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    raise _RedFlag("'+' nggak bisa buat %s + %s." % (_tname(a), _tname(b)))


def _arit(a, b, op):
    if (isinstance(a, bool) or isinstance(b, bool)
            or not isinstance(a, (int, float))
            or not isinstance(b, (int, float))):
        raise _RedFlag("'%s' cuma buat angka, bestie." % op)
    if op == "-":
        return a - b
    return a * b


def _kurang(a, b):
    return _arit(a, b, "-")


def _kali(a, b):
    return _arit(a, b, "*")


def _bagi(a, b):
    if (isinstance(a, bool) or isinstance(b, bool)
            or not isinstance(a, (int, float))
            or not isinstance(b, (int, float))):
        raise _RedFlag("'/' cuma buat angka, bestie.")
    if b == 0:
        raise _RedFlag("bagi nol? Gimmick banget.")
    return a / b


def _mod(a, b):
    if (isinstance(a, bool) or isinstance(b, bool)
            or not isinstance(a, (int, float))
            or not isinstance(b, (int, float))):
        raise _RedFlag("'%' cuma buat angka, bestie.")
    if b == 0:
        raise _RedFlag("modulo nol? Gimmick banget.")
    return a % b


def _neg(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise _RedFlag("minus cuma buat angka.")
    return -x


def _eq(a, b):
    eq = a == b and type(a) is type(b) or a == b
    if type(a) is not type(b) and not (
            isinstance(a, (int, float)) and isinstance(b, (int, float))):
        eq = False
    return eq


def _banding(a, b, op):
    if isinstance(a, bool) or isinstance(b, bool):
        raise _RedFlag("'%s' nggak buat valid/gimmick." % op)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        pass
    elif isinstance(a, str) and isinstance(b, str):
        pass
    else:
        raise _RedFlag("'%s' nggak bisa buat %s lawan %s."
                       % (op, _tname(a), _tname(b)))
    return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]


def _ov_bin(a, b, dunder, biasa):
    """Operator biner dengan dukungan overloading __tambah__ dkk.

    Reflected: method di operan kanan dipanggil dengan operan kiri
    sebagai argumen (kayak interpreter)."""
    m = getattr(a, dunder, None)
    if callable(m):
        return m(b)
    m = getattr(b, dunder, None)
    if callable(m):
        return m(a)
    return biasa(a, b)


def _tambah_ov(a, b):
    return _ov_bin(a, b, "__tambah__", _tambah)


def _kurang_ov(a, b):
    return _ov_bin(a, b, "__kurang__", _kurang)


def _kali_ov(a, b):
    return _ov_bin(a, b, "__kali__", _kali)


def _bagi_ov(a, b):
    return _ov_bin(a, b, "__bagi__", _bagi)


def _mod_ov(a, b):
    return _ov_bin(a, b, "__sisa__", _mod)


def _eq_ov(a, b, op):
    """== / != dengan dukungan __sama__ / __beda__ (kayak interpreter)."""
    dunder = "__sama__" if op == "==" else "__beda__"
    m = getattr(a, dunder, None)
    if callable(m):
        return bool(m(b))
    m = getattr(b, dunder, None)
    if callable(m):
        return bool(m(a))
    eq = _eq(a, b)
    return eq if op == "==" else not eq


_DUNDER_BANDING = {
    "<": "__kurang_dari__",
    ">": "__lebih_dari__",
    "<=": "__kurang_dari_sama__",
    ">=": "__lebih_dari_sama__",
}


def _banding_ov(a, b, op):
    """< > <= >= dengan dukungan __kurang_dari__ dkk (kayak interpreter:
    dunder yang sama dicoba di operan kanan dengan operan kiri
    sebagai argumen)."""
    dunder = _DUNDER_BANDING[op]
    m = getattr(a, dunder, None)
    if callable(m):
        return bool(m(b))
    m = getattr(b, dunder, None)
    if callable(m):
        return bool(m(a))
    return _banding(a, b, op)


def _dalam(a, b):
    if isinstance(b, dict):
        return a in b
    if isinstance(b, (list, str)):
        return a in b
    raise _RedFlag("'dalam' cuma buat daftar/teks/kamus, bukan %s." % _tname(b))


def _coalesce(a, b_fn):
    # '??': kanan cuma dievaluasi kalo kiri zonk (short-circuit)
    return a if a is not None else b_fn()


def _jiter(it):
    # iterable buat comprehension: kamus -> kunci-kuncinya (kayak stalk)
    if isinstance(it, dict):
        return list(it.keys())
    if isinstance(it, (list, str, tuple)):
        return it
    raise _RedFlag("comprehension butuh daftar/teks/kamus.")


def _jchain(vals, ops):
    # perbandingan berantai: tiap operan dievaluasi sekali (sudah jadi list)
    for i, op in enumerate(ops):
        a, b = vals[i], vals[i + 1]
        if op in ("==", "!="):
            ok = _eq_ov(a, b, op)
        elif op == "dalam":
            ok = _dalam(a, b)
        else:
            ok = _banding_ov(a, b, op)
        if not ok:
            return False
    return True


def _idx(obj, i):
    if isinstance(obj, (list, str)):
        if isinstance(i, bool) or not isinstance(i, int):
            raise _RedFlag("index harus angka bulat.")
        if i < 0:
            i += len(obj)
        if not 0 <= i < len(obj):
            raise _RedFlag("index kelewat batas, bestie.")
        return obj[i]
    if isinstance(obj, dict):
        key = str(i)
        if key in obj:
            return obj[key]
        raise _RedFlag("kamus nggak punya kunci '%s'." % key)
    raise _RedFlag("yang bisa di-index cuma daftar/teks/kamus.")


def _slice(obj, mulai, akhir, langkah):
    if not isinstance(obj, (list, str)):
        raise _RedFlag("yang bisa di-slice cuma daftar/teks.")
    for nama, v in (("mulai", mulai), ("akhir", akhir), ("langkah", langkah)):
        if v is not None and (isinstance(v, bool) or not isinstance(v, int)):
            raise _RedFlag("batas slice '%s' harus angka bulat." % nama)
    try:
        return obj[mulai:akhir:langkah]
    except Exception:
        raise _RedFlag("slice gagal, cek batasnya.")


def _setidx(obj, i, v):
    if isinstance(obj, list):
        if isinstance(i, bool) or not isinstance(i, int):
            raise _RedFlag("index daftar harus angka bulat.")
        if i < 0:
            i += len(obj)
        if not 0 <= i < len(obj):
            raise _RedFlag("index daftar kelewat batas, bestie.")
        obj[i] = v
        return
    if isinstance(obj, dict):
        obj[str(i)] = v
        return
    raise _RedFlag("yang bisa di-index cuma daftar/kamus.")


def _attr(obj, name):
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
        raise _RedFlag("kamus nggak punya kunci '%s'." % name)
    if isinstance(obj, _JakselBase):
        return _mvalue(obj, name)
    raise _RedFlag("akses titik cuma buat kamus/objek.")


def _setattr(obj, name, v):
    if isinstance(obj, dict):
        obj[name] = v
        return
    if isinstance(obj, _JakselBase):
        setattr(obj, name, v)
        return
    raise _RedFlag("atribut cuma bisa diset di kamus/objek.")


class _MethodValue:
    """Method yang nempel ke nilai (mis. buah.tambah), bisa dipanggil."""

    def __init__(self, obj, name):
        self.obj, self.name = obj, name

    def __call__(self, *args):
        return _method(self.obj, self.name, *args)

    def __repr__(self):
        return "<method '%s'>" % self.name


_METHOD_NAMES = {
    "daftar": {"tambah", "buang", "sisipkan", "urut", "balik", "gabung", "salin"},
    "teks": {"besar", "kecil", "potong", "ganti", "pisah",
             "mulai_dengan", "berakhir_dengan"},
    "kamus": {"kunci", "nilai", "ambil", "hapus"},
}


def _mvalue(obj, name):
    if isinstance(obj, _JakselBase):
        if hasattr(obj, name):
            return getattr(obj, name)
        _saran = _difflib.get_close_matches(
            name, [m for m in dir(obj) if not m.startswith("_")],
            n=1, cutoff=0.6)
        _msg = "objek '%s' nggak punya atribut/method '%s', bestie." % (
            type(obj).__name__, name)
        if _saran:
            _msg += " Maksudnya '%s'?" % _saran[0]
        raise _RedFlag(_msg)
    t = _tname(obj)
    kunci = {"daftar": "daftar", "teks": "teks", "kamus": "kamus"}.get(t)
    if kunci is None:
        # objek Python lain (modul, enum, dsb): getattr langsung
        try:
            return getattr(obj, name)
        except AttributeError:
            raise _RedFlag("akses titik cuma buat kamus/objek, bestie.")
    if kunci == "kamus" and name in obj:
        return obj[name]
    if name in _METHOD_NAMES[kunci]:
        return _MethodValue(obj, name)
    if kunci == "kamus":
        raise _RedFlag("kamus nggak punya kunci '%s'." % name)
    raise _RedFlag("akses titik cuma buat kamus.")


def _method_opt(obj, name, *args):
    # '?.' buat method call — obj zonk / method hilang = zonk
    if obj is None:
        return None
    try:
        return _method(obj, name, *args)
    except _RedFlag as e:
        if "nggak punya" in str(e):
            return None
        raise


def _mvalue_opt(obj, name):
    # '?.' — zonk?.x = zonk; kunci/atribut hilang juga zonk (nggak error)
    if obj is None:
        return None
    try:
        return _mvalue(obj, name)
    except _RedFlag as e:
        msg = str(e)
        if "nggak punya" in msg or "nggak ada" in msg:
            return None
        raise


def _nargs(nama, args, mn, mx):
    if not mn <= len(args) <= mx:
        perlu = str(mn) if mn == mx else "%d-%d" % (mn, mx)
        raise _RedFlag("%s() butuh %s argumen, bestie." % (nama, perlu))


def _jtruthy(v):
    if v is None or v is False:
        return False
    if v is True:
        return True
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, (str, list, dict)):
        return len(v) > 0
    return True


def _rentang(*args):
    if not 1 <= len(args) <= 3:
        raise _RedFlag("rentang() butuh 1-3 angka, bestie.")
    for a in args:
        if isinstance(a, bool) or not isinstance(a, int):
            raise _RedFlag("rentang() cuma mau angka bulat, bestie.")
    return list(range(*args))


def _method(obj, name, *args):
    """Dispatcher method: obj.nama(args), semantik = interpreter."""
    if isinstance(obj, _JakselBase):
        if hasattr(obj, name):
            _v = getattr(obj, name)
            if callable(_v):
                return _v(*args)
            raise _RedFlag("'%s' di objek '%s' bukan fungsi, nggak bisa "
                           "dipanggil." % (name, type(obj).__name__))
        _saran = _difflib.get_close_matches(
            name, [m for m in dir(obj) if not m.startswith("_")],
            n=1, cutoff=0.6)
        _msg = "objek '%s' nggak punya method '%s', bestie." % (
            type(obj).__name__, name)
        if _saran:
            _msg += " Maksudnya '%s'?" % _saran[0]
        raise _RedFlag(_msg)
    if isinstance(obj, list):
        if name == "tambah":
            _nargs("tambah", args, 1, 1)
            obj.append(args[0])
            return obj
        if name == "buang":
            _nargs("buang", args, 0, 1)
            if not obj:
                raise _RedFlag("daftarnya kosong, nggak ada yang bisa dibuang.")
            i = args[0] if args else -1
            if isinstance(i, bool) or not isinstance(i, int):
                raise _RedFlag("buang() butuh index angka bulat.")
            if i < 0:
                i += len(obj)
            if not 0 <= i < len(obj):
                raise _RedFlag("index buang() kelewat batas, bestie.")
            return obj.pop(i)
        if name == "sisipkan":
            _nargs("sisipkan", args, 2, 2)
            i = args[0]
            if isinstance(i, bool) or not isinstance(i, int):
                raise _RedFlag("sisipkan() butuh index angka bulat.")
            obj.insert(i, args[1])
            return obj
        if name == "urut":
            _nargs("urut", args, 0, 0)
            try:
                obj.sort()
            except TypeError:
                raise _RedFlag("daftarnya campur aduk, nggak bisa diurut, bestie.")
            return obj
        if name == "balik":
            _nargs("balik", args, 0, 0)
            obj.reverse()
            return obj
        if name == "gabung":
            _nargs("gabung", args, 1, 1)
            p = args[0]
            if not isinstance(p, str):
                raise _RedFlag("gabung() butuh pemisah teks, bestie.")
            return p.join(_fmt(e) for e in obj)
        if name == "salin":
            _nargs("salin", args, 0, 0)
            return list(obj)
    elif isinstance(obj, str):
        if name == "besar":
            _nargs("besar", args, 0, 0)
            return obj.upper()
        if name == "kecil":
            _nargs("kecil", args, 0, 0)
            return obj.lower()
        if name == "potong":
            _nargs("potong", args, 0, 0)
            return obj.strip()
        if name == "ganti":
            _nargs("ganti", args, 2, 2)
            a, b = args
            if not isinstance(a, str) or not isinstance(b, str):
                raise _RedFlag("ganti() butuh dua teks, bestie.")
            return obj.replace(a, b)
        if name == "pisah":
            _nargs("pisah", args, 0, 1)
            if not args:
                return obj.split()
            if not isinstance(args[0], str):
                raise _RedFlag("pisah() butuh pemisah teks, bestie.")
            return obj.split(args[0])
        if name == "mulai_dengan":
            _nargs("mulai_dengan", args, 1, 1)
            if not isinstance(args[0], str):
                raise _RedFlag("mulai_dengan() butuh teks, bestie.")
            return obj.startswith(args[0])
        if name == "berakhir_dengan":
            _nargs("berakhir_dengan", args, 1, 1)
            if not isinstance(args[0], str):
                raise _RedFlag("berakhir_dengan() butuh teks, bestie.")
            return obj.endswith(args[0])
    elif isinstance(obj, dict):
        if name == "kunci":
            _nargs("kunci", args, 0, 0)
            return list(obj.keys())
        if name == "nilai":
            _nargs("nilai", args, 0, 0)
            return list(obj.values())
        if name == "ambil":
            _nargs("ambil", args, 1, 2)
            k = str(args[0])
            return obj[k] if k in obj else (args[1] if len(args) == 2 else None)
        if name == "hapus":
            _nargs("hapus", args, 1, 1)
            k = str(args[0])
            if k in obj:
                return obj.pop(k)
            raise _RedFlag("kamus nggak punya kunci '%s'." % k)
        if name in obj:  # fungsi yang disimpan di kamus
            v = obj[name]
            if callable(v):
                return v(*args)
            raise _RedFlag("'%s' di kamus bukan fungsi, nggak bisa dipanggil." % name)
    # objek Python lain (hasil collab python): getattr langsung
    _t = getattr(obj, name, None)
    if callable(_t):
        return _t(*args)
    raise _RedFlag("%s nggak punya method '%s', bestie." % (_tname(obj), name))


def _cek_fungsi(f):
    if not callable(f):
        raise _RedFlag("'%s' bukan fungsi, nggak bisa dipanggil." % _fmt(f))


def _petakan(d, f):
    if not isinstance(d, (list, str)):
        raise _RedFlag("petakan() butuh daftar/teks, bestie.")
    _cek_fungsi(f)
    return [f(x) for x in d]


def _saring(d, f):
    if not isinstance(d, (list, str)):
        raise _RedFlag("saring() butuh daftar/teks, bestie.")
    _cek_fungsi(f)
    return [x for x in d if _jtruthy(f(x))]


def _kumpulkan(d, f, awal):
    if not isinstance(d, (list, str)):
        raise _RedFlag("kumpulkan() butuh daftar/teks, bestie.")
    _cek_fungsi(f)
    acc = awal
    for x in d:
        acc = f(acc, x)
    return acc


def _baca_file(p):
    if not isinstance(p, str):
        raise _RedFlag("baca_file() butuh path teks, bestie.")
    try:
        with open(p, "r", encoding="utf-8") as _fh:
            return _fh.read()
    except FileNotFoundError:
        raise _RedFlag("file '%s' nggak ketemu, bestie." % p)
    except OSError as _e:
        raise _RedFlag("gagal baca file '%s': %s" % (p, _e))


def _tulis_file(p, t):
    if not isinstance(p, str) or not isinstance(t, str):
        raise _RedFlag("tulis_file() butuh path & teks, bestie.")
    try:
        with open(p, "w", encoding="utf-8") as _fh:
            _fh.write(t)
    except OSError as _e:
        raise _RedFlag("gagal tulis file '%s': %s" % (p, _e))
    return True


def _tambah_file(p, t):
    if not isinstance(p, str) or not isinstance(t, str):
        raise _RedFlag("tambah_file() butuh path & teks, bestie.")
    try:
        with open(p, "a", encoding="utf-8") as _fh:
            _fh.write(t)
    except OSError as _e:
        raise _RedFlag("gagal nulis ke file '%s': %s" % (p, _e))
    return True


def _tanggal(fmt=None):
    if fmt is None:
        fmt = "%d/%m/%Y %H:%M:%S"
    if not isinstance(fmt, str):
        raise _RedFlag("format tanggal() harus teks, bestie.")
    return _datetime.datetime.now().strftime(fmt)


def _args():
    return list(_sys.argv[1:])


def _env(nama, default=None):
    if not isinstance(nama, str):
        raise _RedFlag("env() butuh nama variabel teks, bestie.")
    return _os.environ.get(nama, default)


def _klaim(kondisi, pesan="Klaim gagal, bestie."):
    if not _jtruthy(kondisi):
        raise _RedFlag(_fmt(pesan))
    return True


def _jalankan(perintah):
    if not isinstance(perintah, str):
        raise _RedFlag("jalankan() butuh teks perintah, bestie.")
    try:
        _r = _subprocess.run(perintah, shell=True, capture_output=True,
                             text=True, timeout=60)
    except _subprocess.TimeoutExpired:
        raise _RedFlag("perintahnya kelamaan (timeout 60 detik), bestie.")
    except OSError as _e:
        raise _RedFlag("gagal jalanin perintah: %s" % _e)
    return {"kode": _r.returncode, "keluar": _r.stdout, "galat": _r.stderr}


def _json_urai(teks):
    if not isinstance(teks, str):
        raise _RedFlag("json_urai() butuh teks, bestie.")
    try:
        return _json.loads(teks)
    except ValueError as _e:
        raise _RedFlag("teksnya bukan JSON valid: %s" % _e)


def _json_tulis(nilai, cantik=False):
    if not isinstance(cantik, bool):
        raise _RedFlag("argumen 'cantik' json_tulis() harus valid/gimmick.")
    try:
        return _json.dumps(nilai, ensure_ascii=False,
                           indent=2 if cantik else None)
    except (TypeError, ValueError) as _e:
        raise _RedFlag("nilainya nggak bisa jadi JSON: %s" % _e)


def _http_minta(url, data=None):
    if not isinstance(url, str):
        raise _RedFlag("http butuh URL teks, bestie.")
    _req_data = None
    _headers = {"User-Agent": "JakselScript/0.6.0"}
    if data is not None:
        if isinstance(data, dict):
            _req_data = _urlparse.urlencode(data).encode("utf-8")
            _headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif isinstance(data, str):
            _req_data = data.encode("utf-8")
        else:
            raise _RedFlag("data http_post() harus kamus/teks, bestie.")
    _req = _urlreq.Request(url, data=_req_data, headers=_headers)
    try:
        with _urlreq.urlopen(_req, timeout=15) as _resp:
            return _resp.read().decode("utf-8", errors="replace")
    except _urlerr.HTTPError as _e:
        raise _RedFlag("HTTP %s pas buka %s, bestie." % (_e.code, url))
    except _urlerr.URLError as _e:
        raise _RedFlag("gagal konek ke %s: %s" % (url, _e.reason))
    except (OSError, ValueError) as _e:
        raise _RedFlag("HTTP error: %s" % _e)


def _http_get(url):
    return _http_minta(url)


def _http_get_json(url):
    return _json_urai(_http_minta(url))


def _http_post(url, data=None):
    return _http_minta(url, data)


def _rx(pola, nama):
    try:
        return _re.compile(pola)
    except _re.error as _e:
        raise _RedFlag("pola regex-nya rusak, bestie: %s" % _e)


def _cocok(teks, pola):
    if not isinstance(teks, str) or not isinstance(pola, str):
        raise _RedFlag("cocok() butuh teks & pola teks, bestie.")
    return _rx(pola, "cocok").search(teks) is not None


def _cari(teks, pola):
    if not isinstance(teks, str) or not isinstance(pola, str):
        raise _RedFlag("cari() butuh teks & pola teks, bestie.")
    _m = _rx(pola, "cari").search(teks)
    return _m.group(0) if _m else None


def _cari_semua(teks, pola):
    if not isinstance(teks, str) or not isinstance(pola, str):
        raise _RedFlag("cari_semua() butuh teks & pola teks, bestie.")
    return _rx(pola, "cari_semua").findall(teks)


def _ganti_regex(teks, pola, ganti):
    if not isinstance(teks, str) or not isinstance(pola, str):
        raise _RedFlag("ganti_regex() butuh teks & pola teks, bestie.")
    if not isinstance(ganti, str):
        raise _RedFlag("ganti_regex() butuh teks pengganti, bestie.")
    return _rx(pola, "ganti_regex").sub(ganti, teks)


def _csv_baca(path):
    if not isinstance(path, str):
        raise _RedFlag("csv_baca() butuh path teks, bestie.")
    try:
        with open(path, "r", encoding="utf-8", newline="") as _fh:
            return [list(_b) for _b in _csv.reader(_fh)]
    except FileNotFoundError:
        raise _RedFlag("file '%s' nggak ketemu, bestie." % path)
    except OSError as _e:
        raise _RedFlag("gagal baca CSV '%s': %s" % (path, _e))


def _csv_tulis(path, data):
    if not isinstance(path, str):
        raise _RedFlag("csv_tulis() butuh path teks, bestie.")
    if not isinstance(data, list) or any(not isinstance(_b, list) for _b in data):
        raise _RedFlag("csv_tulis() butuh daftar berisi daftar baris, bestie.")
    try:
        with open(path, "w", encoding="utf-8", newline="") as _fh:
            _csv.writer(_fh).writerows(
                [[_fmt(_c) for _c in _b] for _b in data])
    except OSError as _e:
        raise _RedFlag("gagal tulis CSV '%s': %s" % (path, _e))
    return True


def _ada_file(path):
    if not isinstance(path, str):
        raise _RedFlag("ada_file() butuh path teks, bestie.")
    return _os.path.exists(path)


def _daftar_file(folder="."):
    if not isinstance(folder, str):
        raise _RedFlag("daftar_file() butuh path folder teks, bestie.")
    try:
        return sorted(_os.listdir(folder))
    except OSError as _e:
        raise _RedFlag("gagal baca folder '%s': %s" % (folder, _e))


def _buat_folder(path):
    if not isinstance(path, str):
        raise _RedFlag("buat_folder() butuh path teks, bestie.")
    try:
        _os.makedirs(path, exist_ok=True)
    except OSError as _e:
        raise _RedFlag("gagal bikin folder '%s': %s" % (path, _e))
    return True


def _hapus_file(path):
    if not isinstance(path, str):
        raise _RedFlag("hapus_file() butuh path teks, bestie.")
    try:
        _os.remove(path)
    except FileNotFoundError:
        raise _RedFlag("file '%s' nggak ketemu, bestie." % path)
    except OSError as _e:
        raise _RedFlag("gagal hapus '%s': %s" % (path, _e))
    return True


def _cek_angka_list(nama, d):
    if not isinstance(d, list):
        raise _RedFlag("%s() butuh daftar, bestie." % nama)
    if any(isinstance(_x, bool) or not isinstance(_x, (int, float)) for _x in d):
        raise _RedFlag("%s() cuma mau daftar angka, bestie." % nama)
    return d


def _total(d):
    return sum(_cek_angka_list("total", d))


def _terbesar(d):
    _dd = _cek_angka_list("terbesar", d)
    if not _dd:
        raise _RedFlag("daftarnya kosong, nggak ada yang terbesar.")
    return max(_dd)


def _terkecil(d):
    _dd = _cek_angka_list("terkecil", d)
    if not _dd:
        raise _RedFlag("daftarnya kosong, nggak ada yang terkecil.")
    return min(_dd)


def _rerata(d):
    _dd = _cek_angka_list("rerata", d)
    if not _dd:
        raise _RedFlag("daftarnya kosong, nggak bisa dirata-rata.")
    return sum(_dd) / len(_dd)


def _urut_dengan(daftar, kunci):
    if not isinstance(daftar, list):
        raise _RedFlag("urut_dengan() butuh daftar, bestie.")
    if not callable(kunci):
        raise _RedFlag("urut_dengan() butuh fungsi sebagai kunci, bestie.")
    try:
        return sorted(daftar, key=kunci)
    except TypeError:
        raise _RedFlag("hasil fungsi kunci nggak bisa dibandingin, bestie.")


def _pasangkan(a, b):
    if not isinstance(a, list) or not isinstance(b, list):
        raise _RedFlag("pasangkan() butuh dua daftar, bestie.")
    return [[_x, _y] for _x, _y in zip(a, b)]

'''

# identifier Python yang harus dihindari (tambah prefix _j)
_PY_KW = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
}


# builtin Python yang dipakai runtime transpiler — nama variabel user yang
# sama harus di-mangle biar nggak menutupi builtin.
_PY_BUILTIN = {
    "list", "dict", "set", "tuple", "str", "int", "float", "bool",
    "len", "range", "print", "input", "open", "type", "isinstance",
    "enumerate", "zip", "map", "filter", "sum", "min", "max", "abs",
    "round", "sorted", "reversed", "any", "all", "chr", "ord",
}


def _ident(name):
    return "_j" + name if name in _PY_KW or name in _PY_BUILTIN else name


# nama bawaan -> padanan Python di kode hasil.
# Hanya dipakai kalau user TIDAK menimpa nama itu sendiri (cek _shadow).
_BUILTIN_PY = {
    "spill": "_spill", "healing": "_healing", "panjang": "_panjang",
    "angka": "_angka", "teks": "_fmt", "rentang": "_rentang",
    "acak": "_acak", "waktu": "_time.time", "tanggal": "_tanggal",
    "petakan": "_petakan", "saring": "_saring", "kumpulkan": "_kumpulkan",
    "baca_file": "_baca_file", "tulis_file": "_tulis_file",
    "tambah_file": "_tambah_file",
    "args": "_args", "env": "_env", "tipe": "_tipe", "klaim": "_klaim",
    "jalankan": "_jalankan",
    "json_urai": "_json_urai", "json_tulis": "_json_tulis",
    "http_get": "_http_get", "http_get_json": "_http_get_json",
    "http_post": "_http_post",
    "cocok": "_cocok", "cari": "_cari", "cari_semua": "_cari_semua",
    "ganti_regex": "_ganti_regex",
    "csv_baca": "_csv_baca", "csv_tulis": "_csv_tulis",
    "ada_file": "_ada_file", "daftar_file": "_daftar_file",
    "buat_folder": "_buat_folder", "hapus_file": "_hapus_file",
    "total": "_total", "terbesar": "_terbesar", "terkecil": "_terkecil",
    "rerata": "_rerata", "urut_dengan": "_urut_dengan",
    "pasangkan": "_pasangkan",
    "Error": "_JakselError",
    "luncurkan": "_luncurkan", "tunggu": "_tunggu",
    "tunggu_semua": "_tunggu_semua",
}


def _nama_destructure(destr):
    """Semua nama variabel di target destructuring."""
    if destr.kind == "list":
        return [t[3:] if t.startswith("...") else t for t in destr.items]
    return [v for _k, v in destr.items]


def _pola_binds(pola):
    """Semua nama yang di-bind satu pola 'cocokkan' (termasuk bersarang)."""
    if isinstance(pola, PatBind):
        return [pola.name]
    if isinstance(pola, PatType):
        return [pola.name]
    if isinstance(pola, PatList):
        out = []
        for p in pola.items:
            out.extend(_pola_binds(p))
        return out
    if isinstance(pola, PatDict):
        out = []
        for _k, p in pola.items:
            out.extend(_pola_binds(p))
        return out
    return []


def _kumpul_nama(node, out):
    """Kumpulkan nama yang dideklarasikan user (biar nggak ketuker bawaan)."""
    if isinstance(node, VarDecl):
        if isinstance(node.name, Destructure):
            out.update(_nama_destructure(node.name))
        else:
            out.add(node.name)
    if isinstance(node, FuncDef):
        out.add(node.name)
        for p, _d in node.params:
            out.add(p)
        if node.variadic:
            out.add(node.variadic)
    if isinstance(node, ClassDef):
        out.add(node.name)
        for m in node.methods:
            if isinstance(m, PropertyDef):
                out.add(m.name)
                continue
            out.add(m.name)
            for p, _d in m.params:
                out.add(p)
            if m.variadic:
                out.add(m.variadic)
    if isinstance(node, EnumDef):
        out.add(node.name)
    if isinstance(node, Destructure):
        out.update(_nama_destructure(node))
    if isinstance(node, PatBind):
        out.add(node.name)
    if isinstance(node, ImportStmt):
        if node.alias:
            out.add(node.alias)
        if node.ambil:
            out.update(node.ambil)
        if node.py_module is not None and not node.alias and not node.ambil:
            out.add(node.py_module.split(".")[0])
    if isinstance(node, ForStmt):
        out.add(node.var)
        if node.idx_var:
            out.add(node.idx_var)
    if isinstance(node, TryStmt) and node.catch_var:
        out.add(node.catch_var)
    for v in vars(node).values():
        if isinstance(v, Node):
            _kumpul_nama(v, out)
        elif isinstance(v, (list, tuple)):
            for x in v:
                if isinstance(x, Node):
                    _kumpul_nama(x, out)
                elif isinstance(x, tuple):
                    for y in x:
                        if isinstance(y, Node):
                            _kumpul_nama(y, out)


class _Scope:
    """Satu scope buat analisis: 'modul' | 'fungsi'."""
    __slots__ = ("kind", "parent", "defined", "assigned", "_dekl")

    def __init__(self, kind, parent):
        self.kind = kind
        self.parent = parent      # _Scope | None
        self.defined = set()      # nama yang di-bind di scope ini
        self.assigned = set()     # target assignment di badan scope ini
        self._dekl = None         # (global_set, nonlocal_set) hasil analisis


class _AnalisisScope:
    """Tentukan deklarasi 'global'/'nonlocal' tiap fungsi biar hasil transpile
    cocok dengan semantik interpreter.

    Interpreter: assignment (x = ...) jalan ke atas (env.set). Kalau ketemu
    binding di fungsi pembungkus -> ubah binding itu (nonlocal); kalau ketemu
    di global -> ubah global; kalau nggak ketemu -> bikin lokal baru.
    'bestie x = ...' selalu bikin binding baru di scope saat ini (shadowing).

    Loop var / catch var / pattern bind di interpreter hidup di scope anak
    yang fresh, jadi TIDAK dihitung sebagai assignment scope fungsi.
    """

    def __init__(self, tx):
        self.tx = tx  # Transpiler (buat _cari_collab)
        self._fungsi = []       # semua _Scope fungsi
        self._node_scope = []   # (node, scope, kind): kind = func/prop_get/prop_set
        self._loading = set()   # cegah rekursi collab sirkular
        self._modul_scope = {}  # full path -> _Scope (buat collab namespace)

    # -- API --
    def analisis(self, program):
        modul = _Scope("modul", None)
        self._jalan_block(program.statements, modul)
        for scope in self._fungsi:
            g, n = set(), set()
            for nama in scope.assigned:
                if nama in scope.defined:
                    continue
                s = scope.parent
                while s is not None:
                    if nama in s.defined:
                        if s.kind == "fungsi":
                            n.add(nama)
                        else:
                            g.add(nama)
                        break
                    s = s.parent
            scope._dekl = (g, n)
        for node, scope, kind in self._node_scope:
            if kind == "prop_get":
                node._dekl_get = scope._dekl
            elif kind == "prop_set":
                node._dekl_set = scope._dekl
            else:
                node._dekl = scope._dekl
        return modul

    def dekl_node(self, node, kind="func"):
        if kind == "prop_get":
            return getattr(node, "_dekl_get", (set(), set()))
        if kind == "prop_set":
            return getattr(node, "_dekl_set", (set(), set()))
        return getattr(node, "_dekl", (set(), set()))

    def dekl_modul(self, full):
        scope = self._modul_scope.get(full)
        if scope is None:
            return (set(), set())
        return getattr(scope, "_dekl", (set(), set()))

    # -- fase jalan --
    def _jalan_block(self, stmts, scope):
        for s in stmts:
            self._jalan_stmt(s, scope)

    def _jalan_fungsi(self, params, variadic, body, scope, node=None,
                      kind="func"):
        fn = _Scope("fungsi", scope)
        self._fungsi.append(fn)
        if node is not None:
            self._node_scope.append((node, fn, kind))
        for p, d in params:
            fn.defined.add(p)
            if d is not None:
                self._jalan_expr(d, scope)
        if variadic:
            fn.defined.add(variadic)
        self._jalan_block(body.statements, fn)
        return fn

    def _jalan_stmt(self, s, scope):
        if isinstance(s, VarDecl):
            self._jalan_expr(s.value, scope)
            self._target(s.name, scope, True)
        elif isinstance(s, Assign):
            self._jalan_expr(s.value, scope)
            self._target(s.target, scope, False)
        elif isinstance(s, FuncDef):
            scope.defined.add(s.name)
            self._jalan_fungsi(s.params, s.variadic, s.body, scope, node=s)
        elif isinstance(s, ClassDef):
            scope.defined.add(s.name)
            for m in s.methods:
                if isinstance(m, PropertyDef):
                    if m.getter_body is not None:
                        self._jalan_fungsi([], None, m.getter_body, scope,
                                            node=m, kind="prop_get")
                    if m.setter_body is not None:
                        self._jalan_fungsi([(m.setter_param, None)], None,
                                            m.setter_body, scope,
                                            node=m, kind="prop_set")
                else:
                    self._jalan_fungsi(m.params, m.variadic, m.body, scope,
                                        node=m)
        elif isinstance(s, EnumDef):
            scope.defined.add(s.name)
        elif isinstance(s, ForStmt):
            self._jalan_expr(s.iterable, scope)
            self._jalan_block(s.body.statements, scope)
        elif isinstance(s, TryStmt):
            self._jalan_block(s.body.statements, scope)
            self._jalan_block(s.catch_body.statements, scope)
            if s.finally_body is not None:
                self._jalan_block(s.finally_body.statements, scope)
        elif isinstance(s, MatchStmt):
            self._jalan_expr(s.subject, scope)
            for pola, guard, body in s.arms:
                # binding pola ala Python match: bocor ke scope pembungkus
                for nm in _pola_binds(pola):
                    scope.defined.add(nm)
                if guard is not None:
                    self._jalan_expr(guard, scope)
                self._jalan_block(body.statements, scope)
        elif isinstance(s, IfStmt):
            self._jalan_expr(s.cond, scope)
            self._jalan_block(s.then_block.statements, scope)
            for c, b in s.elifs:
                self._jalan_expr(c, scope)
                self._jalan_block(b.statements, scope)
            if s.else_block is not None:
                self._jalan_block(s.else_block.statements, scope)
        elif isinstance(s, WhileStmt):
            self._jalan_expr(s.cond, scope)
            self._jalan_block(s.body.statements, scope)
        elif isinstance(s, ReturnStmt):
            if s.value is not None:
                self._jalan_expr(s.value, scope)
        elif isinstance(s, ExitStmt):
            self._jalan_expr(s.code, scope)
        elif isinstance(s, ThrowStmt):
            self._jalan_expr(s.value, scope)
        elif isinstance(s, ExprStmt):
            self._jalan_expr(s.expr, scope)
        elif isinstance(s, ImportStmt):
            self._jalan_import(s, scope)
        elif isinstance(s, ExportStmt):
            # 'ekspor' cuma ngaruh pas modul di-collab (interpreter/VM);
            # di hasil transpile inline jadi komentar aja
            pass
        # BreakStmt/ContinueStmt: nggak ada binding

    def _target(self, target, scope, definisikan):
        if isinstance(target, str):
            # VarDecl.name: str langsung
            if definisikan:
                scope.defined.add(target)
            else:
                scope.assigned.add(target)
        elif isinstance(target, Name):
            if definisikan:
                scope.defined.add(target.id)
            else:
                scope.assigned.add(target.id)
        elif isinstance(target, Destructure):
            for nama in _nama_destructure(target):
                if definisikan:
                    scope.defined.add(nama)
                else:
                    scope.assigned.add(nama)
        # Index/Attr: bukan binding nama

    def _jalan_expr(self, e, scope):
        # ekspresi nggak punya assignment; cukup jalanin anaknya
        # (buat FuncDef inline — nggak ada di JakselScript — lewati)
        for v in vars(e).values():
            if isinstance(v, Node):
                self._jalan_expr(v, scope)
            elif isinstance(v, (list, tuple)):
                for x in v:
                    if isinstance(x, Node):
                        self._jalan_expr(x, scope)
                    elif isinstance(x, tuple):
                        for y in x:
                            if isinstance(y, Node):
                                self._jalan_expr(y, scope)

    def _jalan_import(self, s, scope):
        if s.py_module is not None:
            if s.ambil:
                for nama in s.ambil:
                    scope.defined.add(nama)
            elif s.alias:
                scope.defined.add(s.alias)
            else:
                scope.defined.add(s.py_module.split(".")[0])
            return
        full = self.tx._cari_collab(s.path)
        if full is None:
            return  # error dilaporin pas transpile
        if s.alias is None and s.ambil is None:
            # mode inline: nama modul masuk scope ini
            if full in self._loading:
                return
            self._loading.add(full)
            old_dir = self.tx._file_dir
            self.tx._file_dir = os.path.dirname(full)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    program = parse(lex(f.read(), full))
                self._jalan_block(program.statements, scope)
            finally:
                self.tx._file_dir = old_dir
                self._loading.discard(full)
        else:
            if s.alias:
                scope.defined.add(s.alias)
            if s.ambil:
                for nama in s.ambil:
                    scope.defined.add(nama)
            # isi modul dianalisis sebagai scope fungsi (induk = scope ini)
            # biar nonlocal/global di dalam modul bener
            if full in self._modul_scope or full in self._loading:
                return
            self._loading.add(full)
            old_dir = self.tx._file_dir
            self.tx._file_dir = os.path.dirname(full)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    program = parse(lex(f.read(), full))
                mscope = _Scope("fungsi", scope)
                self._fungsi.append(mscope)
                self._modul_scope[full] = mscope
                self._jalan_block(program.statements, mscope)
            finally:
                self.tx._file_dir = old_dir
                self._loading.discard(full)


class Transpiler:
    def __init__(self):
        self.lines = []
        self.level = 0
        self._imported = set()
        self._shadow = set()  # nama user yang menimpa bawaan
        self._kelas_induk = {}  # nama kelas -> nama induk (cek warisi melingkar)
        self._modul_func = {}  # full path -> nama fungsi _mod_N
        self._loading_modul = set()  # modul yang lagi di-emit (cegah sirkular)
        self._analisis = None  # _AnalisisScope (diisi pas run)
        self._file_dir = "."
        self._tmp_n = 0  # counter nama temporer

    def _py_name(self, name):
        if name in _BUILTIN_PY and name not in self._shadow:
            return _BUILTIN_PY[name]
        return _ident(name)

    # -- util --
    def emit(self, code):
        self.lines.append("    " * self.level + code)

    # -- expressions -> str --
    def tx(self, node):
        if isinstance(node, Literal):
            v = node.value
            if v is True:
                return "True"
            if v is False:
                return "False"
            if v is None:
                return "None"
            return repr(v)
        if isinstance(node, InterpString):
            parts = []
            for kind, part in node.parts:
                if kind == "teks":
                    if part:
                        parts.append(repr(part))
                else:
                    parts.append("_fmt(%s)" % self.tx(part))
            return " + ".join(parts) if parts else "''"
        if isinstance(node, Name):
            return self._py_name(node.id)
        if isinstance(node, ThisExpr):
            return "self"
        if isinstance(node, SuperExpr):
            raise ValueError("'ortu' harus diikuti '.nama_method(...)'.")
        if isinstance(node, ChainComp):
            vals = ", ".join([self.tx(node.first)] +
                             [self.tx(e) for e in node.operands])
            ops = ", ".join("'%s'" % o for o in node.ops)
            return "_jchain([%s], [%s])" % (vals, ops)
        if isinstance(node, BinOp):
            l, r = self.tx(node.left), self.tx(node.right)
            op = node.op
            if op == "+":
                return "_tambah_ov(%s, %s)" % (l, r)
            if op == "-":
                return "_kurang_ov(%s, %s)" % (l, r)
            if op == "*":
                return "_kali_ov(%s, %s)" % (l, r)
            if op == "/":
                return "_bagi_ov(%s, %s)" % (l, r)
            if op == "%":
                return "_mod_ov(%s, %s)" % (l, r)
            if op in ("==", "!="):
                return "_eq_ov(%s, %s, '%s')" % (l, r, op)
            if op in ("<", ">", "<=", ">="):
                return "_banding_ov(%s, %s, '%s')" % (l, r, op)
            if op == "dalam":
                return "_dalam(%s, %s)" % (l, r)
            if op == "dan":
                return "(%s and %s)" % (l, r)
            if op == "atau":
                return "(%s or %s)" % (l, r)
            if op == "??":
                return "_coalesce(%s, lambda: %s)" % (l, r)
            raise ValueError(f"operator aneh: {op}")
        if isinstance(node, UnaryOp):
            return "_neg(%s)" % self.tx(node.operand)
        if isinstance(node, NotOp):
            return "(not %s)" % self.tx(node.operand)
        if isinstance(node, Call):
            return self.tx_call(node)
        if isinstance(node, Index):
            return "_idx(%s, %s)" % (self.tx(node.obj), self.tx(node.index))
        if isinstance(node, IfExpr):
            return "((%s) if _jtruthy(%s) else (%s))" % (
                self.tx(node.then), self.tx(node.cond), self.tx(node.else_))
        if isinstance(node, Comp):
            # Python comprehension — var loop di-mangle biar nggak bocor
            v = self._py_name(node.var)
            s = "[%s for %s in _jiter(%s)" % (
                self.tx(node.expr), v, self.tx(node.iterable))
            if node.cond is not None:
                s += " if _jtruthy(%s)" % self.tx(node.cond)
            return s + "]"
        if isinstance(node, Slice):
            def _s(v):
                return self.tx(v) if v is not None else "None"
            return "_slice(%s, %s, %s, %s)" % (
                self.tx(node.obj), _s(node.mulai), _s(node.akhir),
                _s(node.langkah))
        if isinstance(node, Attr):
            if isinstance(node.obj, SuperExpr):
                return "super().%s" % node.name
            if node.optional:
                return "_mvalue_opt(%s, %s)" % (self.tx(node.obj), repr(node.name))
            return "_mvalue(%s, %s)" % (self.tx(node.obj), repr(node.name))
        if isinstance(node, ListLit):
            return "[%s]" % ", ".join(self.tx(e) for e in node.elements)
        if isinstance(node, DictLit):
            return "{%s}" % ", ".join(
                "%s: %s" % (repr(k), self.tx(v)) for k, v in node.pairs)
        raise ValueError(f"ekspresi aneh: {type(node).__name__}")

    def _tmp(self, prefix):
        """Nama temporer unik, mis. _d1, _m2."""
        self._tmp_n += 1
        return "_%s%d" % (prefix, self._tmp_n)

    def _emit_dekl(self, g, n):
        """Emit deklarasi global/nonlocal di awal badan fungsi."""
        if g:
            self.emit("global %s" % ", ".join(_ident(x) for x in sorted(g)))
        if n:
            self.emit("nonlocal %s" % ", ".join(_ident(x) for x in sorted(n)))

    def tx_call(self, node):
        parts = []
        for a in node.args:
            if isinstance(a, Spread):
                parts.append("*" + self.tx(a.value))
            else:
                parts.append(self.tx(a))
        for nama, val in node.kwargs:
            parts.append("%s=%s" % (_ident(nama), self.tx(val)))
        args = ", ".join(parts)
        if isinstance(node.func, Name):
            name = node.func.id
            if name == "kepo" and name not in self._shadow:
                return "input(%s)" % ("_fmt(%s)" % args if args else "")
            return "%s(%s)" % (self._py_name(name), args)
        if isinstance(node.func, Attr):
            if isinstance(node.func.obj, SuperExpr):
                # ortu.metode(args) -> super().metode(args)
                # ('lahir' jadi __init__ biar nyambung ke transpiler kelas)
                _mn = "__init__" if node.func.name == "lahir" else node.func.name
                return "super().%s(%s)" % (_mn, args)
            # obj.method(args) -> dispatcher method
            if node.func.optional:
                # short-circuit: obj dievaluasi sekali, args nggak jalan kalo zonk
                _o = self.tx(node.func.obj)
                return ("(None if (_jsopt_ := %s) is None else "
                        "_method_opt(_jsopt_, %s%s))" % (
                            _o, repr(node.func.name),
                            (", " + args) if args else ""))
            return "_method(%s, %s%s)" % (
                self.tx(node.func.obj), repr(node.func.name),
                (", " + args) if args else "")
        return "%s(%s)" % (self.tx(node.func), args)

    # -- statements --
    def tx_stmt(self, node):
        if isinstance(node, VarDecl):
            if isinstance(node.name, Destructure):
                self.tx_destructure(node.name, self.tx(node.value), True)
            else:
                self.emit("%s = %s" % (_ident(node.name), self.tx(node.value)))
        elif isinstance(node, Assign):
            self.tx_assign(node)
        elif isinstance(node, ExprStmt):
            self.emit(self.tx(node.expr))
        elif isinstance(node, IfStmt):
            self.emit("if %s:" % self.tx(node.cond))
            self.tx_block(node.then_block)
            for cond, block in node.elifs:
                self.emit("elif %s:" % self.tx(cond))
                self.tx_block(block)
            if node.else_block is not None:
                self.emit("else:")
                self.tx_block(node.else_block)
        elif isinstance(node, WhileStmt):
            if isinstance(node.cond, Literal) and node.cond.value is True:
                self.emit("while True:")  # gamon
            else:
                self.emit("while %s:" % self.tx(node.cond))
            self.tx_block(node.body)
        elif isinstance(node, ForStmt):
            if node.idx_var:
                self.emit("for %s, %s in enumerate(%s):" % (
                    _ident(node.idx_var), _ident(node.var),
                    self.tx(node.iterable)))
            else:
                self.emit("for %s in %s:" % (_ident(node.var),
                                             self.tx(node.iterable)))
            self.tx_block(node.body)
        elif isinstance(node, FuncDef):
            self.emit("def %s(%s):" % (_ident(node.name),
                                       self._tx_params(node)))
            self.tx_block(node.body, self._analisis.dekl_node(node))
        elif isinstance(node, ClassDef):
            self.tx_class(node)
        elif isinstance(node, EnumDef):
            self.tx_enum(node)
        elif isinstance(node, MatchStmt):
            self.tx_match(node)
        elif isinstance(node, ReturnStmt):
            self.emit("return %s" % self.tx(node.value) if node.value is not None else "return None")
        elif isinstance(node, BreakStmt):
            self.emit("break")
        elif isinstance(node, ContinueStmt):
            self.emit("continue")
        elif isinstance(node, TryStmt):
            self.emit("try:")
            self.tx_block(node.body)
            self.emit("except _RedFlag as _e:")
            self.level += 1
            if node.catch_class is not None:
                # yaudah <Tipe> e -> cuma ketangkep kalau nilai error
                # instanceof Tipe; kalau nggak cocok, lempar lagi
                self.emit("if not _cocok_tipe(_e.nilai, %s, %s):"
                          % (self._py_name(node.catch_class),
                             repr(node.catch_class)))
                self.level += 1
                self.emit("raise")
                self.level -= 1
            if node.catch_var:
                # paritas interpreter: variabel = nilai asli red_flag
                # (kalau ada), kalau nggak ya pesan string-nya
                self.emit("%s = (_e.nilai if _e.nilai is not None else str(_e))"
                          % _ident(node.catch_var))
            self.level -= 1
            self.tx_block(node.catch_body)
            if node.finally_body is not None:
                self.emit("finally:")
                self.tx_block(node.finally_body)
        elif isinstance(node, ThrowStmt):
            self.emit("raise _red_flag_nilai(%s)" % self.tx(node.value))
        elif isinstance(node, ExitStmt):
            self.emit("_sys.exit(int(%s))" % self.tx(node.code))
        elif isinstance(node, ImportStmt):
            self.tx_import(node)
        elif isinstance(node, ExportStmt):
            self.emit("# ekspor: %s" % ", ".join(node.names))
        else:
            raise ValueError(f"statement aneh: {type(node).__name__}")

    def tx_block(self, block, dekl=None):
        self.level += 1
        if dekl:
            self._emit_dekl(*dekl)
        if not block.statements:
            self.emit("pass")
        for stmt in block.statements:
            self.tx_stmt(stmt)
        self.level -= 1

    def _tx_params(self, node):
        """FuncDef -> 'a, b=1, *sisa' ala Python."""
        parts = []
        for pname, dflt in node.params:
            if dflt is None:
                parts.append(_ident(pname))
            else:
                parts.append("%s=%s" % (_ident(pname), self.tx(dflt)))
        if node.variadic:
            parts.append("*" + _ident(node.variadic))
        return ", ".join(parts)

    def tx_class(self, node):
        # tolak pewarisan melingkar (paritas dengan interpreter)
        if node.parent:
            if node.parent == node.name:
                raise ValueError(
                    f"kelas '{node.name}' nggak bisa mewarisi dirinya "
                    "sendiri (pewarisan melingkar), bestie.")
            seen = {node.name}
            p = node.parent
            while p:
                if p in seen:
                    raise ValueError(
                        f"pewarisan kelas '{node.name}' melingkar, bestie.")
                seen.add(p)
                p = self._kelas_induk.get(p)
            self.emit("class %s(%s):" % (_ident(node.name),
                                         self._py_name(node.parent)))
        else:
            self.emit("class %s(_JakselBase):" % _ident(node.name))
        self._kelas_induk[node.name] = node.parent
        self.level += 1
        if not node.methods:
            self.emit("pass")
        for m in node.methods:
            if isinstance(m, PropertyDef):
                self.tx_property(m)
                continue
            # 'lahir' -> __init__ biar konstruktor jalan ala Python
            pyname = "__init__" if m.name == "lahir" else _ident(m.name)
            params = self._tx_params(m)
            if m.static:
                # statik: tanpa self, dipanggil via Kelas.nama()
                self.emit("@staticmethod")
                self.emit("def %s(%s):" % (pyname, params))
            else:
                sig = "self" + (", " + params if params else "")
                self.emit("def %s(%s):" % (pyname, sig))
            self.tx_block(m.body, self._analisis.dekl_node(m))
        self.level -= 1

    def tx_property(self, node):
        """properti nama { ambil {...} taruh(v) {...} } -> @property Python."""
        # nama 'rahasia' sudah di-mangle parser jadi _Kelas__nama
        self.emit("@property")
        self.emit("def %s(self):" % _ident(node.name))
        if node.getter_body is not None:
            self.tx_block(node.getter_body,
                          self._analisis.dekl_node(node, "prop_get"))
        else:
            self.level += 1
            self.emit("raise _RedFlag(\"properti '%s' nggak bisa dibaca, "
                      "bestie.\")" % node.name)
            self.level -= 1
        if node.setter_body is not None:
            self.emit("@%s.setter" % _ident(node.name))
            self.emit("def %s(self, %s):" % (_ident(node.name),
                                            _ident(node.setter_param)))
            self.tx_block(node.setter_body,
                          self._analisis.dekl_node(node, "prop_set"))

    def tx_assign(self, node):
        tgt, val = node.target, self.tx(node.value)
        if isinstance(tgt, Destructure):
            self.tx_destructure(tgt, val, False)
        elif isinstance(tgt, Name):
            self.emit("%s = %s" % (_ident(tgt.id), val))
        elif isinstance(tgt, Index):
            self.emit("_setidx(%s, %s, %s)"
                      % (self.tx(tgt.obj), self.tx(tgt.index), val))
        elif isinstance(tgt, Attr):
            self.emit("_setattr(%s, %s, %s)"
                      % (self.tx(tgt.obj), repr(tgt.name), val))
        else:
            raise ValueError("target assignment aneh.")

    # -- destructuring --
    def _taro(self, nama, code, definisikan):
        """Taruh satu hasil destructuring ke variabel."""
        if not definisikan:
            # [a, b] = ... : variabel harus sudah ada (paritas interpreter)
            self.emit("try:")
            self.level += 1
            self.emit("_ = %s" % _ident(nama))
            self.level -= 1
            self.emit("except NameError:")
            self.level += 1
            self.emit("raise _RedFlag(\"variabel '%s' belum dikenalin, "
                      "bestie. Deklarasi dulu pakai 'bestie %s = ...'\")"
                      % (nama, nama))
            self.level -= 1
        self.emit("%s = %s" % (_ident(nama), code))

    def tx_destructure(self, destr, value_code, definisikan):
        """bestie [a, ...s] = v / [a, b] = v / bestie {k: w} = m."""
        tmp = self._tmp("d")
        self.emit("%s = %s" % (tmp, value_code))
        if destr.kind == "list":
            self.emit("if not isinstance(%s, list):" % tmp)
            self.level += 1
            self.emit('raise _RedFlag("destructuring daftar butuh nilai '
                      'daftar, bestie.")')
            self.level -= 1
            targets = destr.items
            rest_i = next((i for i, t in enumerate(targets)
                           if t.startswith("...")), None)
            if rest_i is not None:
                self.emit("if len(%s) < %d:" % (tmp, rest_i))
                self.level += 1
                self.emit('raise _RedFlag("daftarnya kependekan buat '
                          'destructuring, bestie.")')
                self.level -= 1
                for i in range(rest_i):
                    self._taro(targets[i], "%s[%d]" % (tmp, i), definisikan)
                self._taro(targets[rest_i][3:], "%s[%d:]"
                           % (tmp, rest_i), definisikan)
                for t in targets[rest_i + 1:]:
                    self._taro(t, "None", definisikan)
            else:
                self.emit("if len(%s) != %d:" % (tmp, len(targets)))
                self.level += 1
                self.emit('raise _RedFlag("destructuring butuh %d elemen, '
                          'dapat " + str(len(%s)) + ", bestie.")'
                          % (len(targets), tmp))
                self.level -= 1
                for i, t in enumerate(targets):
                    self._taro(t, "%s[%d]" % (tmp, i), definisikan)
        else:  # dict
            src = self._tmp("ds")
            self.emit("%s = (%s.__dict__ if isinstance(%s, _JakselBase) "
                      "else %s)" % (src, tmp, tmp, tmp))
            self.emit("if not isinstance(%s, dict):" % src)
            self.level += 1
            self.emit('raise _RedFlag("destructuring kamus butuh '
                      'kamus/objek, bestie.")')
            self.level -= 1
            for kunci, var in destr.items:
                self.emit("if %s not in %s:" % (repr(kunci), src))
                self.level += 1
                self.emit('raise _RedFlag("kunci \'%s\' nggak ada di sumber, '
                          'bestie.")' % kunci)
                self.level -= 1
                self._taro(var, "%s[%s]" % (src, repr(kunci)), definisikan)

    # -- cocokkan (pattern matching) --
    def tx_match(self, node):
        subj = self._tmp("m")
        self.emit("%s = %s" % (subj, self.tx(node.subject)))
        fnames = []
        for i, (pola, guard, _body) in enumerate(node.arms):
            fname = self._tmp("arm")
            fnames.append(fname)
            self.emit("def %s(_s):" % fname)
            self.level += 1
            self.emit("_b = {}")
            self._tx_pola(pola, "_s", "_b")
            for nm in _pola_binds(pola):
                self.emit("%s = _b[%s]" % (_ident(nm), repr(nm)))
            if guard is not None:
                self.emit("if not (%s):" % self.tx(guard))
                self.level += 1
                self.emit("return None")
                self.level -= 1
            self.emit("_b['_arm'] = %d" % i)
            self.emit("return _b")
            self.level -= 1
        bvar = self._tmp("b")
        for j, fname in enumerate(fnames):
            if j == 0:
                self.emit("%s = %s(%s)" % (bvar, fname, subj))
            else:
                self.emit("if %s is None:" % bvar)
                self.level += 1
                self.emit("%s = %s(%s)" % (bvar, fname, subj))
                self.level -= 1
        self.emit("if %s is None:" % bvar)
        self.level += 1
        self.emit('raise _RedFlag("cocokkan: nggak ada pola yang cocok, '
                  'bestie. Tambahin cabang \'_\' biar aman.")')
        self.level -= 1
        for i, (pola, _guard, body) in enumerate(node.arms):
            self.emit(("elif " if i else "if ") + "%s['_arm'] == %d:"
                      % (bvar, i))
            self.level += 1
            for nm in _pola_binds(pola):
                self.emit("%s = %s[%s]" % (_ident(nm), bvar, repr(nm)))
            if not body.statements:
                self.emit("pass")
            for stmt in body.statements:
                self.tx_stmt(stmt)
            self.level -= 1

    def _tx_pola(self, pola, subj, bvar):
        """Emit pencocokan satu pola di dalam fungsi arm.
        Ketidakcocokan -> 'return None'. Ikatan -> dict bvar."""
        if isinstance(pola, PatWild):
            return
        if isinstance(pola, PatLit):
            lit = repr(pola.value)
            self.emit("if not (%s == %s and type(%s) is type(%s)):"
                      % (subj, lit, subj, lit))
            self.level += 1
            self.emit("return None")
            self.level -= 1
            return
        if isinstance(pola, PatBind):
            self.emit("%s[%s] = %s" % (bvar, repr(pola.name), subj))
            return
        if isinstance(pola, PatType):
            self.emit("if not _cocok_tipe(%s, %s, %s):"
                      % (subj, self._py_name(pola.name), repr(pola.name)))
            self.level += 1
            self.emit("return None")
            self.level -= 1
            self.emit("%s[%s] = %s" % (bvar, repr(pola.name), subj))
            return
        if isinstance(pola, PatEnum):
            self.emit("if not _cocok_enum(%s, %s, %s):"
                      % (subj, repr(pola.enum_name), repr(pola.member_name)))
            self.level += 1
            self.emit("return None")
            self.level -= 1
            return
        if isinstance(pola, PatList):
            self.emit("if not isinstance(%s, list):" % subj)
            self.level += 1
            self.emit("return None")
            self.level -= 1
            subs = pola.items
            rest_i = next((i for i, p in enumerate(subs)
                           if isinstance(p, PatBind) and p.rest), None)
            if rest_i is None:
                self.emit("if len(%s) != %d:" % (subj, len(subs)))
                self.level += 1
                self.emit("return None")
                self.level -= 1
                for i, p in enumerate(subs):
                    self._tx_pola(p, "%s[%d]" % (subj, i), bvar)
            else:
                self.emit("if len(%s) < %d:" % (subj, rest_i))
                self.level += 1
                self.emit("return None")
                self.level -= 1
                for i in range(rest_i):
                    self._tx_pola(subs[i], "%s[%d]" % (subj, i), bvar)
                self.emit("%s[%s] = %s[%d:]"
                          % (bvar, repr(subs[rest_i].name), subj, rest_i))
            return
        if isinstance(pola, PatDict):
            src = self._tmp("ds")
            self.emit("%s = (%s.__dict__ if isinstance(%s, _JakselBase) "
                      "else %s)" % (src, subj, subj, subj))
            self.emit("if not isinstance(%s, dict):" % src)
            self.level += 1
            self.emit("return None")
            self.level -= 1
            for kunci, sub in pola.items:
                self.emit("if %s not in %s:" % (repr(kunci), src))
                self.level += 1
                self.emit("return None")
                self.level -= 1
                self._tx_pola(sub, "%s[%s]" % (src, repr(kunci)), bvar)
            return
        raise ValueError("pola aneh: %s" % type(pola).__name__)

    # -- pilihan (enum) --
    def tx_enum(self, node):
        """pilihan Warna { MERAH, HIJAU = 10 } -> kelas enum + anggota."""
        self.emit("class %s(_EnumBase):" % _ident(node.name))
        self.level += 1
        self.emit("_enum_name = %s" % repr(node.name))
        if not node.members:
            self.emit("pass")
        else:
            # _ev meniru nilai_otomatis interpreter: tiap anggota
            # (eksplisit/otomatis) menggeser counter ke value+1
            self.emit("_ev = 0")
            for nama, vnode in node.members:
                py = _ident(nama)
                if vnode is not None:
                    self.emit("%s = _EnumMember(%s, %s, %s)"
                              % (py, repr(node.name), repr(nama),
                                 self.tx(vnode)))
                else:
                    self.emit("%s = _EnumMember(%s, %s, _ev)"
                              % (py, repr(node.name), repr(nama)))
                self.emit("_ev = %s.value + 1" % py)
        self.level -= 1

    def tx_import(self, node):
        if node.py_module is not None:
            # collab python "os" [sebagai x] [ambil a, b] -> import Python
            mod = node.py_module
            basis = mod.split(".")[0]
            if node.ambil:
                self.emit("import %s" % mod)
                for nama in node.ambil:
                    self.emit("%s = _ambil_modul_py(%s, %s, %s)"
                              % (_ident(nama), basis, repr(nama), repr(mod)))
            elif node.alias:
                self.emit("import %s as %s" % (mod, _ident(node.alias)))
            else:
                self.emit("import %s as %s" % (mod, _ident(basis)))
            return
        full = self._cari_collab(node.path)
        if full is None:
            raise ValueError(f"file collab '{node.path}' nggak ketemu.")
        if node.alias is None and node.ambil is None:
            # mode lawas v0.4: isi modul di-inline langsung
            if full in self._imported:
                return
            self._imported.add(full)
            old_dir = self._file_dir
            self._file_dir = os.path.dirname(full)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    program = parse(lex(f.read(), full))
                _kumpul_nama(program, self._shadow)
                self.emit("# --- collab: %s ---" % node.path)
                for stmt in program.statements:
                    self.tx_stmt(stmt)
            finally:
                self._file_dir = old_dir
            return
        # mode namespace/selektif: isi modul dibungkus jadi fungsi
        # _mod_N() yang balikin dict namespace (paritas _Modul interpreter)
        if full in self._loading_modul:
            raise ValueError(
                f"collab sirkular terdeteksi: '{node.path}', bestie.")
        fname = self._modul_func.get(full)
        if fname is None:
            self._loading_modul.add(full)
            try:
                fname = "_mod%d" % len(self._modul_func)
                self._modul_func[full] = fname
                old_dir, old_shadow = self._file_dir, self._shadow
                self._file_dir = os.path.dirname(full)
                # shadow lokal modul: nama bawaan yang ditimpa modul
                # jangan bocor ke program utama
                self._shadow = set()
                try:
                    with open(full, "r", encoding="utf-8") as f:
                        program = parse(lex(f.read(), full))
                    _kumpul_nama(program, self._shadow)
                    self.emit("def %s():" % fname)
                    self.level += 1
                    self._emit_dekl(*self._analisis.dekl_modul(full))
                    if not program.statements:
                        self.emit("pass")
                    for stmt in program.statements:
                        self.tx_stmt(stmt)
                    # namespace: nama top-level yang beneran keisi
                    ns_tmp = self._tmp("ns")
                    self.emit("%s = {}" % ns_tmp)
                    mscope = self._analisis._modul_scope.get(full)
                    names = sorted(mscope.defined) if mscope else []
                    for nm in names:
                        self.emit("try:")
                        self.level += 1
                        self.emit("%s[%s] = %s"
                                  % (ns_tmp, repr(nm), _ident(nm)))
                        self.level -= 1
                        self.emit("except NameError:")
                        self.level += 1
                        self.emit("pass")
                        self.level -= 1
                    self.emit("return %s" % ns_tmp)
                    self.level -= 1
                finally:
                    self._file_dir, self._shadow = old_dir, old_shadow
            finally:
                self._loading_modul.discard(full)
        if node.alias:
            self.emit("%s = _Modul(%s, %s())"
                      % (_ident(node.alias), repr(node.path), fname))
        if node.ambil:
            for nama in node.ambil:
                self.emit("%s = _ambil_modul(%s(), %s, %s)"
                          % (_ident(nama), fname, repr(node.path),
                             repr(nama)))

    def _cari_collab(self, path):
        """Urutan cari: dir file -> std/ bawaan -> paket user."""
        if not path.endswith(".jaksel"):
            path += ".jaksel"
        kandidat = []
        if not os.path.isabs(path):
            kandidat.append(os.path.join(self._file_dir, path))
        else:
            kandidat.append(path)
        paket_dir = os.path.dirname(os.path.abspath(__file__))
        kandidat.append(os.path.join(paket_dir, path))
        user_dir = os.path.expanduser(os.path.join("~", ".jaksel", "paket"))
        if os.path.isdir(user_dir):
            for nama in sorted(os.listdir(user_dir)):
                kandidat.append(os.path.join(user_dir, nama, path))
        for k in kandidat:
            if os.path.isfile(k):
                return os.path.abspath(k)
        return None

    def run(self, program, file_dir="."):
        self._file_dir = file_dir
        _kumpul_nama(program, self._shadow)
        # analisis scope -> deklarasi global/nonlocal tiap fungsi
        # (paritas semantik assignment interpreter)
        self._analisis = _AnalisisScope(self)
        self._analisis.analisis(program)
        for stmt in program.statements:
            self.tx_stmt(stmt)
        return HEADER + "\n".join(self.lines) + "\n"


def transpile_source(source, filename="<string>", file_dir="."):
    return Transpiler().run(parse(lex(source, filename)), file_dir)


def transpile_file(path):
    full = os.path.abspath(path)
    with open(full, "r", encoding="utf-8") as f:
        source = f.read()
    return transpile_source(source, full, os.path.dirname(full))
