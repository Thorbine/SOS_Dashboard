"""Erzeugt Beispiel-PDFs aller Schildtypen nach beispiel-pdfs/preisschilder/ (Aufruf im Projektordner:
python tools/preisschilder_beispiele.py). Helme und Ski nutzen die Logos des Altprogramms aus referenz/."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.preisschilder import settings, sheet  # noqa: E402
from modules.preisschilder.layouts import DRAW, schlaeger  # noqa: E402

OUT = ROOT / "beispiel-pdfs" / "preisschilder"
OLD_LOGOS = ROOT / "referenz" / "Preisschilder" / "daten" / "logos"
RACKET_LOGOS = ROOT / "assets" / "preisschilder" / "logos"
BRAND = {"wilson": "Wilson", "head": "HEAD", "babolat": "Babolat", "yonex": "Yonex", "tecnifibre": "Tecnifibre"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    helme = json.loads((ROOT / "referenz" / "Preisschilder" / "daten" / "liste_helme.json").read_text(encoding="utf-8"))
    sheet.LOGO_DIR = str(OLD_LOGOS)
    samples = {
        "helme": [dict(h, mass1="55-59 cm", statt="199" if i % 4 == 0 else "") for i, h in enumerate(helme[:16])],
        "baelle": [{"logo": "", "typ": "DTB-Spielball", "name": "Fort Tournament", "inhalt": "4er Dose", "preis": "8,95", "einzel": "2,24"},
                   {"logo": "", "typ": "", "name": "Head Tour", "inhalt": "3er Dose", "preis": "5,95", "einzel": ""}] * 4,
        "ski": [{"logo": "Ski/Atomic.png", "kategorie": "Allmountain", "modell": "Maverick 86 C", "zusatz1": "incl. Bindung",
                 "zusatz2": "incl. Montage", "text1": "Setpreis bei uns", "statt1": "599", "preis1": "449", "text2": "Mit Wunschbindung",
                 "statt2": "", "preis2": "519,5"},
                {"logo": "Ski/Salomon Schriftzug.png", "kategorie": "Race", "modell": "S/Race GS 12", "zusatz1": "", "zusatz2": "",
                 "text1": "", "statt1": "", "preis1": "1100", "text2": "", "statt2": "", "preis2": ""}] * 4,
    }
    samples["snowboard"] = samples["ski"][:2]
    for typ, items in samples.items():
        _, w, h = settings.TYPEN[typ]
        sheet.render_pdf(str(OUT / f"{typ}.pdf"), w, h, items, DRAW[typ], 10, 0)
        print(OUT / f"{typ}.pdf")
    sheet.LOGO_DIR = str(RACKET_LOGOS)
    cards = json.loads((ROOT / "referenz" / "schlaeger-beispiel.json").read_text(encoding="utf-8"))
    rackets = [dict(marke=BRAND[c["brand"]], farbe=c["color"], name=c["name"], kopfIn=c["kopfIn"], kopfCm=c["kopfCm"],
                    gewicht=c["gewicht"], besaitung=c["besaitung"], balance=c["balance"], preis=c["preis"], uvp=c["uvp"]) for c in cards]
    schlaeger.render_pdf(str(OUT / "schlaeger.pdf"), rackets)
    print(OUT / "schlaeger.pdf")


if __name__ == "__main__":
    main()
