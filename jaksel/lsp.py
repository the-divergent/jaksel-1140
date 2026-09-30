"""LSP server JakselScript (JSON-RPC via stdio, tanpa dependensi).

Dijalankan:  jaksel lsp
Mendukung: initialize, textDocument/didOpen, textDocument/didChange,
textDocument/hover, textDocument/completion, shutdown/exit.
Diagnostics: error sintaks ala 'jaksel cek', real-time.
"""

import json
import re
import sys

from .errors import JakselSyntaxError
from .lexer import lex
from .parser import (
    Assign, ClassDef, EnumDef, FuncDef, Name, VarDecl, parse,
)

# ---------------- dokumentasi hover ----------------

_DOC_KEYWORD = {
    "spill": "spill(teks, ...) — cetak ke layar, bestie.",
    "kepo": 'kepo(prompt?) — baca input dari user. Contoh: bestie nama = kepo("nama? ")',
    "bestie": "bestie nama = nilai — deklarasi variabel baru.",
    "kalo": "kalo kondisi { ... } — percabangan.",
    "plot_twist": "plot_twist { ... } / plot_twist kalo ... — else / else-if.",
    "selama": "selama kondisi { ... } — perulangan while.",
    "gamon": "gamon { ... } — loop selamanya (pakai ghosting buat kabur).",
    "stalk": "stalk x dalam daftar { ... } — perulangan for-each.",
    "dalam": "dalam — dipakai bareng stalk: stalk x dalam daftar.",
    "ghosting": "ghosting — break: kabur dari loop.",
    "skip": "skip — continue: lewati satu putaran loop.",
    "talent": "talent nama(p1, p2) { ... } — definisi fungsi.",
    "balikin": "balikin nilai — return dari talent.",
    "valid": "valid — nilai benar (true).",
    "gimmick": "gimmick — nilai salah (false).",
    "zonk": "zonk — nilai kosong (null).",
    "nggak": "nggak x — negasi (not).",
    "dan": "a dan b — logika AND.",
    "atau": "a atau b — logika OR.",
    "yolo": "yolo { ... } yaudah e { ... } akhirnya { ... } — try/catch/finally.",
    "yaudah": "yaudah e { ... } — blok catch, e = pesan error.",
    "akhirnya": "akhirnya { ... } — blok finally: selalu jalan.",
    "red_flag": "red_flag pesan — lempar error.",
    "collab": 'collab "utils" — import file .jaksel lain (relatif / std / paket).',
    "healing": "healing(detik) — jeda tidur.",
    "cabut": "cabut(kode?) — keluar program.",
    "kelas": "kelas Nama { ... } — definisi kelas.",
    "warisi": "kelas Anak warisi Induk { ... } — pewarisan.",
    "lahir": 'talent lahir(...) { ... } — constructor kelas (dipanggil pas "new").',
    "ini": "ini.atribut — akses atribut objek dari dalam method.",
    "ortu": "ortu.metode(...) — panggil method kelas induk.",
}

