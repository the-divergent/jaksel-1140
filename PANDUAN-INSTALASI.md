# Panduan Instalasi JakselScript

Tutorial lengkap dari nol sampai bisa ngoding `.jaksel` di VS Code.
Ditulis berdasarkan pengalaman install beneran di Windows — jadi semua
jebakan yang umum sudah ditutup di sini.

## Daftar isi

1. [Prasyarat](#1-prasyarat)
2. [Install JakselScript (paket Python)](#2-install-jakselscript-paket-python)
3. [Beresi masalah PATH di Windows](#3-beresi-masalah-path-di-windows)
4. [Verifikasi instalasi](#4-verifikasi-instalasi)
5. [Install extension VS Code](#5-install-extension-vs-code)
6. [Cara menjalankan program](#6-cara-menjalankan-program)
7. [Snippets: ngetik lebih cepat](#7-snippets-ngetik-lebih-cepat)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prasyarat

| Kebutuhan | Buat apa | Cara cek |
|---|---|---|
| Python 3.8+ | menjalankan JakselScript | `python --version` |
| Git | download repo (opsional, bisa pakai ZIP) | `git --version` |
| Node.js (LTS) | install extension VS Code | `node --version` |

> Belum punya Python? Download di [python.org](https://www.python.org/downloads/).
> Belum punya Node.js? Download di [nodejs.org](https://nodejs.org/) (pilih LTS).

## 2. Install JakselScript (paket Python)

Buka terminal (di Windows: PowerShell), jalankan:

```bash
pip install git+https://github.com/the-divergent/jaksel-1140.git
```

Tunggu sampai muncul `Successfully installed jakselscript-0.6.0`.

### Alternatif: install dari source

```bash
git clone https://github.com/the-divergent/jaksel-1140.git
cd jaksel-1140
pip install .
```

### Alternatif: tanpa install sama sekali

```bash
git clone https://github.com/the-divergent/jaksel-1140.git
cd jaksel-1140
python -m jaksel gas contoh/halo.jaksel
```

## 3. Beresi masalah PATH di Windows

Habis `pip install`, kadang muncul warning ini:

```
WARNING: The script jaksel.exe is installed in '...\Python311\Scripts'
which is not on PATH.
```

Artinya perintah `jaksel` belum dikenali terminal. Solusinya, di PowerShell
(copy-paste satu baris ini):

```powershell
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:LOCALAPPDATA\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts", "User")
```

> Sesuaikan `Python311` dengan versi Python kamu (misal `Python312`).
> Kalau ragu, lihat path persisnya di pesan WARNING waktu install.

**Penting:** tutup SEMUA jendela terminal/PowerShell/VS Code, lalu buka lagi.
Perubahan PATH cuma berlaku buat terminal yang dibuka setelah perintah di atas.

### Jalan pintas (tanpa utak-atik PATH)

Kalau mager, perintah ini selalu bisa dipakai di mana aja:

```bash
python -m jaksel gas program.jaksel
```

## 4. Verifikasi instalasi

```bash
jaksel versi
```

Harusnya keluar:

```
JakselScript v0.6.0
```

Coba program pertama. Bikin file `coba.jaksel` isinya:

```jaksel
spill("Halo, bestie!")
```

Jalankan:

```bash
jaksel gas coba.jaksel
```

Keluar `Halo, bestie!`? Beres, bestie!

## 5. Install extension VS Code

Extension-nya ngasih: syntax highlighting, snippets, error real-time
(diagnostics), hover documentation, dan autocomplete buat file `.jaksel`.

### Langkah 1 — Download repo

- Buka https://github.com/the-divergent/jaksel-1140 di browser.
- Klik tombol hijau **<> Code** (kanan atas, di atas daftar file).
- Pilih **Download ZIP**, lalu extract di mana aja.
  (Atau: `git clone https://github.com/the-divergent/jaksel-1140.git`)

### Langkah 2 — Install dependensi extension

Buka terminal di folder `vscode-jakselscript` hasil extract, jalankan:

```bash
cd vscode-jakselscript
npm install
```

### Langkah 3 — Bikin file installer (.vsix)

```bash
npx --yes @vscode/vsce package
```

Nanti muncul file `jakselscript-0.6.0.vsix` di folder itu.

### Langkah 4 — Install ke VS Code

```bash
code --install-extension jakselscript-0.6.0.vsix
```

Tutup total VS Code (**File → Exit**, bukan cuma klik X), buka lagi.

### Verifikasi extension

1. Buka file `.jaksel` apa pun.
2. Lihat **pojok kanan bawah** VS Code — harusnya tertulis **JakselScript**.
   (Kalau masih "Plain Text", klik tulisannya → ketik `JakselScript` → pilih.)
3. Coba ketik `spill` lalu tekan **Tab** — harusnya jadi `spill()` otomatis.

## 6. Cara menjalankan program

### Cara A — Terminal (selalu bisa)

Buka terminal di VS Code (`Ctrl` + `` ` ``), jalankan:

```bash
jaksel gas coba.jaksel
```

### Cara B — Tombol ▶ (pakai extension Code Runner)

1. Di VS Code tekan `Ctrl+Shift+X`, cari **Code Runner**, klik **Install**.
2. Tekan `Ctrl+Shift+P` → ketik **Preferences: Open User Settings (JSON)**.
3. Tambahkan di dalam kurung kurawal (jangan lupa koma di baris sebelumnya):

```json
"code-runner.executorMap": {
    "jaksel": "jaksel gas"
}
```

4. Save. Sekarang tiap buka file `.jaksel`, klik tombol **▶** di pojok
   kanan atas — program langsung jalan.

### Cara C — Tanpa extension tambahan (pakai Task bawaan)

Bikin folder `.vscode` di project kamu, di dalamnya bikin file `tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Jalanin JakselScript",
            "type": "shell",
            "command": "jaksel gas ${file}",
            "group": { "kind": "build", "isDefault": true }
        }
    ]
}
```

Tiap mau jalanin file yang lagi dibuka, tekan **`Ctrl+Shift+B`**.

> Catatan: tombol F5 (Start Debugging) belum didukung — itu butuh debug
> adapter khusus yang masih dalam rencana.

## 7. Snippets: ngetik lebih cepat

Snippet diketik **di file kode (area editor)**, bukan di terminal.
Ketik keyword-nya, tekan **Tab**:

| Ketik | Jadi |
|---|---|
| `spill` + Tab | `spill()` |
| `kalo` + Tab | blok `kalo { }` |
| `talent` + Tab | definisi fungsi |
| `stalk` + Tab | loop `stalk` |
| `selama` + Tab | loop `selama` |
| `gamon` + Tab | loop `gamon` |
| `yolo` + Tab | blok `yolo`/`yaudah` |
| `bestie` + Tab | deklarasi variabel |
| `plot_twist` + Tab | blok `plot_twist` |

## 8. Troubleshooting

### `jaksel` is not recognized (PowerShell)

Folder `Scripts` belum masuk PATH. Ikuti
[Beresi masalah PATH di Windows](#3-beresi-masalah-path-di-windows),
atau pakai jalan pintas `python -m jaksel`.

### Code Runner: "code language not supported or defined"

File-nya belum dikenali sebagai bahasa JakselScript. Buka file `.jaksel`,
klik **pojok kanan bawah** (kalau tertulis "Plain Text") → pilih **JakselScript**.

Kalau **JakselScript nggak ada di daftar**, extension belum kepasang bener —
ulangi [langkah 4](#langkah-4--install-ke-vs-code) dan restart total VS Code.

### Extension tidak muncul di `@installed`

- Pastikan install lewat `code --install-extension` sampai muncul pesan sukses.
- Pastikan VS Code ditutup total (**File → Exit**), bukan cuma klik X.
- Cek dengan `code --list-extensions` — harusnya ada `jakselscript`.

### `npm` is not recognized

Node.js belum kepasang. Download di [nodejs.org](https://nodejs.org/)
(pilih LTS), install, tutup-buka lagi terminal.

### Error waktu `pip install`

- Pastikan Python 3.8+: `python --version`.
- Coba upgrade pip dulu: `python -m pip install --upgrade pip`.

---

Masih mentok? Buka issue di
[github.com/the-divergent/jaksel-1140/issues](https://github.com/the-divergent/jaksel-1140/issues)
— sertakan pesan error lengkapnya biar gampang dibantu.
