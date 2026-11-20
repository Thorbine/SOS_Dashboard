#!/bin/bash
# Startet das SOS Dashboard (Mac). Doppelklick im Finder, oder: ./start.command
cd "$(dirname "$0")" || exit 1
export PATH="/Library/Frameworks/Python.framework/Versions/Current/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
PY="$(command -v python3)"
[ -z "$PY" ] && { echo "Python wurde nicht gefunden. Bitte Python 3.11 oder neuer von python.org installieren."; read -p "Enter zum Beenden"; exit 1; }
# Pakete nur installieren, wenn sie fehlen
if ! "$PY" -c "import webview, reportlab, svglib, PIL, certifi, pymupdf" 2>/dev/null; then
  "$PY" -m pip install -q --prefer-binary -r requirements.txt || { echo "Die Pakete konnten nicht installiert werden (Internetverbindung?)."; read -p "Enter zum Beenden"; exit 1; }
fi
"$PY" app.py || read -p "Fehler - Enter zum Beenden"