_DOC_BUILTIN = {
    "panjang": "panjang(daftar/teks) — jumlah elemen / karakter.",
    "angka": 'angka(teks) — teks jadi angka. Contoh: angka("42")',
    "teks": "teks(nilai) — nilai jadi teks.",
    "rentang": "rentang(awal?, akhir, langkah?) — daftar angka. Contoh: rentang(5)",
    "acak": "acak(daftar) — ambil elemen acak. / acak(awal, akhir) — angka acak.",
    "waktu": "waktu() — detik sejak epoch (float).",
    "tanggal": 'tanggal(format?) — tanggal sekarang. Contoh: tanggal("%d/%m/%Y")',
    "petakan": "petakan(daftar, talent) — map: ubah tiap elemen.",
    "saring": "saring(daftar, talent) — filter: ambil yang lolos tes.",
    "kumpulkan": "kumpulkan(daftar, talent, awal) — reduce: lipat jadi satu nilai.",
    "baca_file": 'baca_file(path) — baca isi file jadi teks.',
    "tulis_file": "tulis_file(path, teks) — tulis (timpa) file.",
    "tambah_file": "tambah_file(path, teks) — tambah teks ke akhir file.",
    "args": "args() — daftar argumen CLI setelah nama file.",
    "env": 'env(nama, default?) — baca environment variable.',
    "tipe": "tipe(x) — nama tipe nilai: angka/teks/daftar/kamus/fungsi/...",
    "klaim": 'klaim(kondisi, pesan?) — assert: lempar red flag kalau gimmick.',
    "jalankan": 'jalankan(perintah) — eksekusi shell, hasil {kode, keluar, galat}.',
    "json_urai": 'json_urai(teks) — teks JSON jadi nilai.',
    "json_tulis": "json_tulis(nilai, cantik?) — nilai jadi teks JSON.",
    "http_get": 'http_get(url) — GET, hasilnya teks.',
    "http_get_json": 'http_get_json(url) — GET lalu otomatis json_urai.',
    "http_post": 'http_post(url, data?) — POST form/teks, hasilnya teks.',
    "cocok": 'cocok(teks, pola) — cek regex, hasil valid/gimmick.',
    "cari": 'cari(teks, pola) — hasil regex pertama (zonk kalau nggak ada).',
    "cari_semua": 'cari_semua(teks, pola) — semua hasil regex.',
    "ganti_regex": 'ganti_regex(teks, pola, ganti) — ganti pakai regex.',
    "csv_baca": 'csv_baca(path) — baca CSV jadi daftar baris.',
    "csv_tulis": 'csv_tulis(path, data) — tulis daftar baris jadi CSV.',
    "ada_file": 'ada_file(path) — cek file/folder ada, hasil valid/gimmick.',
    "daftar_file": 'daftar_file(folder?) — daftar isi folder.',
    "buat_folder": 'buat_folder(path) — bikin folder (rekursif).',
    "hapus_file": 'hapus_file(path) — hapus file.',
    "total": "total(daftar) — jumlah semua angka.",
    "terbesar": "terbesar(daftar) — nilai maksimum.",
    "terkecil": "terkecil(daftar) — nilai minimum.",
    "rerata": "rerata(daftar) — rata-rata.",
    "urut_dengan": "urut_dengan(daftar, talent) — urut pakai fungsi kunci.",
    "pasangkan": "pasangkan(a, b) — zip dua daftar jadi pasangan.",
}

_DOC_METHOD = {
    "tambah": "daftar.tambah(x) — tambah elemen ke akhir.",
    "buang": "daftar.buang(i?) — buang & kembalikan elemen (default terakhir).",
    "sisipkan": "daftar.sisipkan(i, x) — selipkan elemen di posisi i.",
    "urut": "daftar.urut() — urutkan di tempat.",
    "balik": "daftar.balik() — balik urutan di tempat.",
    "gabung": 'daftar.gabung(pemisah) — gabung jadi teks. Contoh: d.gabung(", ")',
    "salin": "daftar.salin() — salinan daftar (biar aslinya aman).",
    "besar": 'teks.besar() — jadi HURUF KAPITAL.',
    "kecil": "teks.kecil() — jadi huruf kecil.",
    "potong": "teks.potong() — buang spasi di ujung-ujung.",
    "ganti": 'teks.ganti(lama, baru) — ganti semua kemunculan.',
    "pisah": 'teks.pisah(pemisah?) — pecah jadi daftar.',
    "mulai_dengan": 'teks.mulai_dengan(awalan) — cek awalan, hasil valid/gimmick.',
    "berakhir_dengan": 'teks.berakhir_dengan(akhiran) — cek akhiran.',
    "kunci": "kamus.kunci() — daftar semua kunci.",
    "nilai": "kamus.nilai() — daftar semua nilai.",
    "ambil": 'kamus.ambil(kunci, default?) — ambil aman, zonk kalau nggak ada.',
    "hapus": "kamus.hapus(kunci) — hapus & kembalikan nilainya.",
}

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DECL = re.compile(r"\b(?:bestie|talent|kelas)\s+([A-Za-z_][A-Za-z0-9_]*)")


