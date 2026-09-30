# CHANGELOG JakselScript

## v0.6.0 — 2026-10-01

Sepuluh upgrade. Bahasa makin ekspresif, tooling makin lengkap, VM makin informatif.

### Bahasa

- **Slice**: `daftar[1:3]`, `teks[0:5]`, `daftar[::2]`, `daftar[::-1]` — potong daftar/teks.
- **Null coalescing `??`**: `nama ?? "anonim"` — short-circuit, kanan lazy.
- **Ternary**: `"hadiah" kalo menang selain "zonk"` — branch lazy.
- **List comprehension**: `[x * 2 buat x dalam daftar kalo x > 0]`.
- **Chained comparison**: `1 < x < 10` — operan tengah dievaluasi sekali.
- **Optional chaining `?.`**: `user?.nama ?? "anonim"` — aman dari zonk.
- **`ekspor` eksplisit**: `ekspor tambah, kali` — batasi nama yang bisa di-collab.

### Tooling

- **LSP signature help**: `textDocument/signatureHelp` — info parameter pas ngetik.
- **LSP document symbols**: `textDocument/documentSymbol` — daftar fungsi/kelas/variabel.

### Mesin

- **VM stack traces**: error di VM sekarang menampilkan jejak tumpukan (nama fungsi + baris), sama kayak interpreter.

## v0.5.0 — 2026-10-01

Tiga puluh satu upgrade. Mesin baru, bahasa makin ekspresif, tooling makin lengkap.

### Bahasa

- **Destructuring**: `bestie [a, b] = [1, 2]`, `bestie {x, y} = {"x": 1}`.
- **Argumen bernama**: `sapa(nama, sapaan = "Hai")`.
- **Variadic**: `talent total(...angka)`, panggil pakai spread `total(...list)`.
- **`cocokkan` (pattern matching)**: literal, wildcard `_`, list, dict, enum, tipe, guard `kalo`.
- **`pilihan` (enum)**: `pilihan Warna { MERAH, HIJAU, BIRU = 10 }`, auto-numbering.
- **`rahasia`**: atribut/metode privat (name mangling).
- **`statik`**: metode/ atribut statik kelas.
- **`properti`**: getter/setter `ambil`/`taruh` dengan validasi.
- **Typed catch**: `yaudah HttpError e { }` — cuma nangkap tipe itu.
- **Import alias**: `collab "mtk" sebagai mm`.
- **Import selektif**: `collab "mtk" ambil kali, tambah`.
- **Python bridge**: `collab python "os"` — panggil modul Python langsung.
- **Operator `=>`** (panah) buat `cocokkan`.
- **String**: triple-quote, raw string, operator `...` (splat).
- **Hierarki error**: `Error` -> `HttpError`, `FileError`, dll.

### Mesin

- **VM bytecode**: `jaksel gas --vm`, `jaksel kompilasi` -> `.jsc`, `jaksel gas file.jsc`.
- **`.jsc`**: bytecode tersimpan, ingat direktori sumber buat import relatif.
- **Tugas paralel**: `tugas`/`tunggu` — concurrency via thread.
- **Sandbox**: `jaksel gas --aman` — batasi file/network/shell.

### Tooling

- **LSP**: go-to-definition, find references, rename (VS Code ready).
- **`jaksel tes`**: runner test bawaan.
- **`jaksel baru`**: scaffold proyek baru.
- **`jaksel lint`**: linter statis.
- **`jaksel dok`**: generator dokumentasi.
- **`jaksel bangun`**: build `.pyz` executable.
- **`jaksel kunci`**: generate `jaksel.lock`.
- **`jaksel kernel`**: install kernel Jupyter.
- **Paket**: manifest `paket.json`, perintah `pasang`/`paket`/`lepas`.

### Paritas

- Interpreter, VM, transpile->Python, dan `.jsc` menghasilkan output identik
  (99 tes lolos, termasuk 4 tes paritas v0.5).

## v0.4.0 — 2026-09-30


Dua puluh dua upgrade, satu rilis. Naik kelasnya kerasa banget.

### OOP (kelas)

- **Kelas**: `kelas Nama { ... }` — atribut instance, method, constructor `lahir`.
- **Pewarisan**: `kelas Anak warisi Ibu` — override method, constructor induk
  otomatis dipakai kalau anak nggak definisikan `lahir`.
