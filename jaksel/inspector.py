"""Inspector JakselScript: intip token & AST (jaksel urai)."""

from .lexer import lex
from .parser import Node, parse


def dump_tokens(source, filename="<urai>"):
    toks = [t for t in lex(source, filename) if t.kind != "EOF"]
    lines = []
    for t in toks:
        lines.append("%d:%d  %-7s %r" % (t.line, t.col, t.kind, t.value))
    lines.append("(total %d token)" % len(toks))
    return "\n".join(lines)


def _ringkas(v):
    if isinstance(v, Node):
        return None
    if isinstance(v, str):
        return repr(v)
    if isinstance(v, (list, tuple)):
        return "[%d item]" % len(v)
    return repr(v)


def _punya_node(v):
    if isinstance(v, Node):
        return True
    if isinstance(v, (list, tuple)):
        return any(_punya_node(x) for x in v)
    return False


def _jalan_anak(v, depth, lines, jalan):
    if isinstance(v, Node):
        jalan(v, depth)
    elif isinstance(v, (list, tuple)):
        for x in v:
            _jalan_anak(x, depth, lines, jalan)


def dump_ast(program):
    lines = []

    def jalan(node, depth):
        pad = "  " * depth
        if not isinstance(node, Node):
            lines.append("%s%r" % (pad, node))
            return
        nama = type(node).__name__
        info, anak = [], []
        for k, v in vars(node).items():
            if k == "line":
                continue
            (anak if _punya_node(v) else info).append((k, v))
        baris = getattr(node, "line", None)
        lines.append("%s%s%s%s" % (
            pad, nama,
            (" " + " ".join("%s=%s" % (k, _ringkas(v))
                            for k, v in info)) if info else "",
            ("  (baris %s)" % baris) if baris else ""))
        for k, v in anak:
            lines.append("%s%s:" % (pad + "  ", k))
            _jalan_anak(v, depth + 2, lines, jalan)

    jalan(program, 0)
    return "\n".join(lines)


def urai(source, filename="<urai>", mode="semua"):
    bagian = []
    if mode in ("semua", "token"):
        bagian.append("=== TOKEN ===")
        bagian.append(dump_tokens(source, filename))
    if mode in ("semua", "ast"):
        if bagian:
            bagian.append("")
        bagian.append("=== AST ===")
        bagian.append(dump_ast(parse(lex(source, filename))))
    return "\n".join(bagian)