def _diagnostik(uri, source):
    """Daftar diagnostic LSP dari hasil parse. Kosong = aman."""
    try:
        parse(lex(source, uri))
        return []
    except JakselSyntaxError as e:
        baris = max(0, (e.line or 1) - 1)
        kolom = max(0, (e.col or 1) - 1)
        return [{
            "range": {
                "start": {"line": baris, "character": kolom},
                "end": {"line": baris, "character": kolom + 1},
            },
            "severity": 1,  # Error
            "source": "jakselscript",
            "message": e.raw,
        }]
    except Exception as e:  # jangan matikan server gara-gara ini
        return [{
            "range": {"start": {"line": 0, "character": 0},
                      "end": {"line": 0, "character": 1}},
            "severity": 1, "source": "jakselscript",
            "message": "Red flag: %s" % e,
        }]


def _kata_di(baris_teks, kolom):
    for m in _WORD.finditer(baris_teks):
        if m.start() <= kolom <= m.end():
            titik = m.start() > 0 and baris_teks[m.start() - 1] == "."
            return m.group(0), titik
    return None, False


# ---------------- simbol: definition / references / rename ----------------

def _bangun_simbol(source):
    # Tabel simbol: nama -> [(line0, col0, col1, kind)]
    # kind: 'def' atau 'ref'. Baris/kolom 0-based.
    try:
        program = parse(lex(source, "<lsp>"))
    except Exception:
        return {}
    simbol = {}
    baris_list = source.split("\n")

    def catat(nama, line, kind):
        if not isinstance(nama, str) or not nama:
            return
        l0 = line - 1
        if not 0 <= l0 < len(baris_list):
            return
        teks = baris_list[l0]
        for m in re.finditer(r"\b%s\b" % re.escape(nama), teks):
            simbol.setdefault(nama, []).append(
                (l0, m.start(), m.end(), kind))
            break

    def jalan_block(stmts):
        for s in stmts:
            jalan_stmt(s)

    def jalan_stmt(s):
        if isinstance(s, VarDecl):
            if isinstance(s.name, str):
                catat(s.name, s.line, "def")
            if s.value is not None:
                jalan_expr(s.value)
        elif isinstance(s, Assign):
            jalan_expr(s.target)
            jalan_expr(s.value)
        elif isinstance(s, FuncDef):
            catat(s.name, s.line, "def")
            for _, d in s.params:
                if d is not None:
                    jalan_expr(d)
            jalan_block(s.body.statements)
        elif isinstance(s, ClassDef):
            catat(s.name, s.line, "def")
            for m in s.methods:
                jalan_stmt(m)
        elif isinstance(s, EnumDef):
            catat(s.name, s.line, "def")
        else:
            for v in vars(s).values():
                _jalan_anak(v)

    def _jalan_anak(v):
        if isinstance(v, list):
            for x in v:
                if hasattr(x, "line"):
                    if hasattr(x, "statements"):
                        jalan_block(x.statements)
                    else:
                        jalan_expr(x)
        elif hasattr(v, "line") and not isinstance(
                v, (str, int, float, bool)):
            jalan_expr(v)

    def jalan_expr(e):
        if e is None or not hasattr(e, "line"):
            return
        if isinstance(e, Name):
            l0 = e.line - 1
            if 0 <= l0 < len(baris_list):
                teks = baris_list[l0]
                for m in re.finditer(r"\b%s\b" % re.escape(e.id), teks):
                    udah = any(l == l0 and c0 == m.start()
                               for l, c0, c1, k in simbol.get(e.id, [])
                               if k == "def")
                    if not udah:
                        simbol.setdefault(e.id, []).append(
                            (l0, m.start(), m.end(), "ref"))
                    break
            return
        for v in vars(e).values():
            _jalan_anak(v)

    jalan_block(program.statements)
    return simbol


