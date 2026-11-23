"""Kern des Instagram Downloaders: URL-Pruefung und Download ueber yt-dlp (ohne Oberflaeche)."""
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

ERLAUBTE_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
ERLAUBTE_PFADE = ("p", "reel", "reels", "tv")
BROWSER = ["Keiner", "Safari", "Chrome", "Firefox", "Edge", "Brave"]


def urls_aus_text(text):
    """Zerlegt eingefuegten Text in eine Liste gueltiger Instagram-Links (ohne Doppelte)."""
    gefunden, doppelt = [], set()
    for roh in re.split(r"[\s,;]+", text or ""):
        url = pruefe_url(roh)
        if url and url not in doppelt:
            doppelt.add(url)
            gefunden.append(url)
    return gefunden


def pruefe_url(roh):
    """Gibt den bereinigten Link zurueck oder None, wenn es kein Instagram-Beitrag/Reel ist.
    Nur https/http; fremde Hosts werden abgelehnt."""
    roh = (roh or "").strip()
    if not roh:
        return None
    if "://" not in roh:
        roh = "https://" + roh
    try:
        teile = urlparse(roh)
    except ValueError:
        return None
    if teile.scheme not in ("http", "https") or (teile.hostname or "").lower() not in ERLAUBTE_HOSTS:
        return None
    pfad = [t for t in teile.path.split("/") if t]
    # Links wie /username/reel/ABC/ -> Benutzername entfernen
    if len(pfad) >= 3 and pfad[1] in ERLAUBTE_PFADE:
        pfad = pfad[1:]
    if len(pfad) < 2 or pfad[0] not in ERLAUBTE_PFADE:
        return None
    return "https://www.instagram.com/%s/%s/" % (pfad[0], pfad[1])


def dateiname_nfc(name):
    """Dateinamen mit Umlauten auf NFC normalisieren (Mac liefert sonst zerlegte Zeichen)."""
    return unicodedata.normalize("NFC", name)


def optionen(zielordner, browser="Keiner", fortschritt=None):
    """yt-dlp Optionen. Format 'best mp4' damit ffmpeg nicht noetig ist."""
    opts = {
        "outtmpl": str(Path(zielordner) / "%(uploader|instagram)s - %(id)s.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": False,
        "windowsfilenames": True,
        "progress_hooks": [fortschritt] if fortschritt else [],
    }
    if browser and browser != "Keiner":
        opts["cookiesfrombrowser"] = (browser.lower(),)
    return opts


def lade(url, zielordner, browser="Keiner", fortschritt=None):
    """Laedt ein Video. Rueckgabe: Pfad der Datei. Wirft RuntimeError mit lesbarer Meldung."""
    try:
        import yt_dlp
    except ImportError as e:
        raise RuntimeError("yt-dlp ist nicht installiert.") from e
    ziel = Path(zielordner).expanduser()
    ziel.mkdir(parents=True, exist_ok=True)
    try:
        with yt_dlp.YoutubeDL(optionen(ziel, browser, fortschritt)) as ydl:
            info = ydl.extract_info(url, download=True)
            pfad = Path(ydl.prepare_filename(info))
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(uebersetze_fehler(str(e))) from e
    nfc = pfad.with_name(dateiname_nfc(pfad.name))
    if nfc != pfad and pfad.exists() and not nfc.exists():
        pfad.rename(nfc)
        pfad = nfc
    return pfad


def uebersetze_fehler(text):
    t = text.lower()
    if "login" in t or "log in" in t or "rate-limit" in t or "empty media response" in t:
        return ("Instagram verlangt eine Anmeldung. Im Browser bei Instagram anmelden und in der App "
                "unter 'Anmeldung aus' diesen Browser waehlen.")
    if "private" in t:
        return "Der Beitrag ist privat."
    if "no video" in t or "there is no video" in t:
        return "In diesem Beitrag ist kein Video."
    if "unable to download" in t or "urlopen" in t or "network" in t:
        return "Keine Verbindung zu Instagram (Internet?)."
    return "Download fehlgeschlagen: " + text.replace("ERROR: ", "")[:300]


def yt_dlp_aktualisieren(python):
    """Befehl zum Aktualisieren (Instagram aendert oft etwas, dann hilft ein neues yt-dlp)."""
    return [python, "-m", "pip", "install", "-q", "--upgrade", "yt-dlp"]
