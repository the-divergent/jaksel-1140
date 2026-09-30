# JakselScript

> Bahasa pemrograman guyonan berbahasa gaul Jaksel.
> Ditulis dalam bahasa yang kamu pahami. Dijalankan dengan bangga.

```jaksel
// julid: program pertama
spill("Halo, bestie! Literally ini JakselScript v0.6.0!")

bestie nama = kepo("Spill nama kamu dong: ")

kalo nama == "" {
    red_flag("Nama kosong? Gimmick banget.")
} plot_twist {
    spill("Welcome to the circle, {nama}!")
}
```

## Instalasi

Butuh **Python 3.8+** (tanpa dependensi lain).

```bash
pip install git+https://github.com/the-divergent/jaksel-1140.git
```

Abis itu perintah `jaksel` bisa dipanggil di mana aja.

> 📖 **Tutorial lengkap dari nol** (termasuk beresi PATH di Windows,
> install extension VS Code, cara run pakai tombol ▶, dan troubleshooting):
> baca **[PANDUAN-INSTALASI.md](PANDUAN-INSTALASI.md)**.

## Cara pakai

| Perintah | Fungsi |
|---|---|
| `jaksel gas program.jaksel arg1 arg2` | jalankan file + argumen (dibaca via `args()`) |
| `jaksel cek program.jaksel` | cek sintaks tanpa menjalankan |
| `jaksel alihbahasakan program.jaksel [-o keluar.py]` | terjemahkan ke Python |
| `jaksel rapi program.jaksel` | auto-format kode (indent 4 spasi, `--cek`/`--stdout`) |
| `jaksel urai program.jaksel` | intip token & AST (`--token`/`--ast`) |
| `jaksel lsp` | language server (dipakai VS Code extension) |
| `jaksel debug program.jaksel` | debugger interaktif (step/breakpoint/inspect) |
| `jaksel pasang <url-git/folder>` | install paket `.jaksel` ke `~/.jaksel/paket/` |
| `jaksel paket` | daftar paket terpasang |
| `jaksel lepas <nama>` | hapus paket |
| `jaksel` | REPL interaktif (ada riwayat + multiline) |
| `jaksel versi` | tampilkan versi |

## Fitur v0.6

- **Slice** — `daftar[1:3]`, `teks[0:5]`, `daftar[::2]`, `daftar[::-1]`.
- **Null coalescing `??`** — `nama ?? "anonim"` (short-circuit).
- **Ternary** — `"hadiah" kalo menang selain "zonk"`.
- **List comprehension** — `[x * 2 buat x dalam daftar kalo x > 0]`.
- **Chained comparison** — `1 < x < 10`.
- **Optional chaining `?.`** — `user?.nama ?? "anonim"`.
- **`ekspor` eksplisit** — `ekspor tambah, kali`.
- **LSP** — signature help + document symbols.
- **VM stack traces** — jejak tumpukan di error VM.

## Fitur v0.5

- **Destructuring** — `bestie [a, b] = [1, 2]`, `bestie {x, y} = {"x": 1}`.
- **Argumen bernama & variadic** — `sapa(nama, sapaan = "Hai")`,
  `talent total(...angka)`, spread `total(...list)`.
- **`cocokkan` (pattern matching)** — literal, `_`, list/dict/enum/tipe, guard `kalo`.
- **`pilihan` (enum)** — auto-numbering, `Warna.MERAH`.
- **OOP++** — `rahasia` (privat), `statik`, `properti` (getter/setter `ambil`/`taruh`).
- **Typed catch** — `yaudah HttpError e { }`, hierarki `Error`.
- **Import canggih** — alias (`collab "mtk" sebagai mm`), selektif
  (`collab "mtk" ambil kali`), Python bridge (`collab python "os"`).
- **VM bytecode** — `jaksel gas --vm`, `jaksel kompilasi` -> `.jsc`,
  `jaksel gas file.jsc` (import relatif tetap jalan).
- **Tugas paralel** — `tugas`/`tunggu`.
- **Sandbox** — `jaksel gas --aman`.
- **LSP** — go-to-definition, references, rename.
- **CLI baru** — `tes`, `baru`, `lint`, `dok`, `bangun`, `kunci`, `kernel`.
- **Paket** — manifest `paket.json`, `jaksel.lock`.
- **Paritas 4 jalur** — interpreter == VM == transpile == `.jsc`.

## Fitur v0.4