def _signature_help(uri, source, line, col):
    """textDocument/signatureHelp: info parameter fungsi di posisi kursor."""
    baris_list = source.split("\n")
    if not 0 <= line < len(baris_list):
        return None
    # cari '(' yang belum ditutup sebelum kursor (mundur dari kursor)
    teks_sebelum = "\n".join(baris_list[:line]) + "\n" + baris_list[line][:col]
    depth = 0
    pos_buka = -1
    i = len(teks_sebelum) - 1
    dalam_string = None
    while i >= 0:
        c = teks_sebelum[i]
        if dalam_string:
            if c == dalam_string and teks_sebelum[i - 1:i] != "\\":
                dalam_string = None
        elif c in ("\"", "'"):
            dalam_string = c
        elif c == ")":
            depth += 1
        elif c == "(":
            if depth == 0:
                pos_buka = i
                break
            depth -= 1
        i -= 1
    if pos_buka < 0:
        return None
    # nama fungsi sebelum '('
    j = pos_buka - 1
    while j >= 0 and teks_sebelum[j] in " \t\n":
        j -= 1
    akhir_nama = j + 1
    while j >= 0 and (teks_sebelum[j].isalnum() or teks_sebelum[j] == "_"):
        j -= 1
    nama = teks_sebelum[j + 1:akhir_nama]
    if "." in nama:
        nama = nama.split(".")[-1]
    if not nama:
        return None
    # hitung parameter aktif (koma di depth 0 dari '(' sampai kursor)
    aktif = 0
    d = 0
    ds = None
    k = pos_buka + 1
    while k < len(teks_sebelum):
        c = teks_sebelum[k]
        if ds:
            if c == ds and teks_sebelum[k - 1:k] != "\\":
                ds = None
        elif c in ("\"", "'"):
            ds = c
        elif c == "(":
            d += 1
        elif c == ")":
            d -= 1
        elif c == "," and d == 0:
            aktif += 1
        k += 1
    # cari definisi fungsi: coba AST dulu, fallback ke regex
    # (source bisa nggak lengkap pas user lagi ngetik)
    params = None
    try:
        program = parse(lex(source, "<lsp>"))

        def cari(stmts):
            for s in stmts:
                if isinstance(s, FuncDef) and s.name == nama:
                    return s
                if isinstance(s, ClassDef):
                    for m in s.methods:
                        if isinstance(m, FuncDef) and m.name == nama:
                            return m
                for v in vars(s).values():
                    if hasattr(v, "statements"):
                        r = cari(v.statements)
                        if r:
                            return r
                    elif isinstance(v, list):
                        for x in v:
                            if hasattr(x, "statements"):
                                r = cari(x.statements)
                                if r:
                                    return r
            return None

        target = cari(program.statements)
        if target is not None:
            params = []
            for pname, default in target.params:
                params.append(pname if default is None else "%s = ..." % pname)
    except Exception:
        pass
    if params is None:
        # fallback regex: talent nama(p1, p2 = default)
        m = re.search(
            r"\btalent\s+%s\s*\(([^)]*)\)" % re.escape(nama), source)
        if not m:
            return None
        params = []
        for p in m.group(1).split(","):
            p = p.strip()
            if not p:
                continue
            pname = p.split("=")[0].strip()
            params.append(p if "=" not in p else "%s = ..." % pname)
    label = "%s(%s)" % (nama, ", ".join(params))
    return {
        "signatures": [{
            "label": label,
            "parameters": [{"label": p} for p in params],
            "documentation": "talent %s — fungsi JakselScript." % nama,
        }],
        "activeSignature": 0,
        "activeParameter": min(aktif, max(len(params) - 1, 0)),
    }


