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

## Cara install (manual)

1. `cd vscode-jakselscript && npm install` (butuh Node.js, buat LSP client).
2. Buka folder ini di VS Code.
3. Tekan `F5` — extension langsung jalan di jendela Extension Development Host.
4. Buka file `.jaksel` apa pun, misal `contoh/halo.jaksel`.

Catatan: perintah `jaksel` harus bisa dipanggil dari terminal
(`pip install .` dulu di folder JakselScript, atau atur
`jakselscript.serverPath` di settings ke path executable-nya).

## Cara publish ke Marketplace

```bash
npm install -g @vscode/vsce
vsce package   # menghasilkan jakselscript-0.3.0.vsix
vsce publish   # butuh Personal Access Token
```

Atau install file `.vsix` langsung: `Ctrl+Shift+P` → "Extensions: Install from VSIX..."