- **`ini`**: instance saat ini (kayak `self`/`this`).
- **`ortu.metode()`**: panggil metode induk (lookup mulai dari kelas induk,
  bukan dari kelas pemilik `ini`) — termasuk `ortu.lahir(...)`.
- **Method sebagai nilai**: bound method bisa disimpan & dipanggil belakangan
  (callback-friendly).
- **`tampil()`**: representasi teks custom objek, dipakai `spill()`/`teks()`.
- **Pewarisan melingkar** (langsung/tak langsung) ditolak dengan error jelas.
- **Transpiler** menghasilkan class Python dengan `self`/`super()` yang
  setara semantik (termasuk bound method & `tampil()`).

### Bahasa

- **Parameter default**: `talent sapa(nama, sapaan = "halo")` — default
  harus di belakang.
- **`stalk i, x dalam daftar`**: loop for-each dengan indeks.
- **Operator `dalam`**: membership — `"a" dalam "abc"`, `2 dalam [1, 2]`,
  `"k" dalam {"k": 1}`.
- **Blok `akhirnya`** (finally): `yolo/yaudah/akhirnya` — selalu jalan,
  bahkan saat `balikin`/`ghosting`/`skip`/`cabut`.
- **`tipe(x)`**: nama tipe (`angka`/`teks`/`daftar`/`kamus`/`fungsi`/`kelas`/
  `zonk`/nama kelas).
- **`klaim(kondisi, pesan?)`**: assert — error kalau kondisi gimmick.
- **Agregat**: `total`, `terbesar`, `terkecil`, `rerata`, `urut_dengan`,
  `pasangkan`.
- **File & folder**: `ada_file`, `daftar_file`, `buat_folder`, `hapus_file`.
- **Saran typo keyword**: `kallo` → "Maksudnya 'kalo'?" (di parser,
  selain posisi assignment/pemanggilan).
- **Path file relatif** sekarang = relatif ke folder file program,
  bukan current working directory.

### Scripting nyata

- **`args()`**: argumen baris perintah (`jaksel gas app.jaksel a1 a2`).
- **`env(nama, default?)`**: baca environment variable.
- **JSON**: `json_tulis(x, cantik?)`, `json_urai(teks)`.
- **HTTP**: `http_get`, `http_get_json`, `http_post` (tanpa dependensi,
  pakai `urllib`).
- **Regex**: `cocok`, `cocok_penuh`, `cari`, `cari_semua`, `ganti_regex`,
  `pisah_regex`.
- **CSV**: `csv_baca`, `csv_tulis`.
- **`jalankan(perintah)`**: shell → kamus `{kode, keluar, galat}`.
  ⚠️ memakai shell sistem — jangan teruskan input user mentah-mentah.

### Tooling

- **Debugger interaktif** (`jaksel debug`): step per baris, breakpoint
  (`b <baris>`), `lanjut`, inspect ekspresi (`p <ekspresi>`), lihat
  tumpukan (`tumpuk`).
- **Jejak tumpukan** (stack trace): error tak tertangkap nampilin
  nama fungsi + nomor baris tiap frame.
- **Package manager mini**: `jaksel pasang <url-git/folder>` →
  `~/.jaksel/paket/`; `jaksel paket`; `jaksel lepas <nama>`.
- **Modul standar** `jaksel/std/`: `teks`, `angka`, `waktu`, `http` —
  dipakai via `collab "std/nama"`; `collab` juga mencari ke
  `~/.jaksel/paket/`.
- **REPL**: riwayat persisten (`~/.jaksel/repl_history`) + mode multiline
  (blok kurung kurawal belum seimbang dilanjutkan ke baris berikutnya).
- Semua fitur v0.4 didukung transpiler (parity interpreter ↔ Python).

### Contoh & tes

- Contoh baru: `contoh/oop.jaksel`, `contoh/sistem.jaksel`, `contoh/v04.jaksel`.
- Test suite: **93 kasus, semua lolos** — termasuk backtest HTTP lokal,
  debugger, REPL, package manager, formatter idempoten, dan parity
  transpile untuk semua contoh.

## v0.3.0 — 2026-09-30

Delapan fitur, satu rilis. Literally naik kelas.

