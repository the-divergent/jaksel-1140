"""Parser JakselScript: daftar Token -> AST (recursive descent)."""

from .errors import JakselSyntaxError
from .lexer import Token, lex
import difflib


def _mirip_kw(nama, kandidat):
    cocok = difflib.get_close_matches(nama, list(kandidat), n=1, cutoff=0.75)
    return cocok[0] if cocok else None


def _is_dunder(nama):
    """True untuk nama __x__ (dunder): tidak kena name mangling."""
    return (len(nama) > 4 and nama.startswith("__")
            and nama.endswith("__"))


# ---------------- AST nodes ----------------

class Node:
    pass


class Program(Node):
    def __init__(self, statements):
        self.statements = statements


class Block(Node):
    def __init__(self, statements):
        self.statements = statements


class VarDecl(Node):
    def __init__(self, name, value, line):
        # name: str | Destructure
        self.name, self.value, self.line = name, value, line


class Destructure(Node):
    """Target destructuring: [a, b] atau {kunci: var, ...}."""
    def __init__(self, kind, items, line):
        # kind "list": items = [nama_var, ...]
        # kind "dict": items = [(kunci, nama_var), ...]
        self.kind, self.items, self.line = kind, items, line


class Assign(Node):
    def __init__(self, target, value, line):
        # target: Name | Index | Attr | Destructure
        self.target, self.value, self.line = target, value, line


class IfStmt(Node):
    def __init__(self, cond, then_block, elifs, else_block, line):
        self.cond, self.then_block = cond, then_block
        self.elifs = elifs            # list of (cond, block)
        self.else_block = else_block
        self.line = line


class WhileStmt(Node):
    def __init__(self, cond, body, line):
        self.cond, self.body, self.line = cond, body, line


class ForStmt(Node):
    def __init__(self, var, iterable, body, line, idx_var=None):
        self.var, self.iterable, self.body, self.line = var, iterable, body, line
        self.idx_var = idx_var   # stalk i, x dalam ... -> i = index


class FuncDef(Node):
    def __init__(self, name, params, body, line, variadic=None,
                 static=False, private=False):
        # params: list[(nama, default_node|None)]
        # variadic: nama parameter ...sisa (tampung sisa argumen jadi daftar)
        self.name, self.params, self.body, self.line = name, params, body, line
        self.variadic = variadic
        self.static = static      # method statik: dipanggil lewat Kelas.nama()
        self.private = private    # 'rahasia' / nama berawalan _: akses terbatas


class PropertyDef(Node):
    """properti nama { ambil { ... } taruh(nilai) { ... } } di dalam kelas."""
    def __init__(self, name, getter_body, setter_param, setter_body, line):
        self.name = name
        self.getter_body = getter_body      # Block | None
        self.setter_param = setter_param    # str | None
        self.setter_body = setter_body      # Block | None
        self.line = line


class ClassDef(Node):
    """kelas Nama warisi Ibu { talent ...; properti ... }"""
    def __init__(self, name, parent, methods, line):
        # methods: list[FuncDef | PropertyDef]
        self.name, self.parent, self.methods, self.line = name, parent, methods, line


class ThisExpr(Node):
    """'ini' di dalam method: instance yang sedang jalan."""
    def __init__(self, line):
        self.line = line


class SuperExpr(Node):
    """'ortu': akses method kelas induk. Harus diikuti .nama(...)."""
    def __init__(self, line):
        self.line = line


class ReturnStmt(Node):
    def __init__(self, value, line):
        self.value, self.line = value, line


class BreakStmt(Node):
    pass


class ContinueStmt(Node):
    pass


class TryStmt(Node):
    def __init__(self, body, catch_var, catch_body, line, finally_body=None,
                 catch_class=None):
        self.body, self.catch_var, self.catch_body, self.line = body, catch_var, catch_body, line
        self.finally_body = finally_body
        self.catch_class = catch_class  # yaudah HttpError e -> tangkap khusus


class ThrowStmt(Node):
    def __init__(self, value, line):
        self.value, self.line = value, line


class MatchStmt(Node):
    """cocokkan nilai { pola [kalo syarat] => blok, ... }"""
    def __init__(self, subject, arms, line):
        # arms: list[(pola, guard|None, Block)]
        self.subject, self.arms, self.line = subject, arms, line


class PatWild(Node):
    """pola '_' : cocok dengan apa pun."""
    def __init__(self, line):
        self.line = line


class PatLit(Node):
    """pola literal: angka/teks/valid/gimmick/zonk."""
    def __init__(self, value, line):
        self.value, self.line = value, line


class PatBind(Node):
    """pola 'nama': cocok apa pun, ikat ke variabel."""
    def __init__(self, name, line, rest=False):
        self.name, self.line, self.rest = name, line, rest


class PatType(Node):
    """pola 'NamaKelas': cocok kalau instance dari kelas itu."""
    def __init__(self, name, line):
        self.name, self.line = name, line


class PatEnum(Node):
    """pola 'Warna.MERAH': cocok kalau anggota enum itu persis."""
    def __init__(self, enum_name, member_name, line):
        self.enum_name, self.member_name, self.line = enum_name, member_name, line


class PatList(Node):
    """pola [p1, p2]: cocok daftar dengan panjang sama."""
    def __init__(self, items, line):
        self.items, self.line = items, line


class PatDict(Node):
    """pola {kunci: pola}: cocok kamus yang punya kunci itu."""
    def __init__(self, items, line):
        # items: list[(kunci_str, pola)]
        self.items, self.line = items, line


class EnumDef(Node):
    """pilihan Warna { MERAH, HIJAU, BIRU }"""
    def __init__(self, name, members, line):
        # members: list[(nama, nilai_node|None)]
        self.name, self.members, self.line = name, members, line