def _document_symbol(uri, source):
    """textDocument/documentSymbol: daftar fungsi/kelas/variabel."""
    try:
        program = parse(lex(source, "<lsp>"))
    except Exception:
        return None
    baris_list = source.split("\n")
    hasil = []

    def rentang(line):
        # baris 1-based -> range 0-based; kolom 0 s/d panjang baris
        l0 = max(line - 1, 0)
        akhir = len(baris_list[l0]) if l0 < len(baris_list) else 0
        return {
            "start": {"line": l0, "character": 0},
            "end": {"line": l0, "character": akhir},
        }

    def seleksi(nama, line):
        l0 = max(line - 1, 0)
        teks = baris_list[l0] if l0 < len(baris_list) else ""
        m = re.search(r"\b%s\b" % re.escape(nama), teks)
        c0 = m.start() if m else 0
        return {
            "start": {"line": l0, "character": c0},
            "end": {"line": l0, "character": c0 + len(nama)},
        }

    def jalan(stmts, wadah):
        for s in stmts:
            if isinstance(s, FuncDef):
                anak = []
                jalan(s.body.statements, anak)
                wadah.append({
                    "name": s.name,
                    "kind": 12,  # Function
                    "range": rentang(s.line),
                    "selectionRange": seleksi(s.name, s.line),
                    "children": anak,
                })
            elif isinstance(s, ClassDef):
                anak = []
                for m in s.methods:
                    jalan([m], anak)
                wadah.append({
                    "name": s.name,
                    "kind": 5,  # Class
                    "range": rentang(s.line),
                    "selectionRange": seleksi(s.name, s.line),
                    "children": anak,
                })
            elif isinstance(s, EnumDef):
                wadah.append({
                    "name": s.name,
                    "kind": 10,  # Enum
                    "range": rentang(s.line),
                    "selectionRange": seleksi(s.name, s.line),
                })
            elif isinstance(s, VarDecl) and isinstance(s.name, str):
                wadah.append({
                    "name": s.name,
                    "kind": 13,  # Variable
                    "range": rentang(s.line),
                    "selectionRange": seleksi(s.name, s.line),
                })
            else:
                for v in vars(s).values():
                    if hasattr(v, "statements"):
                        jalan(v.statements, wadah)

    jalan(program.statements, hasil)
    return hasil


def _definition(uri, source, line, col):
    baris = source.split("\n")
    if not 0 <= line < len(baris):
        return None
    kata, _ = _kata_di(baris[line], col)
    if not kata:
        return None
    entri = _bangun_simbol(source).get(kata, [])
    defs = [e for e in entri if e[3] == "def"]
    if not defs:
        return None
    l0, c0, c1, _ = defs[0]
    return {"uri": uri, "range": {
        "start": {"line": l0, "character": c0},
        "end": {"line": l0, "character": c1}}}


def _references(uri, source, line, col):
    baris = source.split("\n")
    if not 0 <= line < len(baris):
        return None
    kata, _ = _kata_di(baris[line], col)
    if not kata:
        return None
    entri = _bangun_simbol(source).get(kata, [])
    if not entri:
        return None
    return [{"uri": uri, "range": {
        "start": {"line": l0, "character": c0},
        "end": {"line": l0, "character": c1}}}
        for l0, c0, c1, _ in entri]


def _rename(uri, source, line, col, nama_baru):
    refs = _references(uri, source, line, col)
    if not refs:
        return None
    edits = [{"range": r["range"], "newText": nama_baru} for r in refs]
    return {"changes": {uri: edits}}


def _baca_pesan():
    """Baca satu pesan LSP dari stdin. Return dict atau None (EOF)."""
    panjang = None
    while True:
        raw = sys.stdin.buffer.readline()
        if not raw:
            return None
        baris = raw.decode("utf-8").strip()
        if baris == "":
            if panjang is not None:
                break
            continue
        if baris.lower().startswith("content-length:"):
            panjang = int(baris.split(":", 1)[1].strip())
    if panjang is None:
        return None
    badan = sys.stdin.buffer.read(panjang)
    return json.loads(badan.decode("utf-8"))


def _kirim(obj):
    badan = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(
        ("Content-Length: %d\r\n\r\n" % len(badan)).encode("ascii"))
    sys.stdout.buffer.write(badan)
    sys.stdout.buffer.flush()


def _balas(req_id, hasil):
    _kirim({"jsonrpc": "2.0", "id": req_id, "result": hasil})


def _notif(metode, params):
    _kirim({"jsonrpc": "2.0", "method": metode, "params": params})