- **OOP beneran** — `kelas`, `warisi`, constructor `lahir`, `ini`, `ortu.metode()`,
  override, method sebagai nilai (bound method), `tampil()` buat representasi teks.
  Pewarisan melingkar ditolak. Transpiler ngasilin class Python yang setara.
- **Scripting nyata** — `args()`, `env()`, JSON (`json_tulis`/`json_urai`),
  HTTP (`http_get`/`http_post`/`http_get_json`), regex (`cocok`, `cari_semua`,
  `ganti_regex`, `pisah_regex`, ...), CSV (`csv_baca`/`csv_tulis`), `jalankan()`
- **Bahasa** — parameter default (`talent sapa(nama, sapaan = "halo")`),
  `stalk i, x dalam daftar` (loop berindeks), operator `dalam` (membership),
  blok `akhirnya` (finally), `tipe()`, `klaim()` (assert), agregat
  (`total`, `terbesar`, `terkecil`, `rerata`, `urut_dengan`, `pasangkan`),
  file/folder (`ada_file`, `daftar_file`, `buat_folder`, `hapus_file`),
  saran typo keyword (`kallo` → "Maksudnya 'kalo'?")
- **Modul standar** — `collab "std/teks"`, `"std/angka"`, `"std/waktu"`,
  `"std/http"`; lookup `collab` juga nyari ke `~/.jaksel/paket/`
- **Jejak tumpukan** — error nggak ketangkep nampilin nama fungsi + nomor baris
- **Debugger interaktif** — `jaksel debug`: step, breakpoint, `lanjut`,
  inspect ekspresi (`p`), lihat tumpukan
- **Package manager mini** — `jaksel pasang/paket/lepas`
- **REPL** — riwayat persisten (`~/.jaksel/repl_history`) + mode multiline
- Path file relatif = relatif ke **folder file program** (bukan CWD)

## Fitur v0.3

- **Method bawaan** — `daftar.tambah()`, `daftar.urut()`, `teks.besar()`,
  `teks.pisah()`, `kamus.kunci()`, dll. (7 method daftar, 7 method teks, 4 method kamus)
- **Fungsi tingkat tinggi** — `petakan()`, `saring()`, `kumpulkan()`,
  bisa menerima `talent` sebagai argumen (bisa di-chaining)
- **File I/O** — `baca_file()`, `tulis_file()`, `tambah_file()`
- **Tanggal** — `tanggal()` / `tanggal("%d-%m-%Y")` pakai format `strftime`
- **Auto-formatter** — `jaksel rapi` (idempoten, komentar `//` nggak hilang)
- **AST/token inspector** — `jaksel urai` buat debugging & belajar
- **Saran typo** — error `Maksudnya 'spill'?` kalau nama mirip builtin/variabel/method
- **LSP + VS Code extension** — diagnostics real-time, hover documentation,
  completion (termasuk method setelah titik)

## Fitur v0.2

- **String interpolation** — `spill("Halo, {nama}! Umur {umur + 1}.")`, escape `{{` `}}`
- **Error message modern** — setiap error nunjukin baris kode + tanda `^` di posisi error
- **Stdlib mini** — `rentang()`, `acak()`, `waktu()`
- **Transpiler ke Python** — `jaksel alihbahasakan` ngasilin `.py` yang setara semantiknya
  (termasuk `yolo`/`yaudah` dan pesan error gaya Jaksel)
- **Installer** — `pip install .`, `install.sh`, `install.ps1`
- **VS Code extension** — syntax highlighting + snippets di folder `vscode-jakselscript/`

## Keyword

