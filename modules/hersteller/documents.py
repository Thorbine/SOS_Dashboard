"""Retourenschein (RS) und Reklamationsformular (RK): PDF-Erzeugung mit reportlab, Nummernkreise, Archiv.

`python -m modules.hersteller.documents` erzeugt zwei Beispiel-PDFs im Ordner beispiel-pdfs/.
"""

from __future__ import annotations

import copy
import os
import re
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DOC_TYPES = {
    "RS": {"name": "Retourenschein", "title": "Retourenschein"},
    "RK": {"name": "Reklamationsformular", "title": "Reklamation"},
}
WANTED = ["Reparatur", "Umtausch", "Gutschrift", "Geld zurück"]

BRAND = colors.HexColor("#595959")
LABEL_BG = colors.HexColor("#EDEDED")
LINE = colors.HexColor("#8C8C8C")
MUTED = colors.HexColor("#6B6B6B")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
WIDTH = PAGE_W - 2 * MARGIN

BASE = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=12.5)
SMALL = ParagraphStyle("small", parent=BASE, fontSize=8, leading=10, textColor=MUTED)
LABEL = ParagraphStyle("label", parent=BASE, fontSize=8.5, leading=11)
BOLD = ParagraphStyle("bold", parent=BASE, fontName="Helvetica-Bold")
BAR = ParagraphStyle("bar", parent=BASE, fontName="Helvetica-Bold", fontSize=10, textColor=colors.white)
TITLE = ParagraphStyle("title", parent=BASE, fontName="Helvetica-Bold", fontSize=20, leading=24)
RIGHT = ParagraphStyle("right", parent=BASE, alignment=TA_RIGHT)
NUMBER = ParagraphStyle("number", parent=RIGHT, fontName="Helvetica-Bold", fontSize=11, leading=24)
COMPANY = ParagraphStyle("company", parent=BASE, fontName="Helvetica-Bold", fontSize=16, leading=20)


# ----- Text -----

def clean(value) -> str:
    """Nur Zeichen, die Helvetica (WinAnsi) darstellen kann: Umlaute, ß und € bleiben erhalten."""
    return str(value if value is not None else "").encode("cp1252", "replace").decode("cp1252")


def markup(value) -> str:
    return escape(clean(value)).replace("\n", "<br/>")


def P(value, style=BASE) -> Paragraph:
    return Paragraph(markup(value), style)


def fmt_date(iso) -> str:
    """2026-11-14 -> 14.11.2026; alles andere bleibt, wie es ist."""
    text = str(iso or "")[:10]
    parts = text.split("-")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return f"{parts[2]}.{parts[1]}.{parts[0]}"
    return str(iso or "")


def address_lines(address: dict, contact_name: str = "") -> list[str]:
    person = contact_name or address.get("contactName", "")
    plz_ort = " ".join(x for x in (address.get("zip", ""), address.get("city", "")) if x)
    lines = [address.get("company", ""), address.get("addition", ""), f"z. Hd. {person}" if person else "",
             address.get("street", ""), plz_ort, address.get("country", "")]
    return [line for line in lines if line]


def sender_lines(company: dict) -> list[str]:
    plz_ort = " ".join(x for x in (company.get("zip", ""), company.get("city", "")) if x)
    lines = [company.get("name", ""), company.get("street", ""), plz_ort,
             f"Telefon {company['phone']}" if company.get("phone") else "",
             f"E-Mail {company['email']}" if company.get("email") else ""]
    return [line for line in lines if line]


def footer_text(company: dict) -> str:
    """Firmendaten für den Fuß, nur wenn in den Einstellungen angehakt."""
    if not company.get("showFooter"):
        return ""
    parts = [company.get("name", ""),
             f"Geschäftsführer: {company['managingDirector']}" if company.get("managingDirector") else "",
             company.get("register", ""),
             f"USt-IdNr. {company['vatId']}" if company.get("vatId") else ""]
    return clean(" · ".join(p for p in parts if p))


# ----- Bausteine -----