### Bahasa
- **Method bawaan**: 7 method daftar (`tambah`, `buang`, `sisipkan`, `urut`,
  `balik`, `gabung`, `salin`), 7 method teks (`besar`, `kecil`, `potong`,
  `ganti`, `pisah`, `mulai_dengan`, `berakhir_dengan`), 4 method kamus
  (`kunci`, `nilai`, `ambil`, `hapus`). Method bisa di-chaining dan disimpan
  sebagai nilai (`bestie f = buah.tambah`).
- **Fungsi tingkat tinggi**: `petakan()` (map), `saring()` (filter),
  `kumpulkan()` (reduce) — menerima `talent` sebagai argumen.
- **File I/O**: `baca_file()`, `tulis_file()`, `tambah_file()`.
- **Tanggal**: `tanggal()` / `tanggal(format)` pakai format `strftime`.

### Tooling
- **Auto-formatter**: `jaksel rapi` — idempoten, komentar `//` dipertahankan,
  ada mode `--cek` dan `--stdout`.
- **AST/token inspector**: `jaksel urai` (`--token` / `--ast`).
- **Saran typo**: error `Maksudnya 'spill'?` untuk variabel, fungsi bawaan,
  dan method yang salah ketik.
- **LSP server** (`jaksel lsp`, tanpa dependensi): diagnostics real-time,
  hover documentation, completion (termasuk method setelah titik).
- **VS Code extension**: client LSP + highlight fungsi bawaan + restart command.
  Install: `cd vscode-jakselscript && npm install`, lalu F5.
- Transpiler diperluas: method, fungsi tingkat tinggi, file I/O, dan
  `tanggal()` semuanya setara semantik dengan interpreter.

### Kualitas
- Test suite: **67 kasus, 67 lolos** — termasuk contoh baru
  (`metode`, `fungsional`, `file_io`, `tanggal`), kasus typo negatif,
  dogfood `rapi --cek` di semua contoh, dan 14 kasus transpile-then-run.
- Semua contoh di `contoh/` diformat ulang pakai `jaksel rapi` sendiri.

## v0.2.0 — 2026-09-30

Update terbesar sejak lahir. Literally glow up.

### Bahasa
- **String interpolation**: `"Halo, {nama}! Umur {umur + 1}."` — ekspresi apa pun
  bisa ditaruh di dalam `{...}`, termasuk nested dan pemanggilan fungsi.
  Kurung kurawal literal pakai dobel: `{{` dan `}}`.
- **Stdlib mini**: `rentang()` (1–3 argumen, kayak `range`), `acak()` (0 argumen =
  float 0–1, 1–2 argumen = int acak), `waktu()` (epoch detik).

### Tooling
- **Transpiler ke Python**: `jaksel alihbahasakan program.jaksel [-o keluar.py]`
  menghasilkan Python murni yang setara secara semantik — termasuk perilaku
  `yolo`/`yaudah`, `collab` (di-inline), dan pesan error gaya Jaksel.
- **Error message modern**: setiap error (sintaks & runtime) sekarang menampilkan
  baris kode sumber + tanda `^` tepat di posisi error.
- **Installer**: `pip install .` (perintah `jaksel` global), `install.sh`
  (Linux/macOS), `install.ps1` (Windows PowerShell).
- **VS Code extension** (`vscode-jakselscript/`): syntax highlighting TextMate,
  language configuration, dan 9 snippets.

### Kualitas
- Test suite diperluas: **33 kasus, 33 lolos** — termasuk 10 kasus
  "transpile lalu jalankan, output harus identik dengan interpreter".
- Perbaikan bug: `collab` gagal saat `gas` dipakai dari direktori lain;
  escape `{{ }}` tanpa interpolasi.

## v0.1.0 — 2026-09-30

Rilis pertama. Interpreter Python murni (lexer → parser → AST → interpreter),
CLI `gas`/`cek`/REPL/`versi`, 10 contoh program, test suite 16 kasus.
Keyword Jaksel lengkap: spill, kepo, bestie, kalo/plot_twist, selama, gamon,
stalk, ghosting, skip, talent, balikin, valid/gimmick/zonk, nggak/dan/atau,
yolo/yaudah, red_flag, collab, healing, cabut.
