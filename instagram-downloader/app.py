"""Instagram Downloader (Mac): Links einfuegen, Videos in einen Ordner laden."""
import json
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import downloader

EINSTELLUNGEN = Path.home() / "Library" / "Application Support" / "Instagram Downloader" / "einstellungen.json"


def lade_einstellungen():
    try:
        return json.loads(EINSTELLUNGEN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def speichere_einstellungen(daten):
    try:
        EINSTELLUNGEN.parent.mkdir(parents=True, exist_ok=True)
        EINSTELLUNGEN.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instagram Downloader")
        self.geometry("640x560")
        self.minsize(520, 460)
        s = lade_einstellungen()
        self.ordner = tk.StringVar(value=s.get("ordner", str(Path.home() / "Downloads")))
        self.browser = tk.StringVar(value=s.get("browser", "Keiner"))
        self.meldungen = queue.Queue()
        self.laeuft = False
        self.letzte_datei = None
        self._bauen()
        self.after(100, self._abholen)

    def _bauen(self):
        pad = {"padx": 12, "pady": 6}
        ttk.Label(self, text="Instagram-Links (Reel oder Beitrag, ein Link pro Zeile):").pack(anchor="w", **pad)
        self.eingabe = tk.Text(self, height=6, wrap="word")
        self.eingabe.pack(fill="x", padx=12)

        zeile = ttk.Frame(self)
        zeile.pack(fill="x", **pad)
        ttk.Label(zeile, text="Speichern in:").pack(side="left")
        ttk.Entry(zeile, textvariable=self.ordner).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(zeile, text="Wählen…", command=self._ordner_waehlen).pack(side="left")

        zeile2 = ttk.Frame(self)
        zeile2.pack(fill="x", **pad)
        ttk.Label(zeile2, text="Anmeldung aus:").pack(side="left")
        ttk.Combobox(zeile2, textvariable=self.browser, values=downloader.BROWSER,
                     state="readonly", width=10).pack(side="left", padx=6)
        ttk.Label(zeile2, text="(nur nötig, wenn Instagram eine Anmeldung verlangt)",
                  foreground="gray").pack(side="left")

        knoepfe = ttk.Frame(self)
        knoepfe.pack(fill="x", **pad)
        self.start_knopf = ttk.Button(knoepfe, text="Herunterladen", command=self._start)
        self.start_knopf.pack(side="left")
        self.finder_knopf = ttk.Button(knoepfe, text="Im Finder zeigen", command=self._finder, state="disabled")
        self.finder_knopf.pack(side="left", padx=6)
        ttk.Button(knoepfe, text="yt-dlp aktualisieren", command=self._aktualisieren).pack(side="right")

        self.balken = ttk.Progressbar(self, maximum=100)
        self.balken.pack(fill="x", **pad)
        self.protokoll = tk.Text(self, height=10, state="disabled", wrap="word")
        self.protokoll.pack(fill="both", expand=True, padx=12)
        ttk.Label(self, foreground="gray", wraplength=600,
                  text="Nur Videos laden, an denen du die Rechte hast oder für die du eine Erlaubnis hast. "
                       "Die Nutzungsbedingungen von Instagram erlauben Downloads sonst nicht.").pack(anchor="w", **pad)

    def _log(self, text):
        self.protokoll.configure(state="normal")
        self.protokoll.insert("end", text + "\n")
        self.protokoll.see("end")
        self.protokoll.configure(state="disabled")

    def _ordner_waehlen(self):
        neu = filedialog.askdirectory(initialdir=self.ordner.get())
        if neu:
            self.ordner.set(neu)

    def _start(self):
        if self.laeuft:
            return
        urls = downloader.urls_aus_text(self.eingabe.get("1.0", "end"))
        if not urls:
            messagebox.showinfo("Keine Links", "Bitte mindestens einen Instagram-Link (Reel oder Beitrag) einfügen.")
            return
        speichere_einstellungen({"ordner": self.ordner.get(), "browser": self.browser.get()})
        self.laeuft = True
        self.start_knopf.configure(state="disabled")
        self.balken.configure(value=0)
        threading.Thread(target=self._arbeit, args=(urls, self.ordner.get(), self.browser.get()), daemon=True).start()

    def _arbeit(self, urls, ordner, browser):
        ok = 0
        for i, url in enumerate(urls, 1):
            self.meldungen.put(("log", "(%d/%d) %s" % (i, len(urls), url)))
            try:
                pfad = downloader.lade(url, ordner, browser, self._hook)
                self.meldungen.put(("datei", str(pfad)))
                self.meldungen.put(("log", "Fertig: " + pfad.name))
                ok += 1
            except RuntimeError as e:
                self.meldungen.put(("log", "Fehler: %s" % e))
        self.meldungen.put(("ende", "%d von %d geladen." % (ok, len(urls))))

    def _hook(self, d):
        if d.get("status") == "downloading":
            gesamt = d.get("total_bytes") or d.get("total_bytes_estimate")
            if gesamt:
                self.meldungen.put(("prozent", 100.0 * d.get("downloaded_bytes", 0) / gesamt))

    def _abholen(self):
        try:
            while True:
                art, wert = self.meldungen.get_nowait()
                if art == "log":
                    self._log(wert)
                elif art == "prozent":
                    self.balken.configure(value=wert)
                elif art == "datei":
                    self.letzte_datei = wert
                    self.finder_knopf.configure(state="normal")
                elif art == "ende":
                    self._log(wert)
                    self.balken.configure(value=100)
                    self.laeuft = False
                    self.start_knopf.configure(state="normal")
        except queue.Empty:
            pass
        self.after(100, self._abholen)

    def _finder(self):
        if self.letzte_datei:
            subprocess.run(["open", "-R", self.letzte_datei], check=False)
        else:
            subprocess.run(["open", self.ordner.get()], check=False)

    def _aktualisieren(self):
        self._log("Aktualisiere yt-dlp …")

        def los():
            r = subprocess.run(downloader.yt_dlp_aktualisieren(sys.executable), capture_output=True, text=True)
            self.meldungen.put(("log", "yt-dlp aktuell." if r.returncode == 0 else "Aktualisierung fehlgeschlagen: " + r.stderr[-200:]))
        threading.Thread(target=los, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
