#!/data/data/com.termux/files/usr/bin/bash
# ============================================================================
# VoidMirror Utility - Installer
# Works on Termux. On regular Linux/macOS, run with: bash install.sh
# ============================================================================

echo "=============================================="
echo "   VoidMirror Utility - Installer"
echo "=============================================="

# Detect Termux vs normal Linux/macOS shell
if [ -d "/data/data/com.termux" ]; then
    echo "[*] Termux environment detected."
    pkg update -y
    pkg install python -y
else
    echo "[*] Non-Termux environment detected."
    echo "[*] Make sure Python 3 and pip are already installed."
fi

echo "[*] Upgrading pip..."
python3 -m pip install --upgrade pip

echo "[*] Installing required packages: flask, requests, beautifulsoup4"
python3 -m pip install flask requests beautifulsoup4

echo "=============================================="
echo "[OK] Installation complete."
echo "Run the tool with:   python voidsnapshot.py"
echo "=============================================="
