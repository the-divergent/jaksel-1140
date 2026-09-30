"""Formatter JakselScript: sumber berantakan -> rapi (indent 4 spasi).

Strategi: parse ke AST, cetak ulang dengan gaya baku, lalu tempel
komentar // berdasarkan nomor baris aslinya biar nggak hilang.
"""

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

INDENT = "    "

# presedens buat tanda kurung yang pas (makin gede makin kuat)
_PREC = {
    "??": 0,
    "atau": 1, "dan": 2,
    "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3, "dalam": 3,
    "+": 4, "-": 4,
    "*": 5, "/": 5, "%": 5,
}


def _quote(s):
    return '"%s"' % (s.replace("\\", "\\\\").replace('"', '\\"')
                      .replace("\n", "\\n").replace("\t", "\\t")
                      .replace("\r", "\\r"))


def _quote_literal(s):
    # string polos (Literal) selalu lewat proses interpolasi pas parsing,
    # jadi kurung kurawal harus digandakan biar balik jadi literal lagi.
    return _quote(s.replace("{", "{{").replace("}", "}}"))


class Formatter:
    def __init__(self, comments):
        # comments: list[(line, teks)] yang belum ditempel
        self.comments = sorted(comments)
        self.out = []
        self.level = 0
        self._last_line = 0  # baris stmt terakhir (buat baris kosong)
        self._baru_blok = False

    # -- util --
    def w(self, s):
        self.out.append(s)

    def nl(self):
        self.out.append("\n")

    def indent(self):
        self.out.append(INDENT * self.level)

    def stmt_line(self, node):
        line = getattr(node, "line", None)
        if line is not None:
            return line
        if isinstance(node, ExprStmt):
            return self.stmt_line(node.expr)
        return self._last_line

    def tempel_komentar(self, line):
        """Tempel komentar leading (baris < line) sebelum statement."""
        while self.comments and self.comments[0][0] < line:
            _, teks = self.comments.pop(0)
            self.indent()
            self.w(teks)
            self.nl()

    def komentar_trailing(self, line):
        while self.comments and self.comments[0][0] == line:
            _, teks = self.comments.pop(0)
            self.w("  " + teks)

    def statement(self, node):
        line = self.stmt_line(node)
        if (line > self._last_line + 1 and self._last_line
                and not self._baru_blok):
            self.nl()  # pertahankan satu baris kosong antar blok jauh
        self._baru_blok = False
        self._last_line = line
        self.tempel_komentar(line)
        self.indent()
        self.stmt(node)
        self.komentar_trailing(line)
        self.nl()

    def block(self, node):
        self.level += 1
        self._baru_blok = True
        for s in node.statements:
            self.statement(s)
        self.level -= 1

    # -- statements --
    def stmt(self, node):
        if isinstance(node, VarDecl):
            if isinstance(node.name, Destructure):
                target = self._pola_destructure(node.name)
            else:
                target = node.name
            self.w("bestie %s = %s" % (target, self.expr(node.value)))
        elif isinstance(node, Assign):
            self.w("%s = %s" % (self.expr(node.target), self.expr(node.value)))
        elif isinstance(node, IfStmt):
            self.w("kalo %s {" % self.expr(node.cond))
            self.nl()
            self.block(node.then_block)
            for cond, blk in node.elifs:
                self.indent()
                self.w("} plot_twist kalo %s {" % self.expr(cond))
                self.nl()
                self.block(blk)
            if node.else_block is not None:
                self.indent()
                self.w("} plot_twist {")
                self.nl()
                self.block(node.else_block)
            self.indent()
            self.w("}")
        elif isinstance(node, WhileStmt):
            if isinstance(node.cond, Literal) and node.cond.value is True:
                self.w("gamon {")
            else:
                self.w("selama %s {" % self.expr(node.cond))
            self.nl()
            self.block(node.body)
            self.indent()
            self.w("}")
        elif isinstance(node, ForStmt):
            if node.idx_var:
                self.w("stalk %s, %s dalam %s {" % (
                    node.idx_var, node.var, self.expr(node.iterable)))
            else:
                self.w("stalk %s dalam %s {" % (node.var,
                                                self.expr(node.iterable)))
            self.nl()
            self.block(node.body)
            self.indent()
            self.w("}")
        elif isinstance(node, FuncDef):
            params = []
            for p, d in node.params:
                if d is None:
                    params.append(p)
                else:
                    params.append("%s = %s" % (p, self.expr(d)))
            if node.variadic:
                params.append("...%s" % node.variadic)
            prefix = ""
            if getattr(node, "static", False):
                prefix = "statik "
            if getattr(node, "private", False):
                prefix = "rahasia " + prefix
            self.w("%stalent %s(%s) {" % (prefix, node.name, ", ".join(params)))
            self.nl()
            self.block(node.body)
            self.indent()
            self.w("}")
        elif isinstance(node, ClassDef):
            hdr = "kelas %s" % node.name
            if node.parent:
                hdr += " warisi %s" % node.parent
            self.w(hdr + " {")
            self.nl()
            self.level += 1
            self._baru_blok = True
            for m in node.methods:
                self.statement(m)
            self.level -= 1
            self.indent()
            self.w("}")
        elif isinstance(node, EnumDef):
            self.w("pilihan %s {" % node.name)
            self.nl()
            self.level += 1
            self._baru_blok = True
            for idx, (nama, nilai) in enumerate(node.members):
                self.indent()
                if nilai is None:
                    self.w(nama)
                else:
                    self.w("%s = %s" % (nama, self.expr(nilai)))
                # koma kecuali anggota terakhir
                if idx < len(node.members) - 1:
                    self.w(",")
                self.nl()
            self.level -= 1
            self.indent()
            self.w("}")
        elif isinstance(node, PropertyDef):
            self.w("properti %s {" % node.name)
            self.nl()
            self.level += 1
            self._baru_blok = True
            if node.getter_body is not None:
                self.indent()
                self.w("ambil {")
                self.nl()
                self.block(node.getter_body)
                self.indent()
                self.w("}")
                self.nl()
            if node.setter_body is not None:
                self.indent()
                self.w("taruh(%s) {" % node.setter_param)
                self.nl()
                self.block(node.setter_body)
                self.indent()
                self.w("}")
                self.nl()
            self.level -= 1
            self.indent()
            self.w("}")
        elif isinstance(node, MatchStmt):
            self.w("cocokkan %s {" % self.expr(node.subject))
            self.nl()
            self.level += 1
            self._baru_blok = True
            for pola, guard, blk in node.arms:
                self.indent()
                self.w("%s%s => {" % (self._pola_match(pola),
                                      " kalo %s" % self.expr(guard)
                                      if guard else ""))
                self.nl()
                self.block(blk)
                self.indent()
                self.w("},")
                self.nl()
            self.level -= 1
            self.indent()
            self.w("}")
        elif isinstance(node, ReturnStmt):
            if isinstance(node.value, Literal) and node.value.value is None:
                self.w("balikin")
            else:
                self.w("balikin %s" % self.expr(node.value))
        elif isinstance(node, BreakStmt):
            self.w("ghosting")
        elif isinstance(node, ContinueStmt):
            self.w("skip")
        elif isinstance(node, TryStmt):
            self.w("yolo {")
            self.nl()
            self.block(node.body)
            self.indent()
            catch = "} yaudah"
            if node.catch_class:
                catch += " %s" % node.catch_class
            if node.catch_var:
                catch += " %s" % node.catch_var
            catch += " {"
            self.w(catch)
            self.nl()
            self.block(node.catch_body)
            if node.finally_body is not None:
                self.indent()
                self.w("} akhirnya {")
                self.nl()
                self.block(node.finally_body)
            self.indent()
            self.w("}")
        elif isinstance(node, ThrowStmt):
            self.w("red_flag %s" % self.expr(node.value))
        elif isinstance(node, ExitStmt):
            if isinstance(node.code, Literal) and node.code.value == 0:
                self.w("cabut")
            else:
                self.w("cabut %s" % self.expr(node.code))
        elif isinstance(node, ImportStmt):
            if node.py_module:
                s = "collab python %s" % _quote(node.py_module)
            else:
                s = "collab %s" % _quote(node.path)
            if node.alias:
                s += " sebagai %s" % node.alias
            if node.ambil:
                s += " ambil %s" % ", ".join(node.ambil)
            self.w(s)
        elif isinstance(node, ExportStmt):
            self.w("ekspor %s" % ", ".join(node.names))
        elif isinstance(node, ExprStmt):
            self.w(self.expr(node.expr))
        else:
            raise ValueError("node nggak dikenal: %r" % node)

    def _pola_destructure(self, pola):
        # pola: Destructure(kind, items) — kind "list": items=[nama,...];
        # kind "dict": items=[(kunci, nama_var), ...]
        if pola.kind == "list":
            return "[%s]" % ", ".join(pola.items)
        return "{%s}" % ", ".join(
            "%s: %s" % (k, v) if k != v else k for k, v in pola.items)

    def _pola_match(self, pola):
        if isinstance(pola, PatWild):
            return "_"
        if isinstance(pola, PatLit):
            return self.expr(Literal(pola.value))
        if isinstance(pola, PatBind):
            if pola.rest:
                return "...%s" % pola.name
            return pola.name
        if isinstance(pola, PatType):
            return pola.name
        if isinstance(pola, PatEnum):
            return "%s.%s" % (pola.enum_name, pola.member_name)
        if isinstance(pola, PatList):
            return "[%s]" % ", ".join(self._pola_match(p) for p in pola.items)
        if isinstance(pola, PatDict):
            return "{%s}" % ", ".join(
                "%s: %s" % (_quote(k), self._pola_match(p))
                for k, p in pola.items)
        return "_"

    # -- expressions --
    def expr(self, node, parent_prec=0):
        if isinstance(node, Literal):
            v = node.value
            if v is True:
                return "valid"
            if v is False:
                return "gimmick"
            if v is None:
                return "zonk"
            if isinstance(v, str):
                return _quote_literal(v)
            return repr(v)
        if isinstance(node, Name):
            return node.id
        if isinstance(node, ThisExpr):
            return "ini"
        if isinstance(node, SuperExpr):
            return "ortu"
        if isinstance(node, BinOp):
            prec = _PREC[node.op]
            l = self.expr(node.left, prec)
            r = self.expr(node.right, prec + 1)
            s = "%s %s %s" % (l, node.op, r)
            return "(%s)" % s if prec < parent_prec else s
        if isinstance(node, UnaryOp):
            return "-%s" % self.expr(node.operand, 6)
        if isinstance(node, NotOp):
            return "nggak %s" % self.expr(node.operand, 6)
        if isinstance(node, Call):
            args = []
            for a in node.args:
                if isinstance(a, Spread):
                    args.append("...%s" % self.expr(a.value))
                else:
                    args.append(self.expr(a))
            for nama, val in node.kwargs:
                args.append("%s = %s" % (nama, self.expr(val)))
            return "%s(%s)" % (self.expr(node.func, 7), ", ".join(args))
        if isinstance(node, Index):
            return "%s[%s]" % (self.expr(node.obj, 7), self.expr(node.index))
        if isinstance(node, Slice):
            def _s(v):
                return self.expr(v) if v is not None else ""
            dalam = "%s:%s" % (_s(node.mulai), _s(node.akhir))
            if node.langkah is not None:
                dalam += ":%s" % _s(node.langkah)
            return "%s[%s]" % (self.expr(node.obj, 7), dalam)
        if isinstance(node, IfExpr):
            return "%s kalo %s selain %s" % (
                self.expr(node.then), self.expr(node.cond),
                self.expr(node.else_))
        if isinstance(node, Comp):
            s = "[%s buat %s dalam %s" % (
                self.expr(node.expr), node.var, self.expr(node.iterable))
            if node.cond is not None:
                s += " kalo %s" % self.expr(node.cond)
            return s + "]"
        if isinstance(node, ChainComp):
            s = self.expr(node.first)
            for op, e in zip(node.ops, node.operands):
                s += " %s %s" % (op, self.expr(e))
            return s
        if isinstance(node, Attr):
            sep = "?." if node.optional else "."
            return "%s%s%s" % (self.expr(node.obj, 7), sep, node.name)
        if isinstance(node, ListLit):
            return "[%s]" % ", ".join(self.expr(e) for e in node.elements)
        if isinstance(node, DictLit):
            return "{%s}" % ", ".join(
                "%s: %s" % (_quote(k), self.expr(v)) for k, v in node.pairs)
        if isinstance(node, InterpString):
            buf = []
            for kind, part in node.parts:
                if kind == "teks":
                    buf.append(part.replace("{", "{{").replace("}", "}}"))
                else:
                    buf.append("{%s}" % self.expr(part))
            return _quote("".join(buf))
        raise ValueError("ekspresi nggak dikenal: %r" % node)

    def sisa_komentar(self):
        while self.comments:
            _, teks = self.comments.pop(0)
            self.indent()
            self.w(teks)
            self.nl()

    def run(self, program):
        for s in program.statements:
            self.statement(s)
        self.sisa_komentar()
        return "".join(self.out).rstrip("\n") + "\n"


def format_source(source, filename="<rapi>"):
    """Format kode sumber JakselScript. Raise JakselSyntaxError kalau rusak."""
    toks = lex(source, filename, keep_comments=True)
    comments = [(t.line, t.value) for t in toks if t.kind == "COMMENT"]
    program = parse(lex(source, filename))
    return Formatter(comments).run(program)