class Spread(Node):
    """...daftar di dalam argumen panggilan: sebar jadi beberapa argumen."""
    def __init__(self, value, line):
        self.value, self.line = value, line


class ExitStmt(Node):
    def __init__(self, code, line):
        self.code, self.line = code, line


class ImportStmt(Node):
    def __init__(self, path, line, alias=None, ambil=None, py_module=None):
        # collab "x" | collab "x" sebagai u | collab "x" ambil a, b
        # collab python "os" [sebagai o | ambil getcwd, ...]
        self.path, self.line = path, line
        self.alias = alias        # str | None
        self.ambil = ambil        # list[str] | None
        self.py_module = py_module  # str | None (nama modul Python)


class ExprStmt(Node):
    def __init__(self, expr, line=None):
        self.expr = expr
        self.line = line


class BinOp(Node):
    def __init__(self, op, left, right, line):
        self.op, self.left, self.right, self.line = op, left, right, line


class UnaryOp(Node):
    def __init__(self, op, operand, line):
        self.op, self.operand, self.line = op, operand, line


class NotOp(Node):
    def __init__(self, operand, line):
        self.operand, self.line = operand, line


class Call(Node):
    def __init__(self, func, args, line, kwargs=None):
        # args: list[expr | Spread]; kwargs: list[(nama, expr)]
        self.func, self.args, self.line = func, args, line
        self.kwargs = kwargs or []


class Index(Node):
    def __init__(self, obj, index, line):
        self.obj, self.index, self.line = obj, index, line


class Slice(Node):
    """obj[mulai:akhir:langkah] — tiap bagian boleh kosong (zonk)."""
    def __init__(self, obj, mulai, akhir, langkah, line):
        self.obj = obj
        self.mulai = mulai
        self.akhir = akhir
        self.langkah = langkah
        self.line = line


class IfExpr(Node):
    """nilai kalo kondisi selain default — ternary expression."""
    def __init__(self, cond, then, else_, line):
        self.cond = cond
        self.then = then
        self.else_ = else_
        self.line = line


class Comp(Node):
    """[expr buat x dalam iterable kalo kondisi] — list comprehension."""
    def __init__(self, expr, var, iterable, cond, line):
        self.expr = expr
        self.var = var
        self.iterable = iterable
        self.cond = cond  # boleh None
        self.line = line


class ChainComp(Node):
    """1 < x < 10 — perbandingan berantai, tiap operan dievaluasi sekali."""
    def __init__(self, first, ops, operands, line):
        self.first = first
        self.ops = ops            # ["<", "<"]
        self.operands = operands  # [x, 10]
        self.line = line


class ExportStmt(Node):
    """ekspor a, b, c — tandai nama yang boleh di-collab dari modul ini."""
    def __init__(self, names, line):
        self.names = names  # list[str]
        self.line = line


class Attr(Node):
    def __init__(self, obj, name, line, optional=False):
        self.obj, self.name, self.line = obj, name, line
        self.optional = optional  # True buat '?.' — zonk?.x = zonk


class Name(Node):
    def __init__(self, id, line):
        self.id, self.line = id, line


class Literal(Node):
    def __init__(self, value):
        self.value = value


class ListLit(Node):
    def __init__(self, elements):
        self.elements = elements


class DictLit(Node):
    def __init__(self, pairs):
        self.pairs = pairs  # list of (key_str, value_node)


class InterpString(Node):
    """String dengan interpolasi {ekspresi}. parts = [("teks", str) | ("ekspresi", node)]."""
    def __init__(self, parts):
        self.parts = parts