def bar(text: str) -> Table:
    """Abschnittsbalken: anthrazit mit weißer Schrift."""
    table = Table([[Paragraph(markup(text), BAR)]], colWidths=[WIDTH])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def grid(rows, col_widths, label_cells=(), extra=(), **kwargs) -> Table:
    """Tabelle mit dünnen Linien; label_cells sind (Spalte, Zeile)-Bereiche mit hellgrauem Grund."""
    table = Table(rows, colWidths=col_widths, **kwargs)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]
    style += [("BACKGROUND", start, end, LABEL_BG) for start, end in label_cells]
    table.setStyle(TableStyle(style + list(extra)))
    return table


def tall(value, width: float, min_height: float) -> list:
    """Zelleninhalt mit Mindesthöhe (für mehrzeilige Felder)."""
    para = P(value)
    _, height = para.wrap(width - 10, PAGE_H)
    return [para, Spacer(1, max(0, min_height - height))]


class Checks(Flowable):
    """Ankreuzfelder nebeneinander."""

    def __init__(self, options, selected):
        super().__init__()
        self.options = options
        self.selected = set(selected or [])

    def wrap(self, avail_width, avail_height):
        return avail_width, 12

    def draw(self):
        c = self.canv
        x = 0
        c.setLineWidth(0.7)
        c.setFont("Helvetica", 9.5)
        for option in self.options:
            c.rect(x, 1.5, 8.5, 8.5, stroke=1, fill=0)
            if option in self.selected:
                c.setLineWidth(1.2)
                c.line(x + 1.8, 3.3, x + 6.7, 8.2)
                c.line(x + 1.8, 8.2, x + 6.7, 3.3)
                c.setLineWidth(0.7)
            label = clean(option)
            c.drawString(x + 12, 2.7, label)
            x += 12 + stringWidth(label, "Helvetica", 9.5) + 16


def logo_flowable(logo_path, company: dict, height: float = 15 * mm):
    """SOS-Logo aus der SVG-Datei, sonst der Firmenname als Text."""
    if logo_path and Path(logo_path).is_file():
        try:
            from svglib.svglib import svg2rlg

            drawing = svg2rlg(str(logo_path))
            if drawing is not None and drawing.height:
                scale = height / drawing.height
                drawing.scale(scale, scale)
                drawing.width *= scale
                drawing.height = height
                return drawing
        except Exception:
            pass  # ein kaputtes Logo darf das Dokument nicht verhindern
    return P(company.get("name", ""), COMPANY)


def header(doc_type: str, number: str, date_iso: str, company: dict, logo_path, sender_line: bool) -> list:
    top = Table([[logo_flowable(logo_path, company), P(f"Datum: {fmt_date(date_iso)}", RIGHT)]],
                colWidths=[WIDTH * 0.6, WIDTH * 0.4])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
    title = Table([[P(DOC_TYPES[doc_type]["title"], TITLE), P(f"Nr. {number}", NUMBER)]], colWidths=[WIDTH * 0.6, WIDTH * 0.4])
    title.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    parts = [top]
    if sender_line:
        parts.append(P(" · ".join(sender_lines(company)), SMALL))
    parts += [Spacer(1, 5 * mm), title, Spacer(1, 4 * mm)]
    return parts


def make_canvas(head: str, foot: str):
    """Canvas, das Seitenzahlen ("Seite x von y"), den Fuß und ab Seite 2 eine Kopfzeile zeichnet."""

    class DocCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                self._decorate(total)
                super().showPage()
            super().save()

        def _decorate(self, total: int):
            self.setFont("Helvetica", 8)
            self.setFillColor(MUTED)
            self.setStrokeColor(LINE)
            self.setLineWidth(0.5)
            self.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Seite {self._pageNumber} von {total}")
            if foot:
                self.drawString(MARGIN, 10 * mm, foot)
            if self._pageNumber > 1:
                self.setFont("Helvetica-Bold", 9)
                self.drawString(MARGIN, PAGE_H - 12 * mm, head)
                self.line(MARGIN, PAGE_H - 13.5 * mm, PAGE_W - MARGIN, PAGE_H - 13.5 * mm)

    return DocCanvas


# ----- Retourenschein -----

