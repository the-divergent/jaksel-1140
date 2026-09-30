# JakselScript — VS Code Extension

Syntax highlighting, snippets, LSP (diagnostics, hover, completion),
dan konfigurasi bahasa buat file `.jaksel` di VS Code.

## Fitur

- Highlight keyword Jaksel: `spill`, `kalo`, `plot_twist`, `gamon`, `stalk`, `ghosting`, `talent`, `balikin`, `yolo`, `yaudah`, `red_flag`, dll.
- Highlight fungsi bawaan: `petakan`, `saring`, `tanggal`, `baca_file`, dll.
- Highlight nilai `valid` / `gimmick` / `zonk`.
- Highlight interpolasi string `{nama}` di dalam `"..."`.
- Komentar `//`, auto-closing kurung, dan bracket matching.
- Snippets: ketik `spill`, `kalo`, `talent`, `stalk`, `selama`, `gamon`, `yolo`, `bestie`, `plot_twist` lalu tekan Tab.
- **Language Server**: error sintaks real-time (diagnostics), dokumentasi
  saat hover, dan autocomplete (termasuk method setelah titik).
  Perintah: `JakselScript: Restart Language Server`.

## Cara install

### Metode 1: file .vsix (disarankan)

1. `cd vscode-jakselscript && npm install` (butuh Node.js).
2. `npx --yes @vscode/vsce package` — menghasilkan `jakselscript-0.6.0.vsix`.
3. `code --install-extension jakselscript-0.6.0.vsix`
4. Tutup total VS Code (**File → Exit**), buka lagi.

### Metode 2: mode development

1. `cd vscode-jakselscript && npm install`.
2. Buka folder ini di VS Code.
3. Tekan `F5` — extension jalan di jendela Extension Development Host.
4. Buka file `.jaksel` apa pun, misal `contoh/halo.jaksel`.

### Verifikasi

Buka file `.jaksel` — **pojok kanan bawah** VS Code harusnya tertulis
**JakselScript**. Kalau masih "Plain Text", klik tulisannya lalu pilih
**JakselScript** dari daftar.

Catatan: perintah `jaksel` harus bisa dipanggil dari terminal
(`pip install git+https://github.com/the-divergent/jaksel-1140.git` dulu,
atau atur `jakselscript.serverPath` di settings ke path executable-nya).

Panduan lengkap (PATH Windows, tombol Run ▶, troubleshooting):
[../PANDUAN-INSTALASI.md](../PANDUAN-INSTALASI.md).

## Cara publish ke Marketplace

```bash
npm install -g @vscode/vsce
vsce package   # menghasilkan jakselscript-0.3.0.vsix
vsce publish   # butuh Personal Access Token
```

Atau install file `.vsix` langsung: `Ctrl+Shift+P` → "Extensions: Install from VSIX..."
