"""CLI JakselScript: gas | cek | alihbahasakan | rapi | urai | lsp | debug | pasang | paket | lepas | (REPL) | versi."""

import argparse
import os
import shutil
import subprocess
import sys

from .errors import JakselError, JakselSyntaxError
from .lexer import lex
from .parser import parse, FuncDef
from .interpreter import Interpreter, _Exit
from .transpiler import transpile_file
from .formatter import format_source
from .inspector import urai

VERSION = "0.6.0"

BANNER = r"""
     _       _             _ ___         _
  _ | |__ _ | |__ ___  ___| |   \ __ ___(_)_ __  __ _
 | || / _` | / // -_)(_-<| | |) / _/ _ \ | '_ \/ _` |
  \__/\__,_|_\_\\___//__/|_|___/\__\___/_| .__/\__,_|
                                         |_|
"""


def cmd_gas(path, prog_args=None, aman=False, vm=False):
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    # file .jsc: bytecode siap jalan via VM
    if path.endswith(".jsc"):
        return cmd_gas_jsc(path, prog_args, aman=aman)
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    if vm:
        return cmd_gas_vm(path, source, prog_args, aman=aman)
    interp = Interpreter(aman=aman)
    try:
        interp.run_source(source, path,
                          os.path.dirname(os.path.abspath(path)),
                          prog_args=prog_args)
    except _Exit as e:
        return e.code
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1
    return 0


def cmd_gas_jsc(path, prog_args=None, aman=False):
    """Jalankan file .jsc (bytecode) via VM."""
    from .vm import muat_jsc, jalan_vm, JakselError
    from .errors import JakselSyntaxError
    from .interpreter import _Exit
    try:
        unit = muat_jsc(path)
    except (JakselError, JakselSyntaxError, ValueError) as e:
        print(f"Red flag: {e}")
        return 1
    # pakai direktori sumber asli (kalau ada) biar import relatif jalan
    file_dir = getattr(unit, "sumber_dir", None) or os.path.dirname(
        os.path.abspath(path))
    try:
        jalan_vm(unit, aman=aman, file_dir=file_dir,
                 prog_args=prog_args)
        return 0
    except _Exit as e:
        return e.code
    except (JakselError, JakselSyntaxError) as e:
        print(f"Red flag: {e}")
        return 1


def cmd_gas_vm(path, source, prog_args=None, aman=False):
    """Jalankan via VM bytecode (kompilasi -> eksekusi VM)."""
    from .vm import kompilasi, jalan_vm, JakselError
    from .errors import JakselSyntaxError
    from .interpreter import _Exit
    try:
        unit = kompilasi(source, path)
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1
    try:
        jalan_vm(unit, aman=aman, file_dir=os.path.dirname(os.path.abspath(path)),
                 prog_args=prog_args)
        return 0
    except _Exit as e:
        return e.code
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1


def cmd_debug(path, prog_args=None):
    """Debugger interaktif: jalan per-statement + breakpoint."""
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    print("Mode debug: <enter>=langkah, b <baris>=breakpoint, "
          "lanjut(c), p <ekspresi>, tumpuk, keluar(q).")
    interp = Interpreter()
    try:
        interp.debug_source(source, filename=path,
                            file_dir=os.path.dirname(os.path.abspath(path)),
                            prog_args=prog_args)
    except _Exit as e:
        return e.code
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1
    print("Debug selesai, bestie.")
    return 0


def cmd_cek(path):
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        parse(lex(source, path))
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1
    print("Valid! Sintaks aman, bestie.")
    return 0