class Server:
    def __init__(self):
        self.dokumen = {}  # uri -> source
        self._shutdown = False

    def publish(self, uri):
        _notif("textDocument/publishDiagnostics", {
            "uri": uri,
            "diagnostics": _diagnostik(uri, self.dokumen.get(uri, "")),
        })

    def layani(self, msg):
        metode = msg.get("method", "")
        req_id = msg.get("id")
        params = msg.get("params", {}) or {}

        if metode == "initialize":
            _balas(req_id, {
                "capabilities": {
                    "textDocumentSync": 1,
                    "hoverProvider": True,
                    "completionProvider": {"triggerCharacters": ["."]},
                    "signatureHelpProvider": {"triggerCharacters": ["(", ","]},
                    "documentSymbolProvider": True,
                    "definitionProvider": True,
                    "referencesProvider": True,
                    "renameProvider": True,
                },
                "serverInfo": {"name": "jakselscript-lsp", "version": "0.6.0"},
            })
        elif metode == "initialized":
            pass
        elif metode == "textDocument/didOpen":
            doc = params["textDocument"]
            self.dokumen[doc["uri"]] = doc["text"]
            self.publish(doc["uri"])
        elif metode == "textDocument/didChange":
            uri = params["textDocument"]["uri"]
            for ch in params.get("contentChanges", []):
                self.dokumen[uri] = ch["text"]
            self.publish(uri)
        elif metode == "textDocument/didClose":
            self.dokumen.pop(params["textDocument"]["uri"], None)
        elif metode == "textDocument/hover":
            pos = params["position"]
            hasil = _hover(params["textDocument"]["uri"],
                           self.dokumen.get(params["textDocument"]["uri"], ""),
                           pos["line"], pos["character"])
            _balas(req_id, hasil)
        elif metode == "textDocument/completion":
            pos = params["position"]
            hasil = _completion(params["textDocument"]["uri"],
                                self.dokumen.get(
                                    params["textDocument"]["uri"], ""),
                                pos["line"], pos["character"])
            _balas(req_id, {"isIncomplete": False, "items": hasil})
        elif metode == "textDocument/definition":
            pos = params["position"]
            hasil = _definition(params["textDocument"]["uri"],
                                self.dokumen.get(
                                    params["textDocument"]["uri"], ""),
                                pos["line"], pos["character"])
            _balas(req_id, hasil)
        elif metode == "textDocument/references":
            pos = params["position"]
            hasil = _references(params["textDocument"]["uri"],
                                self.dokumen.get(
                                    params["textDocument"]["uri"], ""),
                                pos["line"], pos["character"])
            _balas(req_id, hasil)
        elif metode == "textDocument/rename":
            pos = params["position"]
            hasil = _rename(params["textDocument"]["uri"],
                            self.dokumen.get(
                                params["textDocument"]["uri"], ""),
                            pos["line"], pos["character"],
                            params.get("newName", ""))
            _balas(req_id, hasil)
        elif metode == "textDocument/signatureHelp":
            pos = params["position"]
            hasil = _signature_help(params["textDocument"]["uri"],
                                    self.dokumen.get(
                                        params["textDocument"]["uri"], ""),
                                    pos["line"], pos["character"])
            _balas(req_id, hasil)
        elif metode == "textDocument/documentSymbol":
            hasil = _document_symbol(params["textDocument"]["uri"],
                                     self.dokumen.get(
                                         params["textDocument"]["uri"], ""))
            _balas(req_id, hasil)
        elif metode == "shutdown":
            self._shutdown = True
            _balas(req_id, None)
        elif metode == "exit":
            sys.exit(0)
        elif metode.startswith("$/") or metode.startswith("workspace/"):
            if req_id is not None:
                _balas(req_id, None)
        elif req_id is not None:
            _kirim({"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601,
                              "message": "metode '%s' belum didukung, bestie."
                              % metode}})

    def jalan(self):
        while True:
            msg = _baca_pesan()
            if msg is None:
                break
            try:
                self.layani(msg)
            except Exception as e:
                if msg.get("id") is not None:
                    _kirim({"jsonrpc": "2.0", "id": msg["id"],
                            "error": {"code": -32603,
                                      "message": "Red flag: %s" % e}})
            if self._shutdown:
                # tunggu pesan exit
                msg2 = _baca_pesan()
                if msg2 is None or msg2.get("method") == "exit":
                    break


def serve():
    Server().jalan()