def _return_slip(number, company, address, contact_name, data, logo_path) -> list:
    half = WIDTH / 2
    boxes = Table(
        [[Paragraph("Absender", BAR), Paragraph(markup("Empfänger"), BAR)],
         [P("\n".join(sender_lines(company))), P("\n".join(address_lines(address, contact_name)))]],
        colWidths=[half, half])
    boxes.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("GRID", (0, 1), (-1, 1), 0.5, LINE), ("LINEAFTER", (0, 0), (0, 0), 0.5, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, 0), 3), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 1), (-1, 1), 5), ("BOTTOMPADDING", (0, 1), (-1, 1), 7),
    ]))

    quarter = WIDTH / 4
    reference = grid(
        [[P("Unsere Kundennr", LABEL), P("RMA-/Retourennr.", LABEL), P("Versandart", LABEL), P("Anzahl Pakete", LABEL)],
         [P(data.get("customerNo", "")), P(data.get("rma", "")), P(data.get("shipping", "")), P(data.get("packages", ""))]],
        [quarter] * 4, label_cells=[((0, 0), (-1, 0))])

    widths = [x * mm for x in (10, 56, 24, 18, 26, 14, 26)]
    rows = [[P(t, LABEL) for t in ("Pos.", "Artikel", "Artikelnr.", "Größe", "Farbe", "Menge", "Grund")]]
    for i, pos in enumerate(data.get("positions", []), start=1):
        rows.append([P(i), P(pos.get("article", "")), P(pos.get("articleNo", "")), P(pos.get("size", "")),
                     P(pos.get("color", "")), P(pos.get("qty", "")), P(pos.get("reason", ""))])
    positions = grid(rows, widths, label_cells=[((0, 0), (-1, 0))], repeatRows=1)

    story = header("RS", number, data.get("date", ""), company, logo_path, sender_line=False)
    story += [boxes, Spacer(1, 4 * mm), reference, Spacer(1, 5 * mm), bar("Positionen"), positions, Spacer(1, 5 * mm)]

    reason = grid(
        [[P("Grund", LABEL), P(data.get("reasonGeneral", ""))],
         [P("Bemerkung", LABEL), tall(data.get("remark", ""), WIDTH - 32 * mm, 10 * mm)]],
        [32 * mm, WIDTH - 32 * mm], label_cells=[((0, 0), (0, -1))])
    sign = Table([["", "", ""], [P("Datum", SMALL), "", P("Unterschrift", SMALL)]],
                 colWidths=[55 * mm, 15 * mm, 85 * mm], rowHeights=[16 * mm, None], hAlign="LEFT")
    sign.setStyle(TableStyle([("LINEABOVE", (0, 1), (0, 1), 0.7, colors.black), ("LINEABOVE", (2, 1), (2, 1), 0.7, colors.black),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 1), (-1, 1), 2)]))
    story.append(KeepTogether([bar("Grund und Bemerkung"), reason, Spacer(1, 4 * mm), sign]))
    return story


# ----- Reklamationsformular -----

def _complaint(number, company, address, contact_name, data, logo_path) -> list:
    label_w = 35 * mm
    half = WIDTH / 2
    value_w = half - label_w
    cols = [label_w, value_w, label_w, value_w]
    labels = [((0, 0), (0, -1)), ((2, 0), (2, -1))]

    story = header("RK", number, data.get("date", ""), company, logo_path, sender_line=True)

    # Die Empfängeradresse steht ohne "z. Hd.", der Ansprechpartner hat rechts ein eigenes Feld.
    recipient = "\n".join(address_lines({**address, "contactName": ""}))
    story += [bar("Hersteller"), grid(
        [[P("Anschrift", LABEL), P(recipient), P("Unsere Kundennr", LABEL), P(data.get("customerNo", ""))],
         ["", "", P("Ansprechpartner", LABEL), P(contact_name or address.get("contactName", ""))],
         ["", "", P("Referenz/RMA-Nr", LABEL), P(data.get("reference", ""))]],
        cols, label_cells=labels, extra=[("SPAN", (0, 0), (0, 2)), ("SPAN", (1, 0), (1, 2))]),
        Spacer(1, 4 * mm)]

    articles = data.get("articles", []) or [{}]
    for i, art in enumerate(articles, start=1):
        block = [bar("Artikel" if len(articles) == 1 else f"Artikel {i}"), grid(
            [[P("Artikel", LABEL), P(art.get("article", "")), P("Artikelnr.", LABEL), P(art.get("articleNo", ""))],
             [P("Größe", LABEL), P(art.get("size", "")), P("Farbe", LABEL), P(art.get("color", ""))],
             [P("Kaufdatum", LABEL), P(fmt_date(art.get("purchaseDate", ""))), P("Beleg-Nr.", LABEL), P(art.get("receiptNo", ""))]],
            cols, label_cells=labels), Spacer(1, 4 * mm)]
        story.append(KeepTogether(block))

    wide = WIDTH - label_w
    story.append(KeepTogether([bar("Reklamation"), grid(
        [[P("Fehlerbeschreibung", LABEL), tall(data.get("description", ""), wide, 32 * mm)],
         [P("Gewünscht", LABEL), Checks(WANTED, data.get("wanted"))],
         [P("Zubehör dabei", LABEL), P(data.get("accessories", ""))]],
        [label_w, wide], label_cells=[((0, 0), (0, -1))]), Spacer(1, 4 * mm)]))

    if data.get("printProcessing"):
        # Bleibt leer zum handschriftlichen Ausfüllen.
        story.append(KeepTogether([bar("Bearbeitung"), grid(
            [[P("Gesendet am", LABEL), ""], [P("Rückmeldung", LABEL), ""], [P("Ergebnis", LABEL), ""]],
            [label_w, wide], label_cells=[((0, 0), (0, -1))], rowHeights=[9 * mm, 20 * mm, 20 * mm])]))
    return story