# ---------------- Parser ----------------

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self._mangle = None      # nama 'rahasia' -> nama mangling (aktif di badan kelas)
        self._mangle_cls = None  # nama kelas yang badannya sedang di-parse

    # -- helpers --
    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def err(self, msg, tok=None):
        tok = tok or self.peek()
        return JakselSyntaxError(msg, tok.line, tok.col)

    def expect_op(self, op):
        tok = self.peek()
        if tok.kind == "OP" and tok.value == op:
            return self.advance()
        raise self.err(f"harusnya ada '{op}' di sini, bestie.")

    def expect_kw(self, kw):
        tok = self.peek()
        if tok.kind == "KEYWORD" and tok.value == kw:
            return self.advance()
        raise self.err(f"harusnya ada '{kw}' di sini.")

    def at_kw(self, kw):
        tok = self.peek()
        return tok.kind == "KEYWORD" and tok.value == kw

    def at_op(self, op):
        tok = self.peek()
        return tok.kind == "OP" and tok.value == op

    # -- entry --
    def parse(self):
        stmts = []
        while self.peek().kind != "EOF":
            stmts.append(self.statement())
        return Program(stmts)

    def block(self):
        self.expect_op("{")
        stmts = []
        while not self.at_op("}"):
            if self.peek().kind == "EOF":
                raise self.err("blok nggak ditutup. Mana '}' pasangannya?")
            stmts.append(self.statement())
        self.expect_op("}")
        return Block(stmts)

    # -- statements --
    STATEMENT_KWS = {
        "bestie", "kalo", "selama", "gamon", "stalk", "talent", "balikin",
        "ghosting", "skip", "yolo", "red_flag", "collab", "ekspor", "cabut",
        "kelas", "cocokkan",
    }

    def statement(self):
        tok = self.peek()
        if tok.kind == "KEYWORD" and tok.value in self.STATEMENT_KWS:
            kw = tok.value
            if kw == "bestie":
                return self.var_decl()
            if kw == "kalo":
                return self.if_stmt()
            if kw == "selama":
                return self.while_stmt()
            if kw == "gamon":
                return self.gamon_stmt()
            if kw == "stalk":
                return self.for_stmt()
            if kw == "talent":
                return self.func_def()
            if kw == "balikin":
                return self.return_stmt()
            if kw == "ghosting":
                self.advance()
                return BreakStmt()
            if kw == "skip":
                self.advance()
                return ContinueStmt()
            if kw == "yolo":
                return self.try_stmt()
            if kw == "red_flag":
                return self.throw_stmt()
            if kw == "collab":
                return self.import_stmt()
            if kw == "ekspor":
                return self.export_stmt()
            if kw == "cabut":
                return self.exit_stmt()
            if kw == "kelas":
                return self.class_def()
            if kw == "cocokkan":
                return self.match_stmt()
            raise self.err(f"keyword '{kw}' nggak bisa dipakai di sini.")
        # 'pilihan' kontekstual: pilihan Warna { ... } (enum).
        # Bukan keyword beneran biar kode lama yang pakai nama itu aman.
        if tok.kind == "IDENT" and tok.value == "pilihan" \
                and self.pos + 1 < len(self.tokens):
            nxt = self.tokens[self.pos + 1]
            if nxt.kind == "IDENT":
                return self.enum_def()
        # typo keyword di posisi statement: 'kallo' -> 'kalo'
        # (bukan assignment/pemanggilan: token berikutnya bukan = ( . [)
        if tok.kind == "IDENT" and self.pos + 1 < len(self.tokens):
            nxt = self.tokens[self.pos + 1]
            bukan_awal_valid = not (
                nxt.kind == "OP" and nxt.value in ("=", "(", ".", "["))
            if bukan_awal_valid:
                saran = _mirip_kw(tok.value, self.STATEMENT_KWS)
                if saran:
                    raise self.err(
                        f"'{tok.value}' nggak dikenal di sini, bestie. "
                        f"Maksudnya '{saran}'?")
        # assignment atau expression statement
        # target destructuring: [a, b] = ... / {k: v} = ...
        # (pastikan beneran destructuring: kurung tutupnya diikuti '=')
        tok2 = self.peek()
        if tok2.kind == "OP" and tok2.value in ("[", "{") \
                and self._is_destructure_assign():
            target = self._destructure_target()
            self.expect_op("=")
            return Assign(target, self.expr(), tok2.line)
        expr = self.expr()
        if self.at_op("="):
            if not isinstance(expr, (Name, Index, Attr)):
                raise self.err("yang di kiri '=' harus variabel / index / atribut.")
            self.advance()
            return Assign(expr, self.expr(), tok.line)
        return ExprStmt(expr, getattr(expr, "line", None) or tok.line)

    def _is_destructure_assign(self):
        """Lookahead: [a, b] = ... atau {k, k2: v} = ... ?

        Isi kurung harus valid sebagai target destructuring (nama variabel /
        kunci, bukan angka), dan kurung tutupnya diikuti '='.
        """
        toks = self.tokens
        i = self.pos
        if i >= len(toks) or toks[i].kind != "OP" \
                or toks[i].value not in ("[", "{"):
            return False
        buka = toks[i].value
        tutup = "]" if buka == "[" else "}"
        i += 1
        if buka == "[":
            # [a, b, ...sisa]: isinya harus nama variabel
            while True:
                if i < len(toks) and toks[i].kind == "OP" \
                        and toks[i].value == "...":
                    i += 1  # ...sisa
                if i >= len(toks) or toks[i].kind != "IDENT":
                    return False
                i += 1
                if i < len(toks) and toks[i].kind == "OP" \
                        and toks[i].value == ",":
                    i += 1
                    continue
                break
        else:
            # {k, k2: v, ...}: kunci teks/nama, opsional ': var'
            while True:
                if i >= len(toks) or toks[i].kind not in ("IDENT", "STRING"):
                    return False
                i += 1
                if i < len(toks) and toks[i].kind == "OP" \
                        and toks[i].value == ":":
                    i += 1
                    if i >= len(toks) or toks[i].kind != "IDENT":
                        return False
                    i += 1
                if i < len(toks) and toks[i].kind == "OP" \
                        and toks[i].value == ",":
                    i += 1
                    continue
                break
        if i >= len(toks) or toks[i].kind != "OP" or toks[i].value != tutup:
            return False
        i += 1
        return (i < len(toks) and toks[i].kind == "OP"
                and toks[i].value == "=")

    def var_decl(self):
        kw = self.expect_kw("bestie")
        tok = self.peek()
        if tok.kind == "OP" and tok.value in ("[", "{"):
            # destructuring: bestie [a, b] = ... / bestie {k: v} = ...
            target = self._destructure_target()
            self.expect_op("=")
            return VarDecl(target, self.expr(), kw.line)
        if tok.kind != "IDENT":
            raise self.err("habis 'bestie' harus nama variabel.")
        name = self.advance().value
        self.expect_op("=")
        return VarDecl(name, self.expr(), kw.line)

    def _destructure_target(self):
        """Parse [a, b] atau {kunci: var, kunci2} jadi Destructure."""
        tok = self.peek()
        if tok.value == "[":
            self.advance()
            items = []
            if not self.at_op("]"):
                while True:
                    t = self.peek()
                    if self.at_op("..."):  # [a, ...sisa]
                        self.advance()
                        t2 = self.peek()
                        if t2.kind != "IDENT":
                            raise self.err(
                                "habis '...' harus nama variabel, bestie.")
                        items.append("..." + self.advance().value)
                    elif t.kind == "IDENT":
                        items.append(self.advance().value)
                    else:
                        raise self.err(
                            "destructuring daftar isinya nama variabel.")
                    if self.at_op(","):
                        self.advance()
                        continue
                    break
            self.expect_op("]")
            if not items:
                raise self.err("destructuring daftar nggak boleh kosong.")
            return Destructure("list", items, tok.line)
        # kamus: {nama} atau {nama: varbaru}
        self.advance()
        items = []
        if not self.at_op("}"):
            while True:
                kt = self.peek()
                if kt.kind == "STRING":
                    key = self.advance().value
                elif kt.kind == "IDENT":
                    key = self.advance().value
                else:
                    raise self.err("kunci destructuring harus teks atau nama.")
                var = key
                if self.at_op(":"):
                    self.advance()
                    t = self.peek()
                    if t.kind != "IDENT":
                        raise self.err("habis ':' harus nama variabel.")
                    var = self.advance().value
                items.append((key, var))
                if self.at_op(","):
                    self.advance()
                    continue
                break
        self.expect_op("}")
        if not items:
            raise self.err("destructuring kamus nggak boleh kosong.")
        return Destructure("dict", items, tok.line)

    def if_stmt(self):
        kw = self.expect_kw("kalo")
        cond = self.expr()
        then_b = self.block()
        elifs = []
        else_b = None
        while self.at_kw("plot_twist"):
            self.advance()
            if self.at_kw("kalo"):
                self.advance()
                elifs.append((self.expr(), self.block()))
            else:
                else_b = self.block()
                break
        return IfStmt(cond, then_b, elifs, else_b, kw.line)

    def while_stmt(self):
        kw = self.expect_kw("selama")
        return WhileStmt(self.expr(), self.block(), kw.line)

    def gamon_stmt(self):
        kw = self.expect_kw("gamon")
        return WhileStmt(Literal(True), self.block(), kw.line)

    def for_stmt(self):
        kw = self.expect_kw("stalk")
        tok = self.peek()
        if tok.kind != "IDENT":
            raise self.err("habis 'stalk' harus nama variabel.")
        var = self.advance().value
        idx_var = None
        if self.at_op(","):
            # stalk i, x dalam daftar -> i = index, x = elemen
            self.advance()
            t2 = self.peek()
            if t2.kind != "IDENT":
                raise self.err("habis ',' harus nama variabel index.")
            idx_var = var
            var = self.advance().value
        self.expect_kw("dalam")
        return ForStmt(var, self.expr(), self.block(), kw.line, idx_var)

    def _param_list(self):
        """Parse (a, b = 1, c = "x", ...sisa). Kembalikan (params, variadic).

        params: [(nama, default|None)], variadic: nama|None.
        """
        params = []
        variadic = None
        self.expect_op("(")
        if not self.at_op(")"):
            while True:
                t = self.peek()
                if self.at_op("..."):
                    self.advance()
                    t2 = self.peek()
                    if t2.kind != "IDENT":
                        raise self.err("habis '...' harus nama parameter.")
                    if variadic is not None:
                        raise self.err("cuma boleh satu '...sisa', bestie.")
                    variadic = self.advance().value
                    # ...sisa harus paling belakang
                    if not self.at_op(")"):
                        raise self.err(
                            "'...sisa' harus jadi parameter paling belakang.")
                    break
                if t.kind != "IDENT":
                    raise self.err("parameter harus nama, bestie.")
                nama = self.advance().value
                default = None
                if self.at_op("="):
                    self.advance()
                    default = self.expr()
                params.append((nama, default))
                if self.at_op(","):
                    self.advance()
                    continue
                break
        self.expect_op(")")
        # default harus di belakang (ala Python)
        ketemu_default = False
        for nama, default in params:
            if default is not None:
                ketemu_default = True
            elif ketemu_default:
                raise self.err(
                    f"parameter '{nama}' nggak punya default padahal "
                    "parameter sebelumnya punya. Default harus di belakang, bestie.")
        return params, variadic

    def func_def(self):
        kw = self.expect_kw("talent")
        tok = self.peek()
        if tok.kind != "IDENT":
            raise self.err("habis 'talent' harus nama fungsi.")
        name = self.advance().value
        params, variadic = self._param_list()
        return FuncDef(name, params, self.block(), kw.line, variadic=variadic)

    def _mangle_name(self, nama):
        """Terapkan name mangling untuk nama member kelas."""
        if _is_dunder(nama):
            return nama
        if self._mangle and nama in self._mangle:
            return self._mangle[nama]
        if nama.startswith("_") and self._mangle_cls:
            prefix = f"_{self._mangle_cls}__"
            if nama.startswith(prefix):
                return nama  # sudah di-mangle, jangan dobel
            return f"{prefix}{nama.lstrip('_')}"
        return nama

    def _scan_class_members(self):
        """Pre-scan token badan kelas -> [(kind, nama, private)].

        kind 'talent'|'properti'. Dipakai membangun peta mangling untuk
        member yang dideklarasikan 'rahasia' (tanpa garis bawah).
        """
        out = []
        depth = 0
        i = self.pos
        toks = self.tokens
        while i < len(toks):
            t = toks[i]
            if t.kind == "OP":
                if t.value == "{":
                    depth += 1
                elif t.value == "}":
                    depth -= 1
                    if depth == 0:
                        break
            elif depth == 1 and t.kind == "IDENT":
                j = i
                private = False
                while j < len(toks) and toks[j].kind == "IDENT" \
                        and toks[j].value in ("rahasia", "statik"):
                    if toks[j].value == "rahasia":
                        private = True
                    j += 1
                if j < len(toks) and toks[j].value in ("talent", "properti") \
                        and toks[j].kind in ("IDENT", "KEYWORD"):
                    k = j + 1
                    if k < len(toks) and toks[k].kind == "IDENT":
                        nama = toks[k].value
                        if nama.startswith("_"):
                            private = True
                        out.append((toks[j].value, nama, private))
                        i = k
            i += 1
        return out

    def property_def(self):
        """properti nama { ambil { ... } taruh(param) { ... } }"""
        kw = self.advance()  # 'properti'
        t = self.peek()
        if t.kind != "IDENT":
            raise self.err("habis 'properti' harus nama, bestie.")
        name = self._mangle_name(self.advance().value)
        self.expect_op("{")
        getter = setter_param = setter = None
        while not self.at_op("}"):
            t = self.peek()
            if t.kind != "IDENT" or t.value not in ("ambil", "taruh"):
                raise self.err(
                    "di dalam properti cuma boleh 'ambil' / 'taruh', bestie.", t)
            if t.value == "ambil":
                self.advance()
                if getter is not None:
                    raise self.err("'ambil' ditulis dua kali, bestie.")
                getter = self.block()
            else:
                self.advance()
                self.expect_op("(")
                pt = self.peek()
                if pt.kind != "IDENT":
                    raise self.err("'taruh' butuh satu nama parameter.")
                setter_param = self.advance().value
                self.expect_op(")")
                if setter is not None:
                    raise self.err("'taruh' ditulis dua kali, bestie.")
                setter = self.block()
        self.expect_op("}")
        if getter is None and setter is None:
            raise self.err("properti butuh 'ambil' dan/atau 'taruh', bestie.")
        return PropertyDef(name, getter, setter_param, setter, kw.line)

    def class_def(self):
        kw = self.expect_kw("kelas")
        tok = self.peek()
        if tok.kind != "IDENT":
            raise self.err("habis 'kelas' harus nama kelas, bestie.")
        name = self.advance().value
        parent = None
        if self.at_kw("warisi"):
            self.advance()
            t2 = self.peek()
            if t2.kind != "IDENT":
                raise self.err("habis 'warisi' harus nama kelas induk.")
            parent = self.advance().value
        # peta mangling untuk member 'rahasia' (pre-scan biar forward-ref aman)
        mangle = {}
        for _kind, mnama, private in self._scan_class_members():
            if private and not mnama.startswith("_") \
                    and not _is_dunder(mnama):
                mangle[mnama] = f"_{name}__{mnama}"
        lama_mangle, lama_cls = self._mangle, self._mangle_cls
        self._mangle, self._mangle_cls = mangle, name
        try:
            self.expect_op("{")
            members = []
            while not self.at_op("}"):
                if self.peek().kind == "EOF":
                    raise self.err("blok kelas nggak ditutup. Mana '}' pasangannya?")
                t = self.peek()
                if t.kind == "IDENT" and t.value == "properti":
                    members.append(self.property_def())
                    continue
                # modifier kontekstual: rahasia / statik (urutan bebas)
                statik = False
                private = False
                while self.peek().kind == "IDENT" \
                        and self.peek().value in ("rahasia", "statik"):
                    if self.peek().value == "rahasia":
                        private = True
                    else:
                        statik = True
                    self.advance()
                if not self.at_kw("talent"):
                    raise self.err(
                        "di dalam kelas cuma boleh 'talent' atau 'properti', "
                        "bestie.", self.peek())
                fn = self.func_def()
                fn.static = statik
                fn.private = private
                fn.name = self._mangle_name(fn.name)
                if statik and fn.name == "lahir":
                    raise self.err("'lahir' nggak boleh statik, bestie.")
                members.append(fn)
            self.expect_op("}")
        finally:
            self._mangle, self._mangle_cls = lama_mangle, lama_cls
        return ClassDef(name, parent, members, kw.line)

    def match_stmt(self):
        """cocokkan nilai { pola [kalo syarat] => { ... } }"""
        kw = self.expect_kw("cocokkan")
        subject = self.expr()
        self.expect_op("{")
        arms = []
        while not self.at_op("}"):
            if self.peek().kind == "EOF":
                raise self.err("blok 'cocokkan' nggak ditutup. Mana '}' pasangannya?")
            pola = self._pattern()
            guard = None
            if self.at_kw("kalo"):
                self.advance()
                guard = self.expr()
            self.expect_op("=>")
            body = self.block()
            arms.append((pola, guard, body))
            if self.at_op(","):
                self.advance()  # koma antar arm: opsional
        self.expect_op("}")
        if not arms:
            raise self.err("'cocokkan' butuh minimal satu pola, bestie.")
        return MatchStmt(subject, arms, kw.line)

    def _pattern(self):
        tok = self.peek()
        if tok.kind == "NUMBER":
            self.advance()
            return PatLit(tok.value, tok.line)
        if tok.kind == "STRING":
            self.advance()
            return PatLit(tok.value, tok.line)
        if tok.kind == "KEYWORD" and tok.value in ("valid", "gimmick", "zonk"):
            self.advance()
            return PatLit({"valid": True, "gimmick": False, "zonk": None}[tok.value],
                          tok.line)
        if tok.kind == "IDENT":
            self.advance()
            if tok.value == "_":
                return PatWild(tok.line)
            # Nama berawalan huruf besar = pola tipe (cek instanceof)
            if tok.value[0].isupper():
                if self.at_op("."):  # Warna.MERAH -> pola anggota enum
                    self.advance()
                    mtok = self.peek()
                    if mtok.kind != "IDENT":
                        raise self.err(
                            "setelah 'Warna.' harusnya ada nama anggota, bestie.")
                    self.advance()
                    return PatEnum(tok.value, mtok.value, tok.line)
                return PatType(tok.value, tok.line)
            return PatBind(tok.value, tok.line)
        if tok.kind == "OP" and tok.value == "[":
            self.advance()
            items = []
            if not self.at_op("]"):
                while True:
                    if self.at_op("..."):  # [kepala, ...sisa]
                        self.advance()
                        ntok = self.peek()
                        if ntok.kind != "IDENT":
                            raise self.err(
                                "habis '...' harus nama variabel, bestie.")
                        self.advance()
                        items.append(PatBind(ntok.value, ntok.line, rest=True))
                    else:
                        items.append(self._pattern())
                    if self.at_op(","):
                        self.advance()
                        continue
                    break
            self.expect_op("]")
            return PatList(items, tok.line)
        if tok.kind == "OP" and tok.value == "{":
            self.advance()
            items = []
            if not self.at_op("}"):
                while True:
                    kt = self.peek()
                    if kt.kind == "STRING":
                        key = self.advance().value
                    elif kt.kind == "IDENT":
                        key = self.advance().value
                    else:
                        raise self.err("kunci pola kamus harus teks atau nama.")
                    self.expect_op(":")
                    items.append((key, self._pattern()))
                    if self.at_op(","):
                        self.advance()
                        continue
                    break
            self.expect_op("}")
            return PatDict(items, tok.line)
        raise self.err("pola 'cocokkan' nggak valid di sini.", tok)

    def enum_def(self):
        """pilihan Warna { MERAH, HIJAU = 10, BIRU }"""
        kw = self.advance()  # 'pilihan'
        t = self.peek()
        if t.kind != "IDENT":
            raise self.err("habis 'pilihan' harus nama enum, bestie.")
        name = self.advance().value
        self.expect_op("{")
        members = []
        if not self.at_op("}"):
            while True:
                t = self.peek()
                if t.kind != "IDENT":
                    raise self.err("anggota enum harus nama, bestie.")
                mnama = self.advance().value
                mval = None
                if self.at_op("="):
                    self.advance()
                    mval = self.expr()
                members.append((mnama, mval))
                if self.at_op(","):
                    self.advance()
                    continue
                break
        self.expect_op("}")
        if not members:
            raise self.err("enum nggak boleh kosong, bestie.")
        return EnumDef(name, members, kw.line)

    def return_stmt(self):
        kw = self.expect_kw("balikin")
        # balikin tanpa nilai kalau langsung ketemu } atau EOF atau keyword statement
        tok = self.peek()
        if tok.kind == "EOF" or self.at_op("}"):
            return ReturnStmt(Literal(None), kw.line)
        return ReturnStmt(self.expr(), kw.line)

    def try_stmt(self):
        kw = self.expect_kw("yolo")
        body = self.block()
        self.expect_kw("yaudah")
        catch_var = None
        catch_class = None
        if self.peek().kind == "IDENT":
            pertama = self.advance().value
            if self.peek().kind == "IDENT":
                # yaudah HttpError e -> tangkap khusus kelas itu
                catch_class = pertama
                catch_var = self.advance().value
            else:
                catch_var = pertama
        catch_body = self.block()
        finally_body = None
        if self.at_kw("akhirnya"):
            self.advance()
            finally_body = self.block()
        return TryStmt(body, catch_var, catch_body, kw.line, finally_body,
                       catch_class)

    def throw_stmt(self):
        kw = self.expect_kw("red_flag")
        return ThrowStmt(self.expr(), kw.line)

    def export_stmt(self):
        kw = self.expect_kw("ekspor")
        names = []
        while True:
            t = self.peek()
            if t.kind != "IDENT":
                raise self.err("habis 'ekspor' harus nama, bestie.")
            names.append(self.advance().value)
            if self.at_op(","):
                self.advance()
                continue
            break
        return ExportStmt(names, kw.line)

    def import_stmt(self):
        kw = self.expect_kw("collab")
        tok = self.peek()
        py_module = None
        path = None
        if tok.kind == "IDENT" and tok.value == "python":
            # collab python "os" -> jembatan ke modul Python
            self.advance()
            t2 = self.peek()
            if t2.kind != "STRING":
                raise self.err(
                    "'collab python' butuh nama modul, contoh: collab python \"os\"")
            py_module = self.advance().value
        elif tok.kind == "STRING":
            path = self.advance().value
        else:
            raise self.err("'collab' butuh nama file teks, contoh: collab \"utils\"")
        # 'sebagai' / 'ambil' itu kontekstual (bukan keyword) biar kode lama aman
        alias = None
        ambil = None
        t = self.peek()
        if t.kind == "IDENT" and t.value == "sebagai":
            self.advance()
            t2 = self.peek()
            if t2.kind != "IDENT":
                raise self.err("habis 'sebagai' harus nama alias, bestie.")
            alias = self.advance().value
        elif t.kind == "IDENT" and t.value == "ambil":
            self.advance()
            ambil = []
            while True:
                t2 = self.peek()
                if t2.kind != "IDENT":
                    raise self.err(
                        "habis 'ambil' harus nama-nama yang mau diambil, bestie.")
                ambil.append(self.advance().value)
                if self.at_op(","):
                    self.advance()
                    continue
                break
        if alias is not None and ambil is not None:
            raise self.err("'sebagai' dan 'ambil' nggak bisa barengan, bestie.")
        return ImportStmt(path, kw.line, alias=alias, ambil=ambil,
                          py_module=py_module)

    def exit_stmt(self):
        kw = self.expect_kw("cabut")
        tok = self.peek()
        if tok.kind == "EOF" or self.at_op("}"):
            return ExitStmt(Literal(0), kw.line)
        return ExitStmt(self.expr(), kw.line)

    # -- expressions (precedence climbing) --
    def expr(self):
        # ternary: nilai kalo kondisi selain default (asosiatif kanan)
        # 'kalo' harus sebaris dengan ekspresi — kalo di baris baru itu
        # statement if, bukan ternary.
        node = self.coalesce_expr()
        if self.at_kw("kalo"):
            kalo_tok = self.peek()
            prev_tok = self.tokens[self.pos - 1]
            if kalo_tok.line != prev_tok.line:
                return node
            tok = self.advance()
            cond = self.coalesce_expr()
            if not self.at_kw("selain"):
                raise self.err("ternary butuh 'selain', bestie: "
                               "'nilai kalo kondisi selain default'.")
            self.advance()
            else_ = self.expr()
            node = IfExpr(cond, node, else_, tok.line)
        return node

    def coalesce_expr(self):
        # '??' asosiatif kanan: a ?? b ?? c = a ?? (b ?? c)
        node = self.or_expr()
        if self.at_op("??"):
            op_tok = self.advance()
            node = BinOp("??", node, self.coalesce_expr(), op_tok.line)
        return node

    def or_expr(self):
        node = self.and_expr()
        while self.at_kw("atau"):
            op_tok = self.advance()
            node = BinOp("atau", node, self.and_expr(), op_tok.line)
        return node

    def and_expr(self):
        node = self.not_expr()
        while self.at_kw("dan"):
            op_tok = self.advance()
            node = BinOp("dan", node, self.not_expr(), op_tok.line)
        return node

    def not_expr(self):
        if self.at_kw("nggak"):
            tok = self.advance()
            return NotOp(self.not_expr(), tok.line)
        return self.comparison()

    def comparison(self):
        node = self.additive()
        ops = []
        operands = []
        while True:
            tok = self.peek()
            if tok.kind == "OP" and tok.value in ("==", "!=", "<", ">", "<=", ">="):
                self.advance()
                ops.append(tok.value)
                operands.append(self.additive())
            elif tok.kind == "KEYWORD" and tok.value == "dalam":
                # 'x dalam daftar' = membership test, bisa dipakai di ekspresi apa pun
                self.advance()
                ops.append("dalam")
                operands.append(self.additive())
            else:
                break
        if not ops:
            return node
        if len(ops) == 1:
            return BinOp(ops[0], node, operands[0], tok.line)
        return ChainComp(node, ops, operands, tok.line)

    def additive(self):
        node = self.multiplicative()
        while True:
            tok = self.peek()
            if tok.kind == "OP" and tok.value in ("+", "-"):
                self.advance()
                node = BinOp(tok.value, node, self.multiplicative(), tok.line)
            else:
                return node

    def multiplicative(self):
        node = self.unary()
        while True:
            tok = self.peek()
            if tok.kind == "OP" and tok.value in ("*", "/", "%"):
                self.advance()
                node = BinOp(tok.value, node, self.unary(), tok.line)
            else:
                return node

    def unary(self):
        if self.at_op("-"):
            tok = self.advance()
            return UnaryOp("-", self.unary(), tok.line)
        return self.postfix()

    def postfix(self):
        node = self.primary()
        if isinstance(node, SuperExpr) and not self.at_op("."):
            raise self.err("'ortu' harus diikuti '.nama_method(...)', bestie.")
        while True:
            if self.at_op("("):
                # pemanggilan: nama(...) atau obj.method(...) atau f()(...)
                # argumen: posisi, nama=..., dan sebar ...daftar
                tok = self.advance()
                args = []
                kwargs = []
                if not self.at_op(")"):
                    while True:
                        if self.at_op("..."):
                            if kwargs:
                                raise self.err(
                                    "argumen posisi nggak boleh habis argumen "
                                    "bernama (nama=...), bestie.")
                            self.advance()
                            args.append(Spread(self.expr(), tok.line))
                        elif self.peek().kind == "IDENT" \
                                and self.pos + 1 < len(self.tokens) \
                                and self.tokens[self.pos + 1].kind == "OP" \
                                and self.tokens[self.pos + 1].value == "=":
                            nama = self.advance().value
                            self.advance()  # '='
                            kwargs.append((nama, self.expr()))
                        else:
                            if kwargs:
                                raise self.err(
                                    "argumen posisi nggak boleh habis argumen "
                                    "bernama (nama=...), bestie.")
                            args.append(self.expr())
                        if self.at_op(","):
                            self.advance()
                            continue
                        break
                self.expect_op(")")
                node = Call(node, args, tok.line, kwargs)
            elif self.at_op("["):
                # '[a, b] = ...' di AWAL baris baru setelah sebuah ekspresi
                # itu destructuring-assign statement baru, BUKAN index
                # lanjutan (mis. "orang\n[a, b] = ..."). Index biasa
                # ("data[i] = 5" sebaris) tetap jalan seperti dulu.
                br = self.peek()
                prev = self.tokens[self.pos - 1]
                if br.line != prev.line and self._is_destructure_assign():
                    return node
                tok = self.advance()
                # slice? d[1:3], d[:3], d[1:], d[:], d[::2]
                if self.at_op(":"):
                    mulai = None
                    self.advance()
                else:
                    mulai = self.expr()
                    if not self.at_op(":"):
                        self.expect_op("]")
                        node = Index(node, mulai, tok.line)
                        continue
                    self.advance()
                # di sini kita habis makan ':' pertama (atau mulai zonk)
                if self.at_op("]") or self.at_op(":"):
                    akhir = None
                else:
                    akhir = self.expr()
                if self.at_op(":"):
                    self.advance()
                    if self.at_op("]"):
                        langkah = None
                    else:
                        langkah = self.expr()
                else:
                    langkah = None
                self.expect_op("]")
                node = Slice(node, mulai, akhir, langkah, tok.line)
            elif self.at_op("?."):
                self.advance()
                t = self.peek()
                if t.kind != "IDENT":
                    raise self.err("habis '?.' harus nama atribut.")
                nama = self.advance().value
                nama = self._mangle_name(nama)
                node = Attr(node, nama, t.line, optional=True)
            elif self.at_op("."):
                self.advance()
                t = self.peek()
                if t.kind != "IDENT":
                    raise self.err("habis '.' harus nama atribut.")
                nama = self.advance().value
                # name mangling ala Python (tekstual): di dalam badan kelas,
                # semua akses obj._x / obj.__x / nama 'rahasia' diganti
                # _Kelas__x. Di luar kelas, nama itu nggak ada -> error jelas.
                nama = self._mangle_name(nama)
                node = Attr(node, nama, t.line)
            else:
                return node

    def primary(self):
        tok = self.peek()
        if tok.kind == "NUMBER":
            self.advance()
            return Literal(tok.value)
        if tok.kind == "STRING":
            self.advance()
            return self._string_node(tok)
        if tok.kind == "KEYWORD":
            if tok.value == "valid":
                self.advance()
                return Literal(True)
            if tok.value == "gimmick":
                self.advance()
                return Literal(False)
            if tok.value == "zonk":
                self.advance()
                return Literal(None)
            if tok.value == "ini":
                self.advance()
                return ThisExpr(tok.line)
            if tok.value == "ortu":
                self.advance()
                return SuperExpr(tok.line)
            raise self.err(f"'{tok.value}' nggak bisa dipakai sebagai nilai.")
        if tok.kind == "IDENT":
            self.advance()
            return Name(tok.value, tok.line)
        if tok.kind == "OP":
            if tok.value == "(":
                self.advance()
                node = self.expr()
                self.expect_op(")")
                return node
            if tok.value == "[":
                self.advance()
                elems = []
                if not self.at_op("]"):
                    pertama = self.expr()
                    if self.at_kw("buat"):
                        # comprehension: [expr buat x dalam iter kalo cond]
                        self.advance()
                        vt = self.peek()
                        if vt.kind != "IDENT":
                            raise self.err(
                                "habis 'buat' harus nama variabel, bestie.")
                        var = self.advance().value
                        if not self.at_kw("dalam"):
                            raise self.err(
                                "comprehension butuh 'dalam', bestie: "
                                "'[x buat x dalam daftar]'.")
                        self.advance()
                        iterable = self.coalesce_expr()
                        cond = None
                        if self.at_kw("kalo"):
                            self.advance()
                            cond = self.coalesce_expr()
                        self.expect_op("]")
                        return Comp(pertama, var, iterable, cond, tok.line)
                    elems.append(pertama)
                    while True:
                        if not self.at_op(","):
                            break
                        self.advance()
                        elems.append(self.expr())
                self.expect_op("]")
                return ListLit(elems)
            if tok.value == "{":
                # dalam konteks ekspresi, { } = kamus
                self.advance()
                pairs = []
                if not self.at_op("}"):
                    while True:
                        kt = self.peek()
                        if kt.kind == "STRING":
                            key = self.advance().value
                        elif kt.kind == "IDENT":
                            key = self.advance().value
                        else:
                            raise self.err("kunci kamus harus teks atau nama.")
                        self.expect_op(":")
                        pairs.append((key, self.expr()))
                        if self.at_op(","):
                            self.advance()
                            continue
                        break
                self.expect_op("}")
                return DictLit(pairs)
        raise self.err("ekspresi nggak valid di sini.")

    # -- string interpolation: "Halo, {nama}!" --
    def _string_node(self, tok):
        text = tok.value
        if "{" not in text and "}" not in text:
            return Literal(text)
        return self._interpolasi(text, tok)

    def _interpolasi(self, text, tok):
        parts = []
        buf = []
        i, n = 0, len(text)
        while i < n:
            c = text[i]
            if c == "{" and i + 1 < n and text[i + 1] == "{":
                buf.append("{")
                i += 2
                continue
            if c == "}" and i + 1 < n and text[i + 1] == "}":
                buf.append("}")
                i += 2
                continue
            if c == "{":
                # cari '}' penutup; sadar nesting & string di dalamnya
                j = i + 1
                depth = 1
                quote = None
                inner = []
                while j < n:
                    ch = text[j]
                    if quote:
                        inner.append(ch)
                        if ch == "\\" and j + 1 < n:
                            inner.append(text[j + 1])
                            j += 2
                            continue
                        if ch == quote:
                            quote = None
                        j += 1
                        continue
                    if ch in "\"'":
                        quote = ch
                        inner.append(ch)
                        j += 1
                        continue
                    if ch == "{":
                        depth += 1
                        inner.append(ch)
                        j += 1
                        continue
                    if ch == "}":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                        inner.append(ch)
                        j += 1
                        continue
                    inner.append(ch)
                    j += 1
                if depth != 0:
                    raise JakselSyntaxError(
                        "kurung kurawal '{' nggak ada pasangannya, bestie.", tok.line, tok.col)
                if buf:
                    parts.append(("teks", "".join(buf)))
                    buf = []
                expr_src = "".join(inner)
                sub = Parser(lex(expr_src, "<interpolasi>"))
                node = sub.expr()
                if sub.peek().kind != "EOF":
                    raise JakselSyntaxError(
                        "ekspresi di dalam {...} nggak valid, bestie.", tok.line, tok.col)
                parts.append(("ekspresi", node))
                i = j
                continue
            if c == "}":
                raise JakselSyntaxError(
                    "kurung kurawal '}' nggak punya pasangan, bestie.", tok.line, tok.col)
            buf.append(c)
            i += 1
        if buf:
            parts.append(("teks", "".join(buf)))
        if not any(k == "ekspresi" for k, _ in parts):
            # nggak ada interpolasi beneran: kembalikan teks polos
            # (escape {{ }} sudah diproses)
            return Literal("".join(t for k, t in parts))
        return InterpString(parts)


def parse(tokens):
    return Parser(tokens).parse()
