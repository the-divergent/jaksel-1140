"""Pretty error rendering untuk JakselScript.

Setiap error (sintaks maupun runtime) ditampilkan ala compiler modern:
baris kode sumber + tanda caret (^) tepat di posisi error, dengan
penjelasan tetap bergaya Jaksel.
"""


def render(source, message, line=None, col=None, trace=None):
    """Format pesan error + snippet kode sumber.

    Args:
        source: teks sumber program (boleh None).
        message: pesan error (sudah termasuk prefix gaya Jaksel).
        line: nomor baris (1-based), boleh None.
        col: nomor kolom (1-based), boleh None.
        trace: list[(nama_fungsi, line)] jejak tumpukan, paling baru terakhir.
    """
    out = message
    if source and line:
        lines = source.splitlines()
        if 1 <= line <= len(lines):
            code = lines[line - 1]
            gutter = f"{line} | "
            out += f"\n  {gutter}{code}"
            if col and 1 <= col <= len(code) + 1:
                out += "\n  " + " " * len(gutter) + " " * (col - 1) + "^"
    if trace:
        out += "\n  Jejak tumpukan (yang paling bawah paling duluan dipanggil):"
        for nama, tline in trace:
            loc = f"baris {tline}" if tline else "baris ?"
            out += f"\n    -> di talent '{nama}' ({loc})"
    return out


class JakselSyntaxError(Exception):
    """Error tahap lexing/parsing."""

    def __init__(self, message, line=None, col=None):
        self.raw = message
        self.line = line
        self.col = col
        super().__init__(message)

    def __str__(self):
        loc = f" (baris {self.line}" + (f", kolom {self.col}" if self.col else "") + ")" if self.line else ""
        return f"Gimmick nih sintaksnya{loc}: {self.raw}"

    def pretty(self, source):
        return render(source, str(self), self.line, self.col)


class JakselError(Exception):
    """Error tahap runtime (interpreter)."""

    def __init__(self, message, line=None):
        self.raw = message
        self.line = line
        self.trace = None  # diisi interpreter: [(nama_fungsi, line), ...]
        super().__init__(message)

    def __str__(self):
        loc = f"baris {self.line}: " if self.line else ""
        return f"Red flag {loc}{self.raw}"

    def pretty(self, source):
        return render(source, str(self), self.line, None, self.trace)