def cmd_alihbahasakan(path, out=None):
    """Transpile .jaksel -> .py"""
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        code = transpile_file(path)
    except JakselSyntaxError as e:
        print(e.pretty(source))
        return 1
    except ValueError as e:
        print(f"Red flag: {e}")
        return 1
    if out is None:
        base, _ = os.path.splitext(path)
        out = base + ".py"
    with open(out, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Valid! '{path}' udah diterjemahin ke '{out}'. Gas jalanin pakai: python3 {out}")
    return 0


def cmd_kompilasi(path, out=None):
    """Kompilasi .jaksel -> .jsc (bytecode)."""
    from .vm import kompilasi, simpan_jsc, JakselError
    from .errors import JakselSyntaxError
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        unit = kompilasi(source, path)
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1
    if out is None:
        base, _ = os.path.splitext(path)
        out = base + ".jsc"
    simpan_jsc(unit, out)
    print(f"Valid! '{path}' udah dikompilasi ke '{out}'. Gas jalanin pakai: jaksel gas --vm {out}")
    return 0


def cmd_rapi(path, cek=False, stdout=False):
    """Auto-format file .jaksel."""
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        rapi = format_source(source, path)
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1
    if cek:
        if rapi == source:
            print(f"Rapi! '{path}' udah kinclong, bestie.")
            return 0
        print(f"Belum rapi nih: '{path}'. Jalanin 'jaksel rapi {path}' dulu.")
        return 1
    if stdout:
        print(rapi, end="")
        return 0
    if rapi == source:
        print(f"Udah rapi dari sananya, bestie. '{path}' nggak berubah.")
        return 0
    with open(path, "w", encoding="utf-8") as f:
        f.write(rapi)
    print(f"Rapi! '{path}' udah diformat ulang. Kinclong, bestie.")
    return 0


def cmd_urai(path, mode="semua"):
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        print(urai(source, path, mode))
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1
    return 0


def cmd_lsp():
    from .lsp import serve
    serve()
    return 0


def cmd_tes(target=None):
    """Test framework mini: jalankan fungsi talent tes_* di file tes.

    target: file .jaksel / folder / None (auto: folder tes/, *.tes.jaksel).
    Tiap fungsi tes_* dipanggil; klaim() yang gagal / red_flag = tes gagal.
    """
    files = _kumpul_file_tes(target)
    if not files:
        print("Red flag: nggak ada file tes ketemu, bestie. "
              "Bikin file 'tes_contoh.tes.jaksel' berisi talent tes_*().")
        return 1
    total_lolos, total_gagal = 0, 0
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            program = parse(lex(source, path))
        except (JakselError, JakselSyntaxError) as e:
            print(f"\n{path}: GAGAL PARSE\n{e.pretty(source)}")
            total_gagal += 1
            continue
        tes_fns = [s.name for s in program.statements
                   if isinstance(s, FuncDef) and s.name.startswith("tes_")]
        if not tes_fns:
            print(f"\n{path}: nggak ada talent tes_*(), diskip.")
            continue
        print(f"\n{path}:")
        interp = Interpreter()
        try:
            interp.run_source(source, path,
                              os.path.dirname(os.path.abspath(path)))
        except _Exit:
            pass
        except (JakselError, JakselSyntaxError) as e:
            print(f"  kode top-level gagal: {e}")
            total_gagal += len(tes_fns)
            continue
        for nama in tes_fns:
            try:
                fn = interp.globals.get(nama)
                interp._panggil_nilai(fn, [], 0)
                print(f"  ✓ {nama}")
                total_lolos += 1
            except _Exit as e:
                print(f"  ✗ {nama}: cabut({e.code}) dipanggil di dalam tes")
                total_gagal += 1
            except (JakselError, JakselSyntaxError) as e:
                msg = str(e).split("\n")[0]
                print(f"  ✗ {nama}: {msg}")
                total_gagal += 1
    print(f"\n{total_lolos} lolos, {total_gagal} gagal. "
          + ("Semua valid, bestie!" if total_gagal == 0 else "Ada yang red flag."))
    return 1 if total_gagal else 0


def _kumpul_file_tes(target):
    if target and os.path.isfile(target):
        return [target]
    if target and os.path.isdir(target):
        dirs = [target]
    else:
        dirs = ["."]
    out = []
    for d in dirs:
        for root, _ds, files in os.walk(d):
            for fn in sorted(files):
                if fn.endswith(".tes.jaksel") or fn.endswith("_tes.jaksel"):
                    out.append(os.path.join(root, fn))
            # jangan masuk terlalu dalam: cukup 3 level
            if root.count(os.sep) - d.count(os.sep) >= 3:
                del _ds[:]
    if not out and not target:
        # fallback: folder tes/
        if os.path.isdir("tes"):
            return _kumpul_file_tes("tes")
    return sorted(set(out))


def cmd_baru(nama):
    """Scaffolding proyek: jaksel baru <nama>."""
    if os.path.exists(nama):
        print(f"Red flag: '{nama}' udah ada, bestie.")
        return 1
    os.makedirs(os.path.join(nama, "tes"))
    paket = {"nama": nama, "versi": "0.1.0", "jaksel": ">=0.6.0",
             "utama": "utama.jaksel"}
    with open(os.path.join(nama, "paket.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(paket, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(nama, "utama.jaksel"), "w", encoding="utf-8") as f:
        f.write(f"// {nama} — proyek JakselScript\n"
                f"// jalanin: jaksel gas utama.jaksel\n\n"
                f"talent sapa(nama) {{\n"
                f"    balikin \"Halo, {{nama}}! Gas terus, bestie.\"\n"
                f"}}\n\n"
                f"spill(sapa(\"dunia\"))\n")
    with open(os.path.join(nama, "tes", "contoh.tes.jaksel"), "w",
              encoding="utf-8") as f:
        f.write("// tes contoh — jalanin: jaksel tes\n"
                "collab \"../utama.jaksel\"\n\n"
                "talent tes_sapa() {\n"
                "    klaim(sapa(\"dunia\") == \"Halo, dunia! Gas terus, bestie.\")\n"
                "}\n")
    with open(os.path.join(nama, "README.md"), "w", encoding="utf-8") as f:
        f.write(f"# {nama}\n\nProyek JakselScript.\n\n"
                f"- `jaksel gas utama.jaksel` — jalanin\n"
                f"- `jaksel tes` — jalanin tes\n")
    print(f"Valid! Proyek '{nama}' jadi. Masuk: cd {nama}, "
          f"lalu 'jaksel gas utama.jaksel'.")
    return 0


def cmd_lint(path):
    """Linter statis: nama tak dikenal, dipakai sebelum deklarasi,
    variabel nggak kepakai, bayangan nama bawaan."""
    from .parser import (FuncDef, ClassDef, EnumDef, VarDecl, Assign,
                        Destructure, MatchStmt, Name, ForStmt, WhileStmt,
                        TryStmt, Block, IfStmt, Call)
    from .transpiler import _nama_destructure, _pola_binds
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        program = parse(lex(source, path))
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1
    bawaan = {"spill", "kepo", "rentang", "acak", "waktu", "tipe", "klaim",
              "panjang", "teks", "angka", "json_muat", "json_tulis",
              "http_minta", "regex_cari", "regex_ganti", "csv_baca",
              "csv_tulis", "jalankan", "tidur", "luncurkan", "tunggu",
              "tunggu_semua", "Error", "valid", "gimmick", "zonk"}
    masalah = []  # (level, baris, pesan)

    class Scope:
        def __init__(self, parent):
            self.parent, self.defs, self.used = parent, {}, set()

    def definisikan(sc, nama, line):
        sc.defs.setdefault(nama, line)
        if nama in bawaan:
            masalah.append(("info", line,
                            f"'{nama}' membayangi nama bawaan."))

    def dipakai(nama, line, sc):
        s = sc
        while s is not None:
            if nama in s.defs:
                s.used.add(nama)
                return
            s = s.parent
        if nama not in bawaan:
            masalah.append(("error", line,
                            f"'{nama}' nggak dikenal / belum dideklarasi."))

    def jalan(node, sc):
        """Walker generik: Name dipakai; deklarasi didaftarkan."""
        if node is None:
            return
        if isinstance(node, Name):
            dipakai(node.id, node.line, sc)
            return
        if isinstance(node, VarDecl):
            if isinstance(node.name, Destructure):
                for nm in _nama_destructure(node.name):
                    definisikan(sc, nm, node.line)
            else:
                definisikan(sc, node.name, node.line)
            jalan(node.value, sc)
            return
        if isinstance(node, FuncDef):
            definisikan(sc, node.name, node.line)
            fsc = Scope(sc)
            for pname, dflt in node.params:
                fsc.defs[pname] = node.line
                if dflt is not None:
                    jalan(dflt, sc)
            if node.variadic:
                fsc.defs[node.variadic] = node.line
            jalan_block(node.body.statements, fsc)
            _unused(fsc)
            return
        if isinstance(node, (ClassDef, EnumDef)):
            definisikan(sc, node.name, node.line)
            return
        if isinstance(node, Assign):
            jalan(node.value, sc)
            jalan(node.target, sc)
            return
        if isinstance(node, MatchStmt):
            jalan(node.subject, sc)
            for pola, guard, body in node.arms:
                for nm in _pola_binds(pola):
                    definisikan(sc, nm, node.line)
                if guard is not None:
                    jalan(guard, sc)
                jalan_block(body.statements, sc)
            return
        if isinstance(node, IfStmt):
            jalan(node.cond, sc)
            jalan_block(node.then_body.statements, Scope(sc))
            if node.else_body is not None:
                jalan_block(node.else_body.statements, Scope(sc))
            return
        if isinstance(node, WhileStmt):
            jalan(node.cond, sc)
            jalan_block(node.body.statements, Scope(sc))
            return
        if isinstance(node, ForStmt):
            csc = Scope(sc)
            if node.index_var:
                definisikan(csc, node.index_var, node.line)
            definisikan(csc, node.var, node.line)
            jalan(node.iterable, sc)
            jalan_block(node.body.statements, csc)
            return
        if isinstance(node, Block):
            jalan_block(node.statements, Scope(sc))
            return
        if isinstance(node, TryStmt):
            jalan_block(node.body.statements, sc)
            csc = Scope(sc)
            if node.catch_var:
                definisikan(csc, node.catch_var, node.line)
            jalan_block(node.catch_body.statements, csc)
            if node.finally_body is not None:
                jalan_block(node.finally_body.statements, sc)
            return
        if isinstance(node, Call):
            # func bisa Name/Attr/ekspresi lain
            jalan(node.func, sc)
            for a in node.args:
                jalan(a, sc)
            for _nama, val in node.kwargs:
                jalan(val, sc)
            return
        # fallback: telusuri atribut anak yang berupa Node
        for v in vars(node).values():
            if isinstance(v, list):
                for x in v:
                    if isinstance(x, Name) or hasattr(x, "line"):
                        jalan(x, sc)
            elif hasattr(v, "line"):
                jalan(v, sc)

    def jalan_block(stmts, sc):
        for s in stmts:
            jalan(s, sc)

    def _unused(sc):
        for nama, line in sc.defs.items():
            if nama not in sc.used and not nama.startswith("_"):
                masalah.append(("warning", line,
                                f"'{nama}' dideklarasi tapi nggak kepakai."))

    top = Scope(None)
    jalan_block(program.statements, top)
    _unused(top)
    if not masalah:
        print("Valid! Lint bersih, bestie.")
        return 0
    order = {"error": 0, "warning": 1, "info": 2}
    for level, line, pesan in sorted(masalah, key=lambda m: (m[1], order[m[0]])):
        print(f"{path}:{line}: [{level}] {pesan}")
    return 1 if any(m[0] == "error" for m in masalah) else 0


def cmd_dok(path, out=None):
    """Generator dokumentasi: talent/kelas/pilihan + komentar // -> Markdown."""
    from .parser import FuncDef, ClassDef, EnumDef, PropertyDef
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        program = parse(lex(source, path))
    except (JakselError, JakselSyntaxError) as e:
        print(e.pretty(source))
        return 1
    # petakan komentar // tepat di atas tiap baris definisi
    toks = lex(source, path)
    komentar = {}  # line -> teks komentar
    for t in toks:
        if t.kind == "COMMENT":
            komentar.setdefault(t.line, []).append(
                t.value.lstrip("/").strip())
    # cari baris definisi: talent/kelas/pilihan <nama>
    doc = {}

    def ambil_doc(line):
        baris = []
        l = line - 1
        while l in komentar:
            baris.extend(komentar[l])
            l -= 1
        return "\n".join(reversed(baris)).strip()

    for s in program.statements:
        if isinstance(s, (FuncDef, ClassDef, EnumDef)):
            doc[s.name] = ambil_doc(s.line)
    baris = [f"# Dokumentasi `{os.path.basename(path)}`", "",
             "_Dibuat otomatis oleh `jaksel dok`._", ""]
    for s in program.statements:
        if isinstance(s, FuncDef):
            params = ", ".join(
                p + (" = ..." if d else "") for p, d in s.params)
            if s.variadic:
                params += (", " if params else "") + "..." + s.variadic
            baris.append(f"## talent {s.name}({params})")
            if doc.get(s.name):
                baris.append("")
                baris.append(doc[s.name])
            baris.append("")
        elif isinstance(s, ClassDef):
            jud = f"## kelas {s.name}"
            if s.parent:
                jud += f" warisi {s.parent}"
            baris.append(jud)
            if doc.get(s.name):
                baris.append("")
                baris.append(doc[s.name])
            for m in s.methods:
                if isinstance(m, PropertyDef):
                    baris.append(f"- properti `{m.name}`")
                else:
                    tag = " (statik)" if m.static else ""
                    tag += " (rahasia)" if m.private else ""
                    baris.append(f"- talent `{m.name}`{tag}")
            baris.append("")
        elif isinstance(s, EnumDef):
            baris.append(f"## pilihan {s.name}")
            if doc.get(s.name):
                baris.append("")
                baris.append(doc[s.name])
            baris.append("")
            for nama, _v in s.members:
                baris.append(f"- `{nama}`")
            baris.append("")
    teks = "\n".join(baris)
    if out is None:
        base, _ = os.path.splitext(path)
        out = base + ".md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(teks)
    print(f"Valid! Dokumentasi ditulis ke '{out}'.")
    return 0


def cmd_bangun(path, out=None):
    """Build executable tunggal (.pyz via zipapp, stdlib only)."""
    import tempfile
    import zipapp
    if not os.path.exists(path):
        print(f"Red flag: file '{path}' nggak ketemu, bestie.")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        code = transpile_file(path)
    except JakselSyntaxError as e:
        print(e.pretty(source))
        return 1
    except ValueError as e:
        print(f"Red flag: {e}")
        return 1
    if out is None:
        base, _ = os.path.splitext(path)
        out = base + ".pyz"
    paket_dir = os.path.dirname(os.path.abspath(__file__))
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "__main__.py"), "w",
                  encoding="utf-8") as f:
            f.write(code)
        shutil.copytree(paket_dir, os.path.join(tmp, "jaksel"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        zipapp.create_archive(tmp, out,
                              interpreter="/usr/bin/env python3")
    st = os.stat(out)
    try:
        os.chmod(out, st.st_mode | 0o111)
    except OSError:
        pass
    print(f"Valid! Executable tunggal jadi: '{out}'. "
          f"Jalanin: ./{out} (butuh python3).")
    return 0


def cmd_kunci():
    """Tulis jaksel.lock dari paket yang kepasang."""
    import json
    paket_dir = _dir_paket()
    kunci = {"jaksel": VERSION, "paket": {}}
    if os.path.isdir(paket_dir):
        for nama in sorted(os.listdir(paket_dir)):
            man = os.path.join(paket_dir, nama, "paket.json")
            versi, sumber = "?", "?"
            if os.path.isfile(man):
                try:
                    with open(man, encoding="utf-8") as f:
                        m = json.load(f)
                    versi = m.get("versi", "?")
                    sumber = m.get("sumber", "?")
                except (OSError, ValueError):
                    pass
            kunci["paket"][nama] = {"versi": versi, "sumber": sumber}
    with open("jaksel.lock", "w", encoding="utf-8") as f:
        json.dump(kunci, f, indent=2, ensure_ascii=False)
        f.write("\n")
    n = len(kunci["paket"])
    print(f"Valid! jaksel.lock ditulis ({n} paket dikunci).")
    return 0


def cmd_repl():
    print(BANNER)
    print(f"JakselScript v{VERSION} — REPL. Ketik 'cabut' buat keluar.\n")
    _pasang_history()
    interp = Interpreter()
    buf = []
    while True:
        try:
            prompt = "jaksel> " if not buf else "...     "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nCabut dulu, bestie!")
            break
        buf.append(line)
        src = "\n".join(buf)
        # lanjutkan baris kalau kurung kurawal belum seimbang
        if src.count("{") > src.count("}"):
            continue
        buf = []
        if not src.strip():
            continue
        try:
            out = interp.eval_line(src)
            if out is not None:
                print(out)
        except _Exit:
            print("Cabut dulu, bestie!")
            break
        except (JakselError, JakselSyntaxError) as e:
            print(e.pretty(src))


def _pasang_history():
    """History panah atas/bawah di REPL (readline)."""
    try:
        import readline  # noqa: F401
    except ImportError:
        return
    hist = os.path.expanduser(os.path.join("~", ".jaksel", "repl_history"))
    try:
        os.makedirs(os.path.dirname(hist), exist_ok=True)
        try:
            readline.read_history_file(hist)
        except FileNotFoundError:
            pass
        import atexit
        atexit.register(readline.write_history_file, hist)
    except OSError:
        pass


# ---------------- package manager mini ----------------

def _dir_paket():
    d = os.path.expanduser(os.path.join("~", ".jaksel", "paket"))
    os.makedirs(d, exist_ok=True)
    return d


def _nama_dari_sumber(sumber):
    s = sumber.rstrip("/").rstrip("\\")
    if s.endswith(".git"):
        s = s[:-4]
    return os.path.basename(s) or "paket"


def _itu_url_git(sumber):
    s = sumber.lower()
    return (s.startswith(("http://", "https://", "git@", "ssh://"))
            or s.endswith(".git"))


def cmd_kernel(aksi=None):
    """Kernel Jupyter: 'jaksel kernel pasang' daftarkan kernel JakselScript."""
    if aksi != "pasang":
        print("Pakai: jaksel kernel pasang  (daftarkan kernel ke Jupyter)")
        return 2
    try:
        import ipykernel  # noqa: F401
    except ImportError:
        print("Red flag: butuh 'ipykernel'. Pasang dulu: pip install ipykernel")
        return 1
    import json
    import tempfile
    spec = {
        "argv": [sys.executable, "-m", "jaksel.kernel", "-f", "{connection_file}"],
        "display_name": "JakselScript",
        "language": "jakselscript",
    }
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "jakselscript")
        os.makedirs(d)
        with open(os.path.join(d, "kernel.json"), "w",
                  encoding="utf-8") as f:
            json.dump(spec, f, indent=2)
        r = subprocess.run(
            [sys.executable, "-m", "jupyter", "kernelspec", "install",
             "--user", d],
            capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Red flag: gagal pasang kernel:\n{r.stderr.strip()}")
        return 1
    print("Valid! Kernel 'JakselScript' kepasang. Buka Jupyter, pilih kernel "
          "JakselScript, gas!")
    return 0


def cmd_pasang(sumber):
    """Pasang paket .jaksel dari URL git atau folder lokal."""
    nama = _nama_dari_sumber(sumber)
    tujuan = os.path.join(_dir_paket(), nama)
    if os.path.exists(tujuan):
        print(f"Paket '{nama}' udah kepasang, bestie. "
              f"Lepas dulu pakai: jaksel lepas {nama}")
        return 1
    try:
        if _itu_url_git(sumber):
            if shutil.which("git") is None:
                print("Red flag: butuh 'git' buat pasang dari URL, bestie.")
                return 1
            r = subprocess.run(
                ["git", "clone", "--depth", "1", sumber, tujuan],
                capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                print(f"Red flag: gagal clone '{sumber}':\n{r.stderr.strip()}")
                return 1
        else:
            if not os.path.isdir(sumber):
                print(f"Red flag: '{sumber}' bukan URL git / folder, bestie.")
                return 1
            shutil.copytree(sumber, tujuan)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Red flag: gagal pasang paket: {e}")
        return 1
    print(f"Valid! Paket '{nama}' kepasang. Pakai: collab \"{nama}/namafile\"")
    return 0


def cmd_paket():
    """Daftar paket yang kepasang."""
    d = _dir_paket()
    nama2 = sorted(n for n in os.listdir(d)
                  if os.path.isdir(os.path.join(d, n)))
    if not nama2:
        print("Belum ada paket kepasang, bestie. "
              "Coba: jaksel pasang <url-git / folder>")
        return 0
    print("Paket yang kepasang:")
    for n in nama2:
        print(f"  - {n}")
    return 0


def cmd_lepas(nama):
    """Lepas paket yang kepasang."""
    tujuan = os.path.join(_dir_paket(), nama)
    if not os.path.isdir(tujuan):
        print(f"Paket '{nama}' nggak ketemu, bestie.")
        return 1
    try:
        shutil.rmtree(tujuan)
    except OSError as e:
        print(f"Red flag: gagal lepas paket '{nama}': {e}")
        return 1
    print(f"Valid! Paket '{nama}' udah dilepas.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="jaksel",
        description="JakselScript v%s — bahasa pemrograman gaul Jaksel." % VERSION)
    ap.add_argument("sisa", nargs="*",
                    help="perintah lalu file .jaksel. Contoh: gas program.jaksel")
    ap.add_argument("-o", "--output", default=None, help="file .py hasil terjemahan")
    ap.add_argument("--cek", action="store_true",
                    help="mode cek untuk 'rapi': exit 1 kalau belum rapi")
    ap.add_argument("--stdout", action="store_true",
                    help="cetak hasil 'rapi' ke stdout, jangan tulis file")
    ap.add_argument("--token", action="store_true",
                    help="mode 'urai': tampilkan token saja")
    ap.add_argument("--ast", action="store_true",
                    help="mode 'urai': tampilkan AST saja")
    ap.add_argument("--aman", action="store_true",
                    help="mode 'gas': sandbox aman (file/jaringan/shell dibatasi)")
    ap.add_argument("--vm", action="store_true",
                    help="mode 'gas': jalan via VM bytecode, bukan interpreter")
    # parse_intermixed_args: flag boleh diselip di mana aja, mis.
    #   jaksel rapi --stdout f.jaksel  ==  jaksel rapi f.jaksel --stdout
    args = ap.parse_intermixed_args(argv)
    args.perintah = args.sisa[0] if len(args.sisa) > 0 else None
    args.file = args.sisa[1] if len(args.sisa) > 1 else None
    # 'gas' & 'debug' boleh bawa argumen program sendiri di belakang nama file
    prog_args = args.sisa[2:] if args.perintah in ("gas", "debug") else []
    if len(args.sisa) > 2 and args.perintah not in ("gas", "debug"):
        ap.error("kebanyakan argumen, bestie: %s" % " ".join(args.sisa[2:]))

    if args.perintah in (None, "repl"):
        if args.perintah is None and args.file:
            ap.print_help()
            return 2
        cmd_repl()
        return 0
    if args.perintah == "gas":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel gas program.jaksel")
            return 2
        return cmd_gas(args.file, prog_args, aman=args.aman, vm=args.vm)
    if args.perintah == "debug":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel debug program.jaksel")
            return 2
        return cmd_debug(args.file, prog_args)
    if args.perintah == "cek":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel cek program.jaksel")
            return 2
        return cmd_cek(args.file)
    if args.perintah == "alihbahasakan":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel alihbahasakan program.jaksel")
            return 2
        return cmd_alihbahasakan(args.file, args.output)
    if args.perintah == "kompilasi":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel kompilasi program.jaksel")
            return 2
        return cmd_kompilasi(args.file, args.output)
    if args.perintah == "rapi":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel rapi program.jaksel")
            return 2
        return cmd_rapi(args.file, cek=args.cek, stdout=args.stdout)
    if args.perintah == "urai":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel urai program.jaksel")
            return 2
        mode = "semua"
        if args.token and not args.ast:
            mode = "token"
        elif args.ast and not args.token:
            mode = "ast"
        return cmd_urai(args.file, mode)
    if args.perintah == "lsp":
        return cmd_lsp()
    if args.perintah == "tes":
        return cmd_tes(args.file)
    if args.perintah == "baru":
        if not args.file:
            print("Kasih nama proyek dong, bestie. Contoh: jaksel baru proyekku")
            return 2
        return cmd_baru(args.file)
    if args.perintah == "lint":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel lint program.jaksel")
            return 2
        return cmd_lint(args.file)
    if args.perintah == "dok":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel dok program.jaksel")
            return 2
        return cmd_dok(args.file, args.output)
    if args.perintah == "bangun":
        if not args.file:
            print("Kasih nama file dong, bestie. Contoh: jaksel bangun program.jaksel")
            return 2
        return cmd_bangun(args.file, args.output)
    if args.perintah == "kunci":
        return cmd_kunci()
    if args.perintah == "kernel":
        return cmd_kernel(args.file)
    if args.perintah == "pasang":
        if not args.file:
            print("Kasih sumber paket dong, bestie. "
                  "Contoh: jaksel pasang https://github.com/x/paket.jaksel.git")
            return 2
        return cmd_pasang(args.file)
    if args.perintah == "paket":
        return cmd_paket()
    if args.perintah == "lepas":
        if not args.file:
            print("Kasih nama paket dong, bestie. Contoh: jaksel lepas namapaket")
            return 2
        return cmd_lepas(args.file)
    if args.perintah == "versi":
        print(f"JakselScript v{VERSION}")
        return 0
    print(f"Perintah '{args.perintah}' nggak dikenal. Pakai: gas | cek | alihbahasakan | rapi | urai | lsp | tes | baru | lint | dok | bangun | kunci | kernel | debug | pasang | paket | lepas | versi")
    return 2


if __name__ == "__main__":
    sys.exit(main())
