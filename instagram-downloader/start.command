#!/bin/bash
# Startet den Instagram Downloader (Mac). Doppelklick im Finder, oder: ./start.command
cd "$(dirname "$0")" || exit 1
export PATH="/Library/Frameworks/Python.framework/Versions/Current/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
PY="$(command -v python3)"
[ -z "$PY" ] && { echo "Python wurde nicht gefunden. Bitte Python 3.11 oder neuer von python.org installieren."; read -p "Enter zum Beenden"; exit 1; }
if ! "$PY" -c "import yt_dlp, certifi, tkinter" 2>/dev/null; then
  "$PY" -m pip install -q --prefer-binary yt-dlp certifi || { echo "Installation fehlgeschlagen (Internetverbindung?)."; read -p "Enter zum Beenden"; exit 1; }
fi
SSL_CERT_FILE="$("$PY" -c 'import certifi;print(certifi.where())')" "$PY" app.py || read -p "Fehler - Enter zum Beenden"
