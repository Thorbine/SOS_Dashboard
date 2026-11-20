@echo off
cd /d "%~dp0"
rem Pakete nur installieren, wenn sie fehlen; das Programm startet dann ohne Konsolenfenster (pyw)
py -c "import webview, reportlab, svglib, PIL, certifi, pymupdf" 2>nul
if errorlevel 1 py -m pip install -q --prefer-binary -r requirements.txt
start "" pyw app.py