# ----- Einstieg -----

def build_pdf(doc_type: str, path, *, number: str, company: dict, address: dict, data: dict,
              contact_name: str = "", logo_path=None) -> Path:
    """Schreibt das PDF nach `path`. Ohne Schreibschutz und ohne Passwort, damit Portale es annehmen."""
    if doc_type not in DOC_TYPES:
        raise ValueError(f"Unbekannter Dokumenttyp: {doc_type}")
    path = Path(path)
    builder = _return_slip if doc_type == "RS" else _complaint
    story = builder(number, company, address, contact_name, data, logo_path)
    title = f"{DOC_TYPES[doc_type]['title']} {number}"
    # Der Rahmen von reportlab hat innen 6 pt Abstand; so sind Text und Tabellen bündig.
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=MARGIN - 6, rightMargin=MARGIN - 6,
                            topMargin=MARGIN, bottomMargin=20 * mm,
                            title=clean(title), author=clean(company.get("name", "")), subject=clean(DOC_TYPES[doc_type]["name"]))
    doc.build(story, canvasmaker=make_canvas(clean(title), footer_text(company)))
    return path


# ----- Nummernkreise und Archiv -----

ARCHIVE_DIR = "dokumente"
_TRANSLIT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"})


CUSTOM = "__custom__"  # Auswahlwert für eine einmalig eingegebene Adresse oder Person


class DocumentError(Exception):
    """Eingaben unvollständig oder Dokument nicht auffindbar. Die Meldung ist für die Oberfläche gedacht."""


