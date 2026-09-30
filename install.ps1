# Installer JakselScript untuk Windows (PowerShell)
# Cara pakai:
#   1. Download / clone repo JakselScript, buka foldernya di PowerShell, lalu:
#      .\install.ps1
#   2. Atau langsung dari GitHub (setelah repo dipublish):
#      .\install.ps1 -GitHub

param(
    [switch]$GitHub
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  Lagi install JakselScript, bestie..." -ForegroundColor Cyan
Write-Host ""

# 1. Cek Python
try {
    $pyVersion = (python --version 2>&1)
    Write-Host "  [valid] Ketemu $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "  [gimmick] Python nggak ketemu! Install dulu dari https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  (centang 'Add python.exe to PATH' pas install, bestie)" -ForegroundColor Yellow
    exit 1
}

# 2. Tentukan sumber install
if ($GitHub) {
    $sumber = "git+https://github.com/the-divergent/jakselscript.git"
    Write-Host "  [gas] Install dari GitHub..." -ForegroundColor Cyan
} elseif (Test-Path ".\pyproject.toml") {
    $sumber = "."
    Write-Host "  [gas] Install dari folder ini..." -ForegroundColor Cyan
} else {
    $sumber = "git+https://github.com/the-divergent/jakselscript.git"
    Write-Host "  [gas] pyproject.toml nggak ketemu di sini, coba dari GitHub..." -ForegroundColor Yellow
}

# 3. Install via pip
pip install --upgrade $sumber
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [gimmick] Install gagal. Coba jalanin PowerShell sebagai Administrator." -ForegroundColor Red
    exit 1
}

# 4. Verifikasi
Write-Host ""
try {
    $ver = (jaksel versi 2>&1)
    Write-Host "  [valid] $ver kepasang! Coba: jaksel gas contoh\halo.jaksel" -ForegroundColor Green
} catch {
    Write-Host "  [plot_twist] kepasang sih, tapi perintah 'jaksel' nggak kedetect." -ForegroundColor Yellow
    Write-Host "  Tutup PowerShell ini, buka baru, coba lagi. Kalau masih nggak bisa," -ForegroundColor Yellow
    Write-Host "  tambahin folder Scripts Python ke PATH." -ForegroundColor Yellow
}
Write-Host ""
