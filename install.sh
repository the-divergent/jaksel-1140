#!/usr/bin/env bash
# Installer JakselScript untuk Linux / macOS
# Cara pakai:
#   ./install.sh            # install dari folder repo ini
#   ./install.sh --github   # install langsung dari GitHub
set -e

echo ""
echo "  Lagi install JakselScript, bestie..."
echo ""

# 1. Cek Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "  [gimmick] python3 nggak ketemu! Install dulu, bestie."
    exit 1
fi
echo "  [valid] Ketemu $(python3 --version)"

# 2. Tentukan sumber install
if [ "${1:-}" = "--github" ]; then
    SUMBER="git+https://github.com/the-divergent/jakselscript.git"
    echo "  [gas] Install dari GitHub..."
elif [ -f "pyproject.toml" ]; then
    SUMBER="."
    echo "  [gas] Install dari folder ini..."
else
    SUMBER="git+https://github.com/the-divergent/jakselscript.git"
    echo "  [gas] pyproject.toml nggak ketemu di sini, coba dari GitHub..."
fi

# 3. Install via pip
python3 -m pip install --upgrade "$SUMBER"

# 4. Verifikasi
echo ""
if command -v jaksel >/dev/null 2>&1; then
    echo "  [valid] $(jaksel versi) kepasang! Coba: jaksel gas contoh/halo.jaksel"
else
    echo "  [plot_twist] kepasang sih, tapi perintah 'jaksel' nggak kedetect."
    echo "  Kemungkinan ~/.local/bin belum ada di PATH. Tambahin ke ~/.bashrc / ~/.zshrc:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi
echo ""
