"""Lexer JakselScript: teks sumber -> daftar Token."""

KEYWORDS = {
    "bestie", "kalo", "plot_twist", "selain", "selama", "gamon", "stalk",
    "dalam", "ghosting", "skip", "talent", "balikin", "valid", "gimmick",
    "zonk", "nggak", "dan", "atau", "yolo", "yaudah", "akhirnya",
    "red_flag", "collab", "cabut", "kelas", "warisi", "ini", "ortu",
    "cocokkan", "buat", "ekspor",
}


class Token:
    __slots__ = ("kind", "value", "line", "col")

    def __init__(self, kind, value, line, col):
        self.kind = kind      # "NUMBER" | "STRING" | "IDENT" | "KEYWORD" | "OP" | "EOF"
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.kind}, {self.value!r}, {self.line}:{self.col})"


from .errors import JakselSyntaxError


ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}

TWO_CHAR_OPS = {"==", "!=", "<=", ">=", "=>", "??", "?."}
ONE_CHAR_OPS = set("+-*/%()=<>!{},[]:.")


def lex(source, filename="<repl>", keep_comments=False):
    """Ubah teks sumber jadi daftar Token.

    keep_comments=True: komentar // ikut jadi Token("COMMENT", teks, ...),
    dipakai formatter biar komentar nggak hilang.
    """
    tokens = []
    i, n = 0, len(source)
    line, col = 1, 1

    def advance(k=1):
        nonlocal i, line, col
        for _ in range(k):
            if i < n and source[i] == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1

    def err(msg):
        return JakselSyntaxError(msg, line, col)

    while i < n:
        c = source[i]

        # whitespace
        if c in " \t\r":
            advance()
            continue
        if c == "\n":
            advance()
            continue

        # komentar // sampai akhir baris
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            start_col = col
            j = i
            while j < n and source[j] != "\n":
                j += 1
            if keep_comments:
                tokens.append(Token("COMMENT", source[i:j], line, start_col))
            advance(j - i)
            continue

        # angka: 42, 3.14
        if c.isdigit():
            start_col = col
            j = i
            while j < n and source[j].isdigit():
                j += 1
            if j < n and source[j] == "." and j + 1 < n and source[j + 1].isdigit():
                j += 1
                while j < n and source[j].isdigit():
                    j += 1
                value = float(source[i:j])
            else:
                value = int(source[i:j])
            tokens.append(Token("NUMBER", value, line, start_col))
            advance(j - i)
            continue

        # string """...""" / '''...''' (multiline), "..." / '...',
        # dan raw string r"..." / r'...' (escape nggak diproses)
        raw = False
        if c == "r" and i + 1 < n and source[i + 1] in "\"'":
            raw = True
            advance()  # lewati 'r'
            c = source[i]
        if c in "\"'":
            quote = c
            start_col = col
            triple = source[i:i + 3] == quote * 3
            advance(3 if triple else 1)  # buka quote
            buf = []
            closed = False
            while i < n:
                if triple and source[i:i + 3] == quote * 3:
                    closed = True
                    advance(3)
                    break
                ch = source[i]
                if ch == "\\" and i + 1 < n and not raw:
                    nxt = source[i + 1]
                    buf.append(ESCAPES.get(nxt, nxt))
                    advance(2)
                    continue
                if not triple and ch == quote:
                    closed = True
                    advance()
                    break
                if not triple and ch == "\n":
                    break
                buf.append(ch)
                advance()
            if not closed:
                raise err("string nggak ditutup, bestie. Mana quote pasangannya?")
            tokens.append(Token("STRING", "".join(buf), line, start_col))
            continue

        # identifier / keyword
        if c.isalpha() or c == "_":
            start_col = col
            j = i
            while j < n and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            kind = "KEYWORD" if word in KEYWORDS else "IDENT"
            tokens.append(Token(kind, word, line, start_col))
            advance(j - i)
            continue

        # operator 3 karakter: ... (variadic / spread)
        if source[i:i + 3] == "...":
            tokens.append(Token("OP", "...", line, col))
            advance(3)
            continue

        # operator 2 karakter
        two = source[i:i + 2]
        if two in TWO_CHAR_OPS:
            tokens.append(Token("OP", two, line, col))
            advance(2)
            continue

        # operator 1 karakter
        if c in ONE_CHAR_OPS:
            # '!' sendirian itu gimmick (invalid)
            if c == "!":
                raise err("'!' jomblo nih, bestie. Maksudnya '!='?")
            tokens.append(Token("OP", c, line, col))
            advance()
            continue

        raise err(f"karakter '{c}' nggak dikenal. Typo ya?")

    tokens.append(Token("EOF", None, line, col))
    return tokens