| Keyword | Arti |
|---|---|
| `spill(...)` | cetak ke layar |
| `kepo(...)` | baca input user |
| `bestie nama = ...` | deklarasi variabel |
| `kalo` / `plot_twist` | if / else |
| `selama` | while |
| `gamon` | loop selamanya (gagal move on) |
| `stalk x dalam daftar` | for-each |
| `ghosting` / `skip` | break / continue |
| `talent` / `balikin` | function / return |
| `valid` / `gimmick` / `zonk` | true / false / null |
| `nggak`, `dan`, `atau` | not, and, or |
| `yolo` / `yaudah` / `akhirnya` | try / catch / finally |
| `kelas` / `warisi` / `ini` / `ortu` | class / extends / this / super |
| `stalk i, x dalam daftar` | for-each dengan indeks |
| `x dalam daftar` | cek keanggotaan (in) |
| `talent f(a, b = 1)` | fungsi dengan parameter default |
| `tipe(x)` / `klaim(kondisi)` | cek tipe / assert |
| `args()` / `env(nama)` | argumen CLI / environment variable |
| `json_tulis(x)` / `json_urai(t)` | JSON encode / decode |
| `http_get(url)` / `http_post(url, data)` | HTTP GET / POST |
| `cocok(t, pola)` / `cari_semua(t, pola)` / `ganti_regex(t, p, g)` | regex |
| `csv_baca(p)` / `csv_tulis(p, data)` | baca / tulis CSV |
| `ada_file(p)` / `daftar_file()` / `buat_folder(p)` / `hapus_file(p)` | file & folder |
| `total(d)` / `terbesar(d)` / `terkecil(d)` / `rerata(d)` | agregat daftar |
| `urut_dengan(d, f)` / `pasangkan(a, b)` | sort by key / zip |
| `jalankan(perintah)` | jalankan perintah shell |
| `red_flag(...)` | throw error |
| `collab "..."` | import file `.jaksel` lain |
| `healing(n)` | jeda n detik |
| `rentang(a, b)` / `acak(a, b)` / `waktu()` | stdlib mini |
| `daftar.tambah(x)` / `urut()` / `gabung(p)` | method daftar |
| `teks.besar()` / `potong()` / `pisah(p)` / `ganti(a, b)` | method teks |
| `kamus.kunci()` / `ambil(k)` / `hapus(k)` | method kamus |
| `petakan(d, f)` / `saring(d, f)` / `kumpulkan(d, f, awal)` | fungsi tingkat tinggi |
| `baca_file(p)` / `tulis_file(p, t)` / `tambah_file(p, t)` | file I/O |
| `tanggal(fmt?)` | tanggal sekarang (format `strftime`) |
| `cabut` | keluar program |

## Contoh: terjemahan ke Python

```bash
jaksel alihbahasakan contoh/faktorial.jaksel -o faktorial.py
python3 faktorial.py
```

Hasilnya Python murni yang bisa dibaca, dimodifikasi, dan dishare ke
orang yang belum ngerti bahasa Jaksel.

Dokumentasi lengkap: [SPESIFIKASI.md](SPESIFIKASI.md).
Contoh program: folder [contoh/](contoh/).
Riwayat versi: [CHANGELOG.md](CHANGELOG.md).

## Menjalankan tes

```bash
python tes/run_tests.py
# 106 lolos, 0 gagal. Semua valid, bestie!
```

## Struktur proyek

```
jakselscript/
├── jaksel/
│   ├── lexer.py         # teks -> token
│   ├── parser.py        # token -> AST (+ interpolasi)
│   ├── errors.py        # error + pretty-print snippet
│   ├── interpreter.py   # AST -> eksekusi (+ method, OOP & saran typo)
│   ├── transpiler.py    # AST -> Python
│   ├── formatter.py     # AST -> kode rapi (jaksel rapi)
│   ├── inspector.py     # dump token & AST (jaksel urai)
│   ├── lsp.py           # language server (jaksel lsp)
│   ├── std/             # modul standar (teks, angka, waktu, http)
│   └── cli.py           # gas | cek | alihbahasakan | rapi | urai | lsp | debug | pasang | paket | repl | versi
├── bin/jaksel           # launcher CLI
├── contoh/              # contoh program .jaksel (23 file)
├── tes/run_tests.py     # test suite (106 kasus)
├── vscode-jakselscript/ # extension VS Code (grammar + snippets + LSP client)
├── install.sh           # installer Linux/macOS
├── install.ps1          # installer Windows
├── pyproject.toml       # packaging pip
├── SPESIFIKASI.md       # spesifikasi bahasa
├── CHANGELOG.md         # riwayat versi
└── README.md
```

## Roadmap

- [x] Method bawaan daftar/teks/kamus (v0.3.0)
- [x] Auto-formatter + AST inspector (v0.3.0)
- [x] LSP & integrasi VS Code (v0.3.0)
- [x] OOP: kelas, pewarisan, `ini`/`ortu` (v0.4.0)
- [x] Modul standar via `collab` + package manager mini (v0.4.0)
- [x] Debugger interaktif (v0.4.0)
- [x] JSON / HTTP / regex / CSV / shell (v0.4.0)
- [ ] Playground web (coba di browser)
- [ ] Mode bahasa Suroboyo & baku (satu engine)
- [ ] Publish extension ke VS Code Marketplace

## Lisensi

MIT — bebas dipakai, dimodifikasi, dan disebarluaskan.
Yang penting vibes-nya tetap Jaksel.
