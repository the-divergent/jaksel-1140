#!/usr/bin/env python3
"""Test suite JakselScript: jalankan semua contoh + kasus negatif.

Usage: python3 tes/run_tests.py
Keluar dengan kode 0 kalau semua lolos.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run(cmd, stdin_data=None, cwd=ROOT):
    p = subprocess.run(
        cmd, input=stdin_data, capture_output=True, text=True,
        cwd=cwd, timeout=30)
    return p.returncode, p.stdout, p.stderr


def gas(path, stdin_data=None):
    return run([PY, "-m", "jaksel", "gas", path], stdin_data)


CASES = [
    # (nama, file, stdin, expected_stdout, expected_exit)
    ("halo", "contoh/halo.jaksel", None,
     "Halo, bestie! Literally ini JakselScript v0.5.0!\n"
     "Bahasa pemrograman yang vibes-nya Jaksel abis.\n", 0),

    ("faktorial", "contoh/faktorial.jaksel", None,
     "faktorial(0) = 1\nfaktorial(1) = 1\nfaktorial(2) = 2\n"
     "faktorial(3) = 6\nfaktorial(4) = 24\nfaktorial(5) = 120\n", 0),

    ("fibonacci", "contoh/fibonacci.jaksel", None,
     "fib(10) = 55\nfib(15) = 610\n", 0),

    ("loop", "contoh/loop.jaksel", None,
     "--- selama ---\ni = 0\ni = 1\ni = 2\n"
     "--- stalk ---\nsuka apel\nsuka duku\n"
     "--- gamon + ghosting ---\nkeluar gamon, n = 3\n", 0),

    ("kamus", "contoh/kamus.jaksel", None,
     "Budi umur 20\nhobi: healing, kota: Jaksel\n"
     "[99, 2, 3]\npanjang: 3\nindex negatif: 3\nteks di-index: j\n", 0),

    ("error_handling", "contoh/error_handling.jaksel", None,
     "coba bagi nol...\n"
     "ketangkep: Red flag baris 4: bagi nol? Gimmick banget.\n"
     "yaudah, lanjut...\nprogram tetap jalan, valid!\n", 0),

    ("collab", "contoh/pakai_utils.jaksel", None,
     "Halo, Budi! Literally seneng ketemu kamu.\n"
     "kuadrat 7 = 49\nutils versi 1.0\n", 0),

    ("cek_umur", "contoh/cek_umur.jaksel", "Budi\n20\n",
     "Welcome to the skena!\n"
     "Spill nama kamu dong: Umur berapa? "
     "Literally valid! Welcome to the circle, Budi\n"
     "Udah healing, gas lagi!\n", 0),

    ("tebak_angka", "contoh/tebak_angka.jaksel", "5\n9\n7\n",
     "=== Tebak Angka, bestie! ===\n"
     "Aku mikirin angka 1-10. Coba tebak!\n"
     "Tebakanmu (3 nyawa): Kekecilan, bestie.\n"
     "Tebakanmu (2 nyawa): Kegedean, bestie.\n"
     "Tebakanmu (1 nyawa): Literally bener! Kamu valid banget!\n"
     "Thanks for playing!\n", 0),

    ("interpolasi", "contoh/interpolasi.jaksel", None,
     "Halo, DIVERGENT! Umurmu 21 tahun.\n"
     "Tahun depan umurmu 22, bestie.\n"
     "Bawa 3 barang: [kopi, indomie, susu]\n"
     "Status: valid, lawannya gimmick, kosongnya zonk\n"
     "Kurung kurawal literal: {bukan variabel}\n"
     "Halo, Budi!\n", 0),

    ("stdlib", "contoh/stdlib.jaksel", None,
     "rentang(5): [0, 1, 2, 3, 4]\n"
     "rentang(2, 9, 3): [2, 5, 8]\n"
     "iterasi 0\niterasi 1\niterasi 2\n"
     "dadu valid, bestie\n"
     "waktu epoch jalan: valid\n", 0),

    ("metode", "contoh/metode.jaksel", None,
     "mangga, apel, duku\n"
     "[1, 2, 5, 8]\n[8, 5, 2, 1]\n1\n[8, 5, 2]\n"
     "jakselscript\n"
     "halo bestie\n"
     "[a, b, c]\n"
     "valid\nvalid\n"
     "[nama, kota]\n20\n"
     '{"nama": Budi}\n', 0),

    ("fungsional", "contoh/fungsional.jaksel", None,
     "[1, 4, 9, 16, 25]\n"
     "[2, 4]\n"
     "15\n"
     "[4, 16]\n"
     "[J, A, K, S, E, L]\n", 0),

    ("file_io", "contoh/file_io.jaksel", None,
     "baris satu\nbaris dua\nbaris tiga\n\n4\n", 0),

    ("oop", "contoh/oop.jaksel", None,
     "Halo, aku Tom!\n"
     "Tom bersuara: meong\n"
     "putih\n"
     "Doggo jaga rumah DIVERGENT: guk guk\n"
     "Kucing\n"
     "callback: meong\n"
     "0. Tom bersuara: meong\n"
     "1. Doggo bersuara: guk guk\n", 0),
]

# Kasus transpile: terjemahkan ke .py lalu jalankan, output harus sama.
# error_handling punya ekspektasi khusus (pesan transpiled tanpa "baris N").
TRANSPILE_CASES = [
    ("halo", "contoh/halo.jaksel", None,
     "Halo, bestie! Literally ini JakselScript v0.5.0!\n"
     "Bahasa pemrograman yang vibes-nya Jaksel abis.\n", 0),
    ("faktorial", "contoh/faktorial.jaksel", None,
     "faktorial(0) = 1\nfaktorial(1) = 1\nfaktorial(2) = 2\n"
     "faktorial(3) = 6\nfaktorial(4) = 24\nfaktorial(5) = 120\n", 0),
    ("fibonacci", "contoh/fibonacci.jaksel", None,
     "fib(10) = 55\nfib(15) = 610\n", 0),
    ("loop", "contoh/loop.jaksel", None,
     "--- selama ---\ni = 0\ni = 1\ni = 2\n"
     "--- stalk ---\nsuka apel\nsuka duku\n"
     "--- gamon + ghosting ---\nkeluar gamon, n = 3\n", 0),
    ("kamus", "contoh/kamus.jaksel", None,
     "Budi umur 20\nhobi: healing, kota: Jaksel\n"
     "[99, 2, 3]\npanjang: 3\nindex negatif: 3\nteks di-index: j\n", 0),
    ("error_handling", "contoh/error_handling.jaksel", None,
     "coba bagi nol...\n"
     "ketangkep: bagi nol? Gimmick banget.\n"
     "yaudah, lanjut...\nprogram tetap jalan, valid!\n", 0),
    ("collab", "contoh/pakai_utils.jaksel", None,
     "Halo, Budi! Literally seneng ketemu kamu.\n"
     "kuadrat 7 = 49\nutils versi 1.0\n", 0),
    ("interpolasi", "contoh/interpolasi.jaksel", None,
     "Halo, DIVERGENT! Umurmu 21 tahun.\n"
     "Tahun depan umurmu 22, bestie.\n"
     "Bawa 3 barang: [kopi, indomie, susu]\n"
     "Status: valid, lawannya gimmick, kosongnya zonk\n"
     "Kurung kurawal literal: {bukan variabel}\n"
     "Halo, Budi!\n", 0),
    ("stdlib", "contoh/stdlib.jaksel", None,
     "rentang(5): [0, 1, 2, 3, 4]\n"
     "rentang(2, 9, 3): [2, 5, 8]\n"
     "iterasi 0\niterasi 1\niterasi 2\n"
     "dadu valid, bestie\n"
     "waktu epoch jalan: valid\n", 0),
    ("tebak_angka", "contoh/tebak_angka.jaksel", "5\n9\n7\n",
     "=== Tebak Angka, bestie! ===\n"
     "Aku mikirin angka 1-10. Coba tebak!\n"
     "Tebakanmu (3 nyawa): Kekecilan, bestie.\n"
     "Tebakanmu (2 nyawa): Kegedean, bestie.\n"
     "Tebakanmu (1 nyawa): Literally bener! Kamu valid banget!\n"
     "Thanks for playing!\n", 0),
    ("metode", "contoh/metode.jaksel", None,
     "mangga, apel, duku\n"
     "[1, 2, 5, 8]\n[8, 5, 2, 1]\n1\n[8, 5, 2]\n"
     "jakselscript\n"
     "halo bestie\n"
     "[a, b, c]\n"
     "valid\nvalid\n"
     "[nama, kota]\n20\n"
     '{"nama": Budi}\n', 0),
    ("fungsional", "contoh/fungsional.jaksel", None,
     "[1, 4, 9, 16, 25]\n"
     "[2, 4]\n"
     "15\n"
     "[4, 16]\n"
     "[J, A, K, S, E, L]\n", 0),
    ("file_io", "contoh/file_io.jaksel", None,
     "baris satu\nbaris dua\nbaris tiga\n\n4\n", 0),
    ("oop", "contoh/oop.jaksel", None,
     "Halo, aku Tom!\n"
     "Tom bersuara: meong\n"
     "putih\n"
     "Doggo jaga rumah DIVERGENT: guk guk\n"
     "Kucing\n"
     "callback: meong\n"
     "0. Tom bersuara: meong\n"
     "1. Doggo bersuara: guk guk\n", 0),
]

NEGATIVE = [
    # (nama, source, stdin, fragmen_output, expected_exit)
    ("undefined_var", 'spill(variabel_ghaib)\n', None, "belum dikenalin", 1),
    ("type_error", 'spill(1 + "a")\n', None, "nggak bisa buat", 1),
    ("bagi_nol_tanpa_yolo", 'spill(1/0)\n', None, "Gimmick banget", 1),
    ("syntax_error", 'spill("lupa\n', None, "Gimmick nih sintaksnya", 1),
    ("arg_salah", 'talent f(a) { balikin a }\nspill(f(1, 2))\n', None,
     "butuh 1 argumen", 1),
    ("cabut_kode", 'cabut 42\n', None, "", 42),
    ("interp_brace_terbuka", 'spill("halo {nama")\n', None,
     "nggak ada pasangannya", 1),
    ("interp_brace_tutup", 'spill("halo }")\n', None,
     "nggak punya pasangan", 1),
    ("error_pakai_snippet", 'spill("lupa\n', None, "1 |", 1),
    ("typo_builtin", 'spilll("halo")\n', None, "Maksudnya 'spill'?", 1),
    ("typo_variabel", 'bestie buah = [1]\nspill(buahh)\n', None,
     "belum dikenalin", 1),
    ("typo_method", 'bestie buah = [1]\nbuah.tambha(2)\n', None,
     "Maksudnya 'tambah'?", 1),
    ("method_tipe_salah", 'spill((5).tambah(1))\n', None,
     "nggak punya method", 1),
    ("method_arg_salah", 'bestie b = [1]\nb.tambah()\n', None,
     "butuh 1 argumen", 1),
    ("hof_bukan_fungsi", 'spill(petakan([1, 2], 5))\n', None,
     "bukan fungsi", 1),
    ("baca_file_hilang", 'spill(baca_file("tes/_tmp_ghaib_xyz.txt"))\n', None,
     "nggak ketemu", 1),
    # v0.5.0 negatif: OOP & fitur baru
    ("warisi_bukan_kelas",
     'bestie x = 5\nkelas A warisi x {\n}\n', None, "bukan kelas", 1),
    ("warisi_sirkular",
     'kelas A warisi A {\n}\n', None, "melingkar", 1),
    ("warisi_sirkular_tak_langsung",
     'kelas A {\n}\nkelas B warisi A {\n}\nkelas A warisi B {\n}\n', None,
     "melingkar", 1),
    ("ortu_tanpa_induk",
     'kelas A {\n  talent f() {\n    ortu.f()\n  }\n}\nbestie a = A()\na.f()\n',
     None, "nggak punya induk", 1),
    ("param_default_salah_urutan",
     'talent f(a = 1, b) {\n  balikin a\n}\n', None, "Default harus di belakang", 1),
    ("klaim_gagal",
     'klaim(1 == 2, "harusnya sama")\n', None, "harusnya sama", 1),
    ("json_rusak",
     'spill(json_urai("{{bukan json}}"))\n', None, "JSON", 1),
    ("regex_rusak",
     'spill(cocok("x", "[nggak-tutup"))\n', None, "regex", 1),
    ("typo_keyword", 'kallo x > 1 {\n    spill("ya")\n}\n', None,
     "Maksudnya 'kalo'?", 1),
    ("kunci_hilang",
     'bestie d = {"a": 1}\nspill(d.b)\n', None, "nggak punya kunci", 1),
    ("panggil_bukan_fungsi",
     'bestie x = 5\nspill(x())\n', None, "bukan fungsi", 1),
    ("attr_objek_hilang",
     'kelas A {\n}\nbestie a = A()\nspill(a.ghaib)\n', None,
     "nggak punya atribut", 1),
]


# ============ v0.5.0: fixture server HTTP lokal (tanpa internet) ============
import json as _json
import shutil as _shutil
import tempfile as _tempfile
import threading as _threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _HandlerUji(BaseHTTPRequestHandler):
    def _kirim(self, body, ctype="text/plain"):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/data":
            self._kirim(_json.dumps({"pesan": "halo", "nilai": 42}),
                        "application/json")
        elif self.path == "/teks":
            self._kirim("teks biasa")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self._kirim(self.rfile.read(n).decode("utf-8"))

    def log_message(self, *a):
        pass


def _nyalakan_http():
    srv = HTTPServer(("127.0.0.1", 0), _HandlerUji)
    _threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


V04_EXPECTED = (
    "== parameter default ==\n"
    "halo budi\n"
    "hai sari\n"
    "== stalk berindeks ==\n"
    "0:apel\n"
    "1:duku\n"
    "== akhirnya ==\n"
    "tangkep\n"
    "beres\n"
    "== tipe & klaim ==\n"
    "angka,teks,daftar,kamus,fungsi\n"
    "== json ==\n"
    "4\n"
    '{"x": 1}\n'
    "== regex ==\n"
    "valid\n"
    "123\n"
    "[1, 22]\n"
    "h*l*\n"
    "== csv & file ==\n"
    "budi=90\n"
    "3 baris\n"
    "valid\n"
    "2 entri\n"
    "valid\n"
    "gimmick\n"
    "== agregat ==\n"
    "10\n"
    "4\n"
    "1\n"
    "2.5\n"
    "[a, bb, ccc]\n"
    "[[1, a], [2, b]]\n"
    "== dalam ==\n"
    "valid\n"
    "valid\n"
    "valid\n"
    "== args & env ==\n"
    "[a1, a2]\n"
    "asli\n"
    "== http lokal ==\n"
    "halo:42\n"
    "valid\n"
    "nama=budi\n"
    "== jalankan ==\n"
    "0:oke\n"
    "gas v0.5.0 selesai!\n"
)


def _env_v04(http_url, tmpdir):
    e = dict(os.environ)
    e["JAKSEL_HTTP_URL"] = http_url
    e["JAKSEL_TMP"] = tmpdir
    e["JAKSEL_TEST_VAR"] = "asli"
    return e



V05_EXPECTED = (
    "30\n12\nHalo, Budi!\nHai, Ani!\n10\n11\n"
    "satu\ndua\nlain\nWarna.MERAH\nWarna.BIRU\n"
    "merah!\nbiru!\n100\n250\nBank Jaksel\n"
    "ketangkep: http 404\n5\n20\n"
)


def test_v05_interpreter():
    """contoh/v05.jaksel via interpreter: output harus eksak."""
    p = subprocess.run(
        [PY, "-m", "jaksel", "gas", "contoh/v05.jaksel"],
        capture_output=True, text=True, cwd=ROOT, timeout=60)
    return p.returncode == 0 and p.stdout == V05_EXPECTED, p


def test_v05_vm_parity():
    """contoh/v05.jaksel: VM output harus identik interpreter."""
    p = subprocess.run(
        [PY, "-m", "jaksel", "gas", "--vm", "contoh/v05.jaksel"],
        capture_output=True, text=True, cwd=ROOT, timeout=60)
    return p.returncode == 0 and p.stdout == V05_EXPECTED, p


def test_v05_transpile_parity():
    """contoh/v05.jaksel: transpile->python output harus identik."""
    tmp_py = os.path.join(ROOT, "tes", "_tmp_v05.py")
    r1 = subprocess.run(
        [PY, "-m", "jaksel", "alihbahasakan", "contoh/v05.jaksel",
         "-o", tmp_py],
        capture_output=True, text=True, cwd=ROOT, timeout=60)
    ok = False
    p = None
    if r1.returncode == 0 and os.path.exists(tmp_py):
        p = subprocess.run([PY, tmp_py], capture_output=True,
                           text=True, cwd=ROOT, timeout=60)
        ok = p.returncode == 0 and p.stdout == V05_EXPECTED
        os.remove(tmp_py)
    return ok, p or r1


def test_v05_jsc_parity():
    """contoh/v05.jaksel: kompilasi .jsc lalu jalan, output identik."""
    tmp_jsc = os.path.join(ROOT, "tes", "_tmp_v05.jsc")
    r1 = subprocess.run(
        [PY, "-m", "jaksel", "kompilasi", "contoh/v05.jaksel",
         "-o", tmp_jsc],
        capture_output=True, text=True, cwd=ROOT, timeout=60)
    ok = False
    p = None
    if r1.returncode == 0 and os.path.exists(tmp_jsc):
        p = subprocess.run(
            [PY, "-m", "jaksel", "gas", tmp_jsc],
            capture_output=True, text=True, cwd=ROOT, timeout=60)
        ok = p.returncode == 0 and p.stdout == V05_EXPECTED
        os.remove(tmp_jsc)
    return ok, p or r1


def test_jsc_malformed():
    """.jsc rusak: magic salah, versi salah, payload terpotong."""
    tmp = os.path.join(ROOT, "tes", "_tmp_bad.jsc")
    try:
        # magic salah
        with open(tmp, "wb") as f:
            f.write(b"XXXX" + b"\x00" * 100)
        p = subprocess.run([PY, "-m", "jaksel", "gas", tmp],
                           capture_output=True, text=True, cwd=ROOT,
                           timeout=30)
        if p.returncode == 0:
            return False, "magic salah lolos"
        # payload terpotong
        with open(tmp, "wb") as f:
            f.write(b"JSC\x01")
        p = subprocess.run([PY, "-m", "jaksel", "gas", tmp],
                           capture_output=True, text=True, cwd=ROOT,
                           timeout=30)
        if p.returncode == 0:
            return False, "payload terpotong lolos"
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return True, None


def test_v04_interpreter(http_url):
    """contoh/v04.jaksel via interpreter: output harus eksak."""
    tmpdir = _tempfile.mkdtemp(prefix="jaksel_v04_")
    p = subprocess.run(
        [PY, "-m", "jaksel", "gas", "contoh/v04.jaksel", "a1", "a2"],
        capture_output=True, text=True, cwd=ROOT, timeout=60,
        env=_env_v04(http_url, tmpdir))
    _shutil.rmtree(tmpdir, ignore_errors=True)
    return p.returncode == 0 and p.stdout == V04_EXPECTED, p


def test_v04_transpile_parity(http_url):
    """contoh/v04.jaksel: transpile->python output harus identik interpreter."""
    tmpdir = _tempfile.mkdtemp(prefix="jaksel_v04t_")
    tmp_py = os.path.join(ROOT, "tes", "_tmp_v04.py")
    env = _env_v04(http_url, tmpdir)
    r1 = subprocess.run(
        [PY, "-m", "jaksel", "alihbahasakan", "contoh/v04.jaksel",
         "-o", tmp_py],
        capture_output=True, text=True, cwd=ROOT, timeout=60, env=env)
    ok = False
    p = None
    if r1.returncode == 0 and os.path.exists(tmp_py):
        p = subprocess.run([PY, tmp_py, "a1", "a2"], capture_output=True,
                           text=True, cwd=ROOT, timeout=60, env=env)
        ok = p.returncode == 0 and p.stdout == V04_EXPECTED
        os.remove(tmp_py)
    _shutil.rmtree(tmpdir, ignore_errors=True)
    return ok, p or r1


def test_debug():
    """Debugger interaktif dengan stdin scripted."""
    src = ('bestie x = 5\n'
           'bestie y = x * 2\n'
           'spill(y)\n')
    tmp = os.path.join(ROOT, "tes", "_tmp_debug.jaksel")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(src)
    # langkah, cetak x, breakpoint di baris 3, lanjut sampai selesai
    stdin_data = "\np x\nb 3\nlanjut\nlanjut\n"
    p = subprocess.run([PY, "-m", "jaksel", "debug", tmp], input=stdin_data,
                       capture_output=True, text=True, cwd=ROOT, timeout=30)
    os.remove(tmp)
    ok = (p.returncode == 0
          and "[debug] baris 1:" in p.stdout
          and "= 5" in p.stdout
          and "breakpoint di baris 3" in p.stdout
          and "[debug] baris 3:" in p.stdout
          and "10\n" in p.stdout
          and "Debug selesai" in p.stdout)
    return ok, p


def test_pasang():
    """Package manager: pasang (folder lokal) -> paket -> collab -> lepas."""
    home = _tempfile.mkdtemp(prefix="jaksel_home_")
    env = dict(os.environ, HOME=home)
    src = os.path.join(home, "paketku")
    os.makedirs(src)
    with open(os.path.join(src, "sapa.jaksel"), "w",
              encoding="utf-8") as f:
        f.write('talent sapa(nama) {\n    balikin "halo " + nama\n}\n')
    prog = os.path.join(home, "pakai.jaksel")
    with open(prog, "w", encoding="utf-8") as f:
        f.write('collab "paketku/sapa"\nspill(sapa("bestie"))\n')
    hasil = []

    def jl(*a):
        return subprocess.run([PY, "-m", "jaksel"] + list(a),
                              capture_output=True, text=True,
                              cwd=ROOT, timeout=30, env=env)

    r1 = jl("pasang", src)
    hasil.append(("pasang", r1.returncode == 0 and "kepasang" in r1.stdout))
    r2 = jl("paket")
    hasil.append(("paket", r2.returncode == 0 and "paketku" in r2.stdout))
    r3 = jl("gas", prog)
    hasil.append(("collab-paket", r3.returncode == 0
                  and r3.stdout.strip() == "halo bestie"))
    r4 = jl("lepas", "paketku")
    hasil.append(("lepas", r4.returncode == 0 and "dilepas" in r4.stdout))
    r5 = jl("paket")
    hasil.append(("paket-kosong", r5.returncode == 0
                  and "paketku" not in r5.stdout))
    _shutil.rmtree(home, ignore_errors=True)
    ok = all(h[1] for h in hasil)
    return ok, hasil


def test_repl():
    """REPL via stdin: ekspresi, multiline blok, interpolasi."""
    stdin_data = ('1 + 2\n'
                  'bestie nama = "budi"\n'
                  'spill("halo {nama}")\n'
                  'talent f(x) {\n'
                  '    balikin x * 2\n'
                  '}\n'
                  'f(21)\n'
                  'cabut\n')
    p = subprocess.run([PY, "-m", "jaksel"], input=stdin_data,
                       capture_output=True, text=True, cwd=ROOT, timeout=30)
    ok = (p.returncode == 0 and "> 3\n" in p.stdout
          and "halo budi" in p.stdout and "> 42\n" in p.stdout)
    return ok, p


def test_stack_trace():
    """Error di fungsi bersarang harus menampilkan jejak tumpukan."""
    src = ('talent lapis_dalam() {\n'
           '    red_flag "duar dari dalam"\n'
           '}\n'
           'talent lapis_luar() {\n'
           '    lapis_dalam()\n'
           '}\n'
           'lapis_luar()\n')
    tmp = os.path.join(ROOT, "tes", "_tmp_stack.jaksel")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(src)
    p = subprocess.run([PY, "-m", "jaksel", "gas", tmp],
                       capture_output=True, text=True, cwd=ROOT, timeout=30)
    os.remove(tmp)
    ok = (p.returncode == 1
          and "Jejak tumpukan" in p.stdout
          and "lapis_dalam" in p.stdout
          and "lapis_luar" in p.stdout)
    return ok, p


def test_v06_fitur():
    """v0.6: slice, ??, ternary, comprehension, chain, ?., ekspor."""
    cases = [
        # (source, expected_stdout)
        ('bestie d = [1,2,3,4,5]\nspill(d[1:3])\n', '[2, 3]\n'),
        ('bestie d = [1,2,3,4,5]\nspill(d[::-1])\n', '[5, 4, 3, 2, 1]\n'),
        ('spill("halo"[1:3])\n', 'al\n'),
        ('spill(zonk ?? "x")\n', 'x\n'),
        ('spill(zonk ?? zonk ?? "y")\n', 'y\n'),
        ('spill("a" kalo valid selain "b")\n', 'a\n'),
        ('spill("a" kalo gimmick selain "b")\n', 'b\n'),
        ('spill([x*2 buat x dalam [1,2,3]])\n', '[2, 4, 6]\n'),
        ('spill([x buat x dalam [1,2,3,4] kalo x > 2])\n', '[3, 4]\n'),
        ('bestie x = 5\nspill(1 < x < 10)\n', 'valid\n'),
        ('bestie x = 5\nspill(10 < x < 20)\n', 'gimmick\n'),
        ('bestie u = zonk\nspill(u?.nama ?? "anon")\n', 'anon\n'),
        ('bestie u = {"nama": "B"}\nspill(u?.nama)\n', 'B\n'),
    ]
    for src, expected in cases:
        for mode in ([], ["--vm"]):
            tmp = os.path.join(ROOT, "tes", "_tmp_v06.jaksel")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(src)
            p = subprocess.run([PY, "-m", "jaksel", "gas"] + mode + [tmp],
                               capture_output=True, text=True, cwd=ROOT,
                               timeout=30)
            os.remove(tmp)
            if p.stdout != expected:
                return False, (src, mode, p.stdout, expected)
    return True, None


def test_v06_ekspor():
    """v0.6: 'ekspor' membatasi nama yang bisa di-collab."""
    mod = ('bestie rahasia = 1\n'
           'talent pub() { balikin 42 }\n'
           'ekspor pub\n')
    main = ('collab "_tmp_v06mod" sebagai m\n'
            'spill(m.pub())\n')
    mod_path = os.path.join(ROOT, "tes", "_tmp_v06mod.jaksel")
    main_path = os.path.join(ROOT, "tes", "_tmp_v06main.jaksel")
    with open(mod_path, "w", encoding="utf-8") as f:
        f.write(mod)
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(main)
    try:
        for mode in ([], ["--vm"]):
            p = subprocess.run([PY, "-m", "jaksel", "gas"] + mode + [main_path],
                               capture_output=True, text=True, cwd=ROOT,
                               timeout=30)
            if p.stdout != "42\n":
                return False, ("ekspor pub()", mode, p.stdout)
        # rahasia nggak boleh kelihatan
        main2 = ('collab "_tmp_v06mod" sebagai m\n'
                 'spill(m.rahasia)\n')
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(main2)
        p = subprocess.run([PY, "-m", "jaksel", "gas", main_path],
                           capture_output=True, text=True, cwd=ROOT,
                           timeout=30)
        if p.returncode == 0:
            return False, ("rahasia bocor!", p.stdout)
    finally:
        for pp in (mod_path, main_path):
            if os.path.exists(pp):
                os.remove(pp)
    return True, None


def test_v06_vm_stack():
    """v0.6: VM juga menampilkan jejak tumpukan."""
    src = ('talent dalam2() {\n'
           '    red_flag "duar"\n'
           '}\n'
           'talent luar2() {\n'
           '    dalam2()\n'
           '}\n'
           'luar2()\n')
    tmp = os.path.join(ROOT, "tes", "_tmp_v06stack.jaksel")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(src)
    p = subprocess.run([PY, "-m", "jaksel", "gas", "--vm", tmp],
                       capture_output=True, text=True, cwd=ROOT, timeout=30)
    os.remove(tmp)
    ok = ("Jejak tumpukan" in p.stdout
          and "dalam2" in p.stdout
          and "luar2" in p.stdout)
    return ok, p


def test_v06_lsp():
    """v0.6: LSP signatureHelp + documentSymbol."""
    sys.path.insert(0, ROOT)
    try:
        from jaksel.lsp import _signature_help, _document_symbol
    finally:
        sys.path.remove(ROOT)
    src = ('talent tambah(a, b) {\n'
           '    balikin a + b\n'
           '}\n'
           'bestie x = 1\n')
    syms = _document_symbol("file:///t.jaksel", src) or []
    names = [s["name"] for s in syms]
    if "tambah" not in names or "x" not in names:
        return False, ("documentSymbol", names)
    # signatureHelp: lagi ngetik tambah(
    typing = src + "spill(tambah(1, "
    sig = _signature_help("file:///t.jaksel", typing, 4, 16)
    if not sig or sig["signatures"][0]["label"] != "tambah(a, b)":
        return False, ("signatureHelp", sig)
    if sig["activeParameter"] != 1:
        return False, ("activeParameter", sig["activeParameter"])
    return True, None


def test_std_modules():
    """Modul std/: teks, angka, waktu bisa di-collab dan dipakai."""
    src = ('collab "std/teks"\n'
           'collab "std/angka"\n'
           'collab "std/waktu"\n'
           'spill(judul("halo dunia"))\n'
           'spill(teks(faktorial(5)))\n'
           'spill(teks(median([3, 1, 2])))\n'
           'spill(slug("Halo Dunia Bestie"))\n')
    tmp = os.path.join(ROOT, "tes", "_tmp_std.jaksel")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(src)
    p = subprocess.run([PY, "-m", "jaksel", "gas", tmp],
                       capture_output=True, text=True, cwd=ROOT, timeout=30)
    os.remove(tmp)
    ok = (p.returncode == 0
          and p.stdout == "Halo Dunia\n120\n2\n"
          "halo-dunia-bestie\n")
    return ok, p


def test_file_relatif_program():
    """Path relatif file I/O = relatif ke folder program, bukan CWD."""
    progdir = _tempfile.mkdtemp(prefix="jaksel_prog_")
    prog = os.path.join(progdir, "app.jaksel")
    with open(prog, "w", encoding="utf-8") as f:
        f.write('tulis_file("relatif.txt", "isi program")\n'
                'spill(baca_file("relatif.txt"))\n'
                'spill(teks(ada_file("relatif.txt")))\n')
    cwd_lain = _tempfile.mkdtemp(prefix="jaksel_cwd_")
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    p = subprocess.run([PY, "-m", "jaksel", "gas", prog],
                       capture_output=True, text=True, cwd=cwd_lain,
                       timeout=30, env=env)
    ok = (p.returncode == 0
          and p.stdout == "isi program\nvalid\n"
          and os.path.exists(os.path.join(progdir, "relatif.txt"))
          and not os.path.exists(os.path.join(cwd_lain, "relatif.txt")))
    _shutil.rmtree(progdir, ignore_errors=True)
    _shutil.rmtree(cwd_lain, ignore_errors=True)
    return ok, p


def test_transpile_sirkular():
    """Transpiler menolak pewarisan melingkar (paritas dgn interpreter)."""
    kasus = [
        ("kelas A warisi A {\n}\n", "dirinya sendiri"),
        ("kelas A {\n}\nkelas B warisi A {\n}\nkelas A warisi B {\n}\n",
         "melingkar"),
    ]
    for src, fragmen in kasus:
        tmp = os.path.join(ROOT, "tes", "_tmp_sirk.jaksel")
        out = tmp + ".py"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(src)
        p = subprocess.run([PY, "-m", "jaksel", "alihbahasakan", tmp, "-o", out],
                           capture_output=True, text=True, cwd=ROOT,
                           timeout=30)
        for pp in (tmp, out):
            if os.path.exists(pp):
                os.remove(pp)
        if not (p.returncode == 1 and fragmen in p.stdout):
            return False, p
    return True, None


def main():
    passed, failed = 0, []
    for name, path, stdin_data, expected, code in CASES:
        rc, out, err = gas(path, stdin_data)
        if rc == code and out == expected:
            passed += 1
            print(f"  [OK] {name}")
        else:
            failed.append(name)
            print(f"  [GAGAL] {name}: exit={rc} (harap {code})")
            print(f"    stdout: {out!r}")
            if err:
                print(f"    stderr: {err!r}")

    for name, src, stdin_data, frag, code in NEGATIVE:
        tmp = os.path.join(ROOT, "tes", "_tmp_neg.jaksel")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(src)
        rc, out, err = gas(tmp, stdin_data)
        ok = rc == code and (frag in out or frag in err)
        if os.path.exists(tmp):
            os.remove(tmp)
        if ok:
            passed += 1
            print(f"  [OK] negatif: {name}")
        else:
            failed.append("negatif:" + name)
            print(f"  [GAGAL] negatif: {name}: exit={rc}, out={out!r}")

    # cek sintaks
    rc, out, _ = run([PY, "-m", "jaksel", "cek", "contoh/halo.jaksel"])
    if rc == 0 and "Valid!" in out:
        passed += 1
        print("  [OK] cek file valid")
    else:
        failed.append("cek-valid")
        print(f"  [GAGAL] cek file valid: {out!r}")

    # versi
    rc, out, _ = run([PY, "-m", "jaksel", "versi"])
    if rc == 0 and "0.6.0" in out:
        passed += 1
        print("  [OK] versi 0.6.0")
    else:
        failed.append("versi")
        print(f"  [GAGAL] versi: {out!r}")

    # tanggal(): output tergantung jam, cek pakai pola
    import re
    rc, out, _ = gas("contoh/tanggal.jaksel")
    baris = out.split("\n")
    ok_tanggal = (
        rc == 0 and len(baris) == 5
        and re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}", baris[0])
        and re.fullmatch(r"\d{2}-\d{2}-\d{4}", baris[1])
        and re.fullmatch(r"\d{2}:\d{2}", baris[2])
        and baris[3] == "epoch: valid"
    )
    if ok_tanggal:
        passed += 1
        print("  [OK] tanggal()")
    else:
        failed.append("tanggal")
        print(f"  [GAGAL] tanggal: {out!r}")

    # rapi: semua contoh harus lolos --cek (dogfood formatter)
    for f in sorted(os.listdir(os.path.join(ROOT, "contoh"))):
        if not f.endswith(".jaksel"):
            continue
        rc, out, _ = run([PY, "-m", "jaksel", "rapi", "--cek",
                          os.path.join("contoh", f)])
        if rc == 0:
            passed += 1
        else:
            failed.append("rapi:" + f)
            print(f"  [GAGAL] rapi --cek {f}: {out!r}")
    print(f"  [OK] rapi --cek semua contoh "
          f"({len([f for f in os.listdir(os.path.join(ROOT, 'contoh')) if f.endswith('.jaksel')])} file)")

    # rapi idempoten: format 2x hasilnya sama
    rc, out, _ = run([PY, "-m", "jaksel", "rapi", "--stdout",
                      "contoh/faktorial.jaksel"])
    tmp1 = os.path.join(ROOT, "tes", "_tmp_rapi1.jaksel")
    with open(tmp1, "w", encoding="utf-8") as fh:
        fh.write(out)
    rc2, out2, _ = run([PY, "-m", "jaksel", "rapi", "--stdout", tmp1])
    os.remove(tmp1)
    if rc == 0 and rc2 == 0 and out == out2:
        passed += 1
        print("  [OK] rapi idempoten")
    else:
        failed.append("rapi-idempoten")
        print("  [GAGAL] rapi idempoten")

    # urai: token & AST
    rc, out, _ = run([PY, "-m", "jaksel", "urai", "--token",
                      "contoh/halo.jaksel"])
    if rc == 0 and "=== TOKEN ===" in out and "IDENT" in out:
        passed += 1
        print("  [OK] urai --token")
    else:
        failed.append("urai-token")
        print(f"  [GAGAL] urai --token: {out!r}")
    rc, out, _ = run([PY, "-m", "jaksel", "urai", "--ast",
                      "contoh/halo.jaksel"])
    if rc == 0 and "=== AST ===" in out and "Program" in out:
        passed += 1
        print("  [OK] urai --ast")
    else:
        failed.append("urai-ast")
        print(f"  [GAGAL] urai --ast: {out!r}")

    # lsp: EOF di stdin -> server mati rapi (exit 0)
    p = subprocess.run([PY, "-m", "jaksel", "lsp"], input="",
                       capture_output=True, text=True, cwd=ROOT, timeout=15)
    if p.returncode == 0:
        passed += 1
        print("  [OK] lsp start/EOF")
    else:
        failed.append("lsp-eof")
        print(f"  [GAGAL] lsp EOF: exit={p.returncode} err={p.stderr!r}")

    # ---- v0.5.0: server HTTP lokal sekali untuk semua tes HTTP ----
    srv = _nyalakan_http()
    http_url = f"http://127.0.0.1:{srv.server_address[1]}"

    ok, p = test_v05_interpreter()
    if ok:
        passed += 1
        print("  [OK] v05 interpreter (destructuring/named/variadic/cocokkan/pilihan/properti/typed-catch)")
    else:
        failed.append("v05-interp")
        print(f"  [GAGAL] v05 interpreter: exit={p.returncode}")
        print(f"    stdout: {p.stdout!r}")
        if p.stderr:
            print(f"    stderr: {p.stderr[-500:]!r}")

    ok, p = test_v05_vm_parity()
    if ok:
        passed += 1
        print("  [OK] v05 VM parity")
    else:
        failed.append("v05-vm")
        print(f"  [GAGAL] v05 VM parity: exit={p.returncode}")
        print(f"    stdout: {p.stdout!r}")
        if p.stderr:
            print(f"    stderr: {p.stderr[-500:]!r}")

    ok, p = test_v05_transpile_parity()
    if ok:
        passed += 1
        print("  [OK] v05 transpile parity")
    else:
        failed.append("v05-transpile")
        print(f"  [GAGAL] v05 transpile parity: exit={p.returncode}")
        print(f"    stdout: {p.stdout!r}")
        if p.stderr:
            print(f"    stderr: {p.stderr[-500:]!r}")

    ok, p = test_v05_jsc_parity()
    if ok:
        passed += 1
        print("  [OK] v05 .jsc parity")
    else:
        failed.append("v05-jsc")
        print(f"  [GAGAL] v05 .jsc parity: exit={p.returncode}")
        print(f"    stdout: {p.stdout!r}")
        if p.stderr:
            print(f"    stderr: {p.stderr[-500:]!r}")

    ok, p = test_jsc_malformed()
    if ok:
        passed += 1
        print("  [OK] .jsc malformed ditolak")
    else:
        failed.append("jsc-malformed")
        print(f"  [GAGAL] .jsc malformed: {p}")

    ok, p = test_v04_interpreter(http_url)
    if ok:
        passed += 1
        print("  [OK] v04 interpreter (args/env/json/http/regex/csv/file/tipe/klaim/agregat/dalam)")
    else:
        failed.append("v04-interp")
        print(f"  [GAGAL] v04 interpreter: exit={p.returncode}")
        print(f"    stdout: {p.stdout!r}")
        if p.stderr:
            print(f"    stderr: {p.stderr[-500:]!r}")

    ok, p = test_v04_transpile_parity(http_url)
    if ok:
        passed += 1
        print("  [OK] v04 transpile parity")
    else:
        failed.append("v04-transpile")
        print(f"  [GAGAL] v04 transpile parity: exit={p.returncode}")
        print(f"    stdout: {p.stdout!r}")
        if p.stderr:
            print(f"    stderr: {p.stderr[-500:]!r}")

    srv.shutdown()

    for nama, fn in (("debug", test_debug),
                     ("repl", test_repl),
                     ("stack-trace", test_stack_trace),
                     ("v06-fitur", test_v06_fitur),
                     ("v06-ekspor", test_v06_ekspor),
                     ("v06-vm-stack", test_v06_vm_stack),
                     ("v06-lsp", test_v06_lsp),
                     ("std-modules", test_std_modules),
                     ("file-relatif-program", test_file_relatif_program),
                     ("transpile-sirkular", test_transpile_sirkular)):
        ok, p = fn()
        if ok:
            passed += 1
            print(f"  [OK] {nama}")
        else:
            failed.append(nama)
            print(f"  [GAGAL] {nama}: {p!r}"[:500])

    ok, hasil = test_pasang()
    if ok:
        passed += 1
        print("  [OK] pasang/paket/lepas")
    else:
        failed.append("pasang")
        print(f"  [GAGAL] pasang: {hasil!r}")

    # bersih-bersih artefak file_io (relatif ke folder contoh/*.jaksel)
    for tmp in ("contoh/_tmp_io.txt", "tes/_tmp_io.txt"):
        pp = os.path.join(ROOT, tmp)
        if os.path.exists(pp):
            os.remove(pp)

    # alihbahasakan: .jaksel -> .py
    tmp_py = os.path.join(ROOT, "tes", "_tmp_terjemahan.py")
    rc, out, _ = run([PY, "-m", "jaksel", "alihbahasakan",
                      "contoh/halo.jaksel", "-o", tmp_py])
    if rc == 0 and os.path.exists(tmp_py):
        passed += 1
        print("  [OK] alihbahasakan CLI")
        os.remove(tmp_py)
    else:
        failed.append("alihbahasakan-cli")
        print(f"  [GAGAL] alihbahasakan CLI: {out!r}")

    # transpile: tiap contoh diterjemahkan ke Python lalu dijalankan,
    # output harus identik dengan interpreter
    for name, path, stdin_data, expected, code in TRANSPILE_CASES:
        tmp_py = os.path.join(ROOT, "tes", "_tmp_transpile.py")
        rc1, out1, err1 = run(
            [PY, "-m", "jaksel", "alihbahasakan", path, "-o", tmp_py])
        if rc1 != 0:
            failed.append("transpile:" + name)
            print(f"  [GAGAL] transpile:{name}: {out1!r} {err1!r}")
            continue
        rc, out, err = run([PY, tmp_py], stdin_data)
        if os.path.exists(tmp_py):
            os.remove(tmp_py)
        if rc == code and out == expected:
            passed += 1
            print(f"  [OK] transpile: {name}")
        else:
            failed.append("transpile:" + name)
            print(f"  [GAGAL] transpile:{name}: exit={rc} (harap {code})")
            print(f"    stdout: {out!r}")
            if err:
                print(f"    stderr: {err!r}")

    print(f"\n{passed} lolos, {len(failed)} gagal.")
    if failed:
        print("Gagal:", ", ".join(failed))
        return 1
    print("Semua valid, bestie!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