def safe_name(text: str, fallback: str = "Hersteller") -> str:
    """Datei- und Ordnernamen ohne Sonderzeichen, damit Portale und Mailprogramme sie annehmen."""
    name = str(text or "").translate(_TRANSLIT)
    name = re.sub(r"[^A-Za-z0-9 ._-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:60].strip(" .") or fallback


def format_number(doc_type: str, year: str, n: int) -> str:
    return f"{doc_type}-{year}-{n:04d}"


def _find(supplier: dict, block_type: str, key: str, item_id: str):
    for block in supplier.get("blocks", []):
        if block.get("type") == block_type:
            for item in block.get(key, []):
                if item.get("id") == item_id:
                    return item
    return None


def _validated(doc_type: str, form: dict) -> dict:
    """Prüft die Pflichtfelder und entfernt leere Zeilen."""
    form = copy.deepcopy(form if isinstance(form, dict) else {})
    filled = lambda rows: [r for r in rows or [] if isinstance(r, dict) and str(r.get("article", "")).strip()]
    if doc_type == "RS":
        form["positions"] = filled(form.get("positions"))
        if not form["positions"]:
            raise DocumentError("Bitte mindestens eine Position mit Artikel eintragen.")
    else:
        form["articles"] = filled(form.get("articles"))
        if not form["articles"]:
            raise DocumentError("Bitte einen Artikel eintragen.")
        if not str(form.get("description", "")).strip():
            raise DocumentError("Bitte eine Fehlerbeschreibung eintragen.")
    return form


def create_document(data: dict, data_dir, doc_type: str, payload: dict, *, logo_path=None, now=None) -> dict:
    """Erzeugt das PDF im Archiv und trägt das Dokument in `data` ein.

    Die Nummer wird erst hier vergeben. `data` (Zähler und Dokumentenliste) wird nur verändert,
    wenn die PDF-Datei erfolgreich geschrieben wurde. Gibt den neuen Eintrag zurück.
    """
    if doc_type not in DOC_TYPES:
        raise DocumentError("Unbekannter Dokumenttyp.")
    now = now or datetime.now()
    payload = payload if isinstance(payload, dict) else {}
    supplier = next((s for s in data.get("suppliers", []) if s.get("id") == payload.get("supplierId")), None)
    if supplier is None:
        raise DocumentError("Der Hersteller wurde nicht gefunden.")
    form = _validated(doc_type, payload.get("data"))
    if form.get("addressId") == CUSTOM:
        # Einmalige Adresse, die beim Hersteller nicht hinterlegt ist.
        raw = form.get("customAddress") if isinstance(form.get("customAddress"), dict) else {}
        address = {k: str(raw.get(k, "")).strip() for k in ("company", "addition", "street", "zip", "city", "country")}
        if not (address["company"] and address["street"] and address["city"]):
            raise DocumentError("Bitte für die andere Adresse mindestens Firma, Straße und Ort eintragen.")
        address["id"] = ""
    else:
        address = _find(supplier, "addresses", "addresses", form.get("addressId"))
        if address is None:
            raise DocumentError("Bitte eine Empfängeradresse auswählen.")
    if form.get("contactId") == CUSTOM:
        contact_name = str(form.get("customContactName", "")).strip()
        if not contact_name:
            raise DocumentError("Bitte den Namen des anderen Ansprechpartners eintragen.")
    else:
        contact = _find(supplier, "contacts", "contacts", form.get("contactId"))
        contact_name = contact.get("name", "") if contact else ""

    try:
        year = str(date.fromisoformat(str(form.get("date", ""))[:10]).year)
    except ValueError:
        form["date"] = now.date().isoformat()
        year = str(now.year)

    # Nächste freie Nummer: nie eine vergeben, die schon in der Liste oder als Datei existiert.
    counters = data.setdefault("counters", {})
    used = {d.get("number") for d in data.get("documents", [])}
    folder = Path(data_dir) / ARCHIVE_DIR / safe_name(supplier.get("name", ""))
    n = int(counters.get(doc_type, {}).get(year, 0) or 0)
    while True:
        n += 1
        number = format_number(doc_type, year, n)
        target = folder / f"{number}_{DOC_TYPES[doc_type]['name']}.pdf"
        if number not in used and not target.exists():
            break

    snapshot = copy.deepcopy(address)
    tmp = target.with_name(target.name + ".tmp")
    try:
        folder.mkdir(parents=True, exist_ok=True)
        build_pdf(doc_type, tmp, number=number, company=data.get("company", {}), address=snapshot,
                  data=form, contact_name=contact_name, logo_path=logo_path)
        os.replace(tmp, target)
    except Exception as exc:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise DocumentError(f"Das PDF konnte nicht geschrieben werden: {exc}") from exc

    entry = {
        "id": str(uuid.uuid4()), "supplierId": supplier["id"], "type": doc_type, "number": number,
        "createdAt": now.replace(microsecond=0).isoformat(),
        "file": target.relative_to(Path(data_dir)).as_posix(),
        "addressSnapshot": snapshot, "contactName": contact_name, "data": form,
    }
    counters.setdefault(doc_type, {})[year] = n
    data.setdefault("documents", []).append(entry)
    return entry


def document_path(data: dict, data_dir, document_id: str) -> Path:
    """Pfad der PDF-Datei eines archivierten Dokuments (muss im Datenordner liegen und existieren)."""
    entry = next((d for d in data.get("documents", []) if d.get("id") == document_id), None)
    if entry is None:
        raise DocumentError("Das Dokument wurde nicht gefunden.")
    root = Path(data_dir).resolve()
    path = (root / str(entry.get("file", ""))).resolve()
    if root not in path.parents:
        raise DocumentError("Der Dateipfad des Dokuments ist ungültig.")
    if not path.is_file():
        raise DocumentError(f"Die Datei fehlt im Archiv: {entry.get('file')}")
    return path


def supplier_folder(data: dict, data_dir, supplier_id: str) -> Path:
    """Archivordner eines Herstellers: der Ordner seines neuesten Dokuments."""
    root = Path(data_dir).resolve()
    docs = [d for d in data.get("documents", []) if d.get("supplierId") == supplier_id]
    for entry in sorted(docs, key=lambda d: d.get("createdAt", ""), reverse=True):
        folder = (root / str(entry.get("file", ""))).resolve().parent
        if root in folder.parents and folder.is_dir():
            return folder
    raise DocumentError("Für diesen Hersteller gibt es noch keine Dokumente.")


# ----- Beispiel-PDFs -----

SAMPLE_COMPANY = {
    "name": "SOS Sport GmbH", "street": "Rebenring 10", "zip": "38106", "city": "Braunschweig", "country": "Deutschland",
    "phone": "+49 (0) 531-347711", "email": "shop@sos-sport.de", "managingDirector": "Oliver Nieß",
    "register": "HRB 4881, Amtsgericht Braunschweig", "vatId": "DE 201646705", "showFooter": False,
}
SAMPLE_ADDRESS = {
    "label": "Retourenadresse", "company": "Beispiel Sportartikel GmbH", "addition": "Retourenlager Halle 3",
    "street": "Logistikstraße 12", "zip": "85000", "city": "Musterhausen", "country": "Deutschland", "contactName": "",
}
SAMPLE_RS = {
    "date": "2026-11-14", "customerNo": "104711", "rma": "RMA-88123", "shipping": "DPD", "packages": 2,
    "reasonGeneral": "Fehllieferung", "remark": "Falsche Größen geliefert, bitte Gutschrift über 249,90 € erstellen.",
    "positions": [
        {"article": "Skischuh Formula 110", "articleNo": "601150", "size": "27,5", "color": "anthrazit", "qty": 1, "reason": "Fehllieferung"},
        {"article": "Skihelm Radar mit Visier", "articleNo": "323410", "size": "M/L", "color": "weiß", "qty": 3, "reason": "Fehllieferung"},
        {"article": "Tennisschläger Speed MP, unbesaitet", "articleNo": "233612", "size": "L3", "color": "schwarz/weiß", "qty": 2, "reason": "Retoure"},
        {"article": "Handschuh Größe 8 (Fäustling)", "articleNo": "", "size": "8", "color": "blau", "qty": 4, "reason": "Reklamation"},
    ],
}
SAMPLE_RK = {
    "date": "2026-11-14", "customerNo": "104711", "reference": "",
    "articles": [{"article": "Ski Supershape e-Magnum", "articleNo": "313303", "size": "170 cm", "color": "schwarz/gelb",
                  "purchaseDate": "2026-01-15", "receiptNo": "R-10442"}],
    "description": "Die Kante löst sich im Schaufelbereich nach drei Skitagen auf etwa 6 cm Länge.\n"
                   "Kein Sturz, kein Steinkontakt. Fotos liegen bei. Verkaufspreis 649,95 €.",
    "wanted": ["Umtausch"], "accessories": "Bindung montiert, Größe 310 mm eingestellt", "printProcessing": True,
}


def write_samples(folder) -> list[Path]:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    logo = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "assets" / "sos-logo.svg"
    common = {"company": SAMPLE_COMPANY, "logo_path": logo}
    return [
        build_pdf("RS", folder / "RS-2026-0001_Retourenschein.pdf", number="RS-2026-0001", address=SAMPLE_ADDRESS,
                  contact_name="Wareneingang", data=SAMPLE_RS, **common),
        build_pdf("RK", folder / "RK-2026-0001_Reklamationsformular.pdf", number="RK-2026-0001",
                  address={**SAMPLE_ADDRESS, "label": "Reklamationsadresse", "addition": "Service Center"},
                  contact_name="Martina Beispiel", data=SAMPLE_RK, **common),
    ]


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "beispiel-pdfs"
    for pdf in write_samples(target):
        print(pdf)
