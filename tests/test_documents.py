import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pypdf = pytest.importorskip("pypdf")

from modules.hersteller import documents  # noqa: E402


def pdf_text(path):
    reader = pypdf.PdfReader(str(path))
    # Zeilenumbrüche im Fließtext sollen die Suche nach Textstellen nicht stören.
    return len(reader.pages), " ".join("\n".join(page.extract_text() for page in reader.pages).split())


def build(tmp_path, doc_type, data, **kwargs):
    company = kwargs.pop("company", documents.SAMPLE_COMPANY)
    return documents.build_pdf(doc_type, tmp_path / f"{doc_type}.pdf", number=f"{doc_type}-2026-0001",
                               company=company, address=documents.SAMPLE_ADDRESS, data=data, **kwargs)


def test_return_slip_contains_umlauts_eszett_and_euro(tmp_path):
    data = {**documents.SAMPLE_RS, "remark": "Größe falsch, Maß prüfen – Gutschrift über 249,90 € (ÄÖÜ äöü ß)"}
    pages, text = pdf_text(build(tmp_path, "RS", data, contact_name="Jürgen Müßig"))
    assert pages == 1
    for expected in ("Retourenschein", "RS-2026-0001", "14.11.2026", "Empfänger", "Größe", "weiß",
                     "Logistikstraße 12", "z. Hd. Jürgen Müßig", "249,90 €", "ÄÖÜ äöü ß", "Seite 1 von 1"):
        assert expected in text, expected


def test_complaint_contains_umlauts_eszett_and_euro(tmp_path):
    pages, text = pdf_text(build(tmp_path, "RK", documents.SAMPLE_RK, contact_name="Martina Beispiel"))
    assert pages == 1
    for expected in ("Reklamation", "RK-2026-0001", "Kante löst sich", "649,95 €", "Zubehör dabei", "Größe 310 mm",
                     "Geld zurück", "Gewünscht", "15.01.2026", "Bearbeitung", "Rückmeldung", "Martina Beispiel"):
        assert expected in text, expected
    # Das Formular geht an den Hersteller: kein Preisfeld, keine Endkundendaten.
    assert "Preis " not in text and "Kunde" not in text.replace("Kundennr", "")


def test_complaint_without_processing_section(tmp_path):
    _, text = pdf_text(build(tmp_path, "RK", {**documents.SAMPLE_RK, "printProcessing": False}))
    assert "Bearbeitung" not in text and "Gesendet am" not in text


def test_complaint_with_several_articles(tmp_path):
    second = {"article": "Skistock Carbon", "articleNo": "", "size": "125 cm", "color": "rot", "purchaseDate": "", "receiptNo": ""}
    data = {**documents.SAMPLE_RK, "articles": documents.SAMPLE_RK["articles"] + [second]}
    _, text = pdf_text(build(tmp_path, "RK", data))
    assert "Artikel 1" in text and "Artikel 2" in text and "Skistock Carbon" in text


def test_many_positions_continue_on_further_pages(tmp_path):
    positions = [{"article": f"Artikel Nr. {i} für den Größentest", "articleNo": str(1000 + i), "size": "M",
                  "color": "weiß", "qty": 1, "reason": "Retoure"} for i in range(1, 91)]
    path = build(tmp_path, "RS", {**documents.SAMPLE_RS, "positions": positions})
    reader = pypdf.PdfReader(str(path))
    assert len(reader.pages) >= 3
    last = reader.pages[-1].extract_text()
    second = reader.pages[1].extract_text()
    assert "Retourenschein RS-2026-0001" in second            # Kopfzeile ab Seite 2
    assert "Pos." in second and "Artikelnr." in second         # Tabellenkopf wiederholt sich
    assert f"Seite 2 von {len(reader.pages)}" in second
    assert "Unterschrift" in last and "Artikel Nr. 90" in "".join(p.extract_text() for p in reader.pages)


def test_footer_only_when_enabled(tmp_path):
    _, without = pdf_text(build(tmp_path, "RS", documents.SAMPLE_RS))
    assert "HRB 4881" not in without and "Oliver Nieß" not in without
    company = {**documents.SAMPLE_COMPANY, "showFooter": True}
    _, with_footer = pdf_text(build(tmp_path, "RS", documents.SAMPLE_RS, company=company))
    assert "Geschäftsführer: Oliver Nieß" in with_footer and "USt-IdNr. DE 201646705" in with_footer


def test_characters_outside_winansi_do_not_break_the_pdf(tmp_path):
    data = {**documents.SAMPLE_RS, "remark": "Smiley \U0001F600 und Pfeil → im Text"}
    _, text = pdf_text(build(tmp_path, "RS", data))
    assert "Smiley" in text and "im Text" in text


def test_pdf_is_not_encrypted_and_has_title(tmp_path):
    reader = pypdf.PdfReader(str(build(tmp_path, "RK", documents.SAMPLE_RK)))
    assert not reader.is_encrypted
    assert reader.metadata.title == "Reklamation RK-2026-0001"


def test_missing_or_broken_logo_falls_back_to_company_name(tmp_path):
    broken = tmp_path / "logo.svg"
    broken.write_text("kein svg", encoding="utf-8")
    for logo in (tmp_path / "fehlt.svg", broken):
        _, text = pdf_text(build(tmp_path, "RS", documents.SAMPLE_RS, logo_path=logo))
        assert "SOS Sport GmbH" in text


def test_unknown_type_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path, "XX", {})


# ----- Nummernkreise, Archiv, Adress-Snapshot (Phase 3b) -----

import copy  # noqa: E402
from datetime import datetime  # noqa: E402

from modules.hersteller import models  # noqa: E402

NOW = datetime(2026, 11, 14, 10, 0, 0)


def make_data(name="Völkl & Söhne GmbH"):
    data = models.new_data()
    supplier = models.new_supplier(name, data["blockTemplate"])
    supplier["blocks"][0]["fields"][0]["value"] = "104711"
    supplier["blocks"][1]["contacts"].append(models.new_contact(name="Jürgen Müßig"))
    for address in supplier["blocks"][2]["addresses"]:
        address.update(company="Beispiel GmbH", street="Logistikstraße 12", zip="85000", city="Musterhausen")
    data["suppliers"].append(supplier)
    return data, supplier


def rs_payload(supplier, **changes):
    form = {**copy.deepcopy(documents.SAMPLE_RS), "addressId": supplier["blocks"][2]["addresses"][1]["id"], "contactId": ""}
    form.update(changes)
    return {"supplierId": supplier["id"], "data": form}


def rk_payload(supplier, **changes):
    form = {**copy.deepcopy(documents.SAMPLE_RK), "addressId": supplier["blocks"][2]["addresses"][2]["id"], "contactId": ""}
    form.update(changes)
    return {"supplierId": supplier["id"], "data": form}


def test_numbers_run_per_type_and_year_without_gaps(tmp_path):
    data, s = make_data()
    make = lambda t, p: documents.create_document(data, tmp_path, t, p, now=NOW)["number"]
    assert [make("RS", rs_payload(s)) for _ in range(3)] == ["RS-2026-0001", "RS-2026-0002", "RS-2026-0003"]
    assert make("RK", rk_payload(s)) == "RK-2026-0001"
    assert make("RS", rs_payload(s, date="2027-01-02")) == "RS-2027-0001"
    assert make("RS", rs_payload(s)) == "RS-2026-0004"
    assert data["counters"] == {"RS": {"2026": 4, "2027": 1}, "RK": {"2026": 1}}
    numbers = [d["number"] for d in data["documents"]]
    assert len(numbers) == len(set(numbers)) == 6


def test_document_is_archived_with_clean_file_name(tmp_path):
    data, s = make_data()
    entry = documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)
    assert entry["file"] == "dokumente/Voelkl Soehne GmbH/RS-2026-0001_Retourenschein.pdf"
    assert (tmp_path / entry["file"]).is_file()
    assert entry["supplierId"] == s["id"] and entry["type"] == "RS" and entry["createdAt"] == "2026-11-14T10:00:00"
    assert entry["data"]["positions"][0]["article"] == "Skischuh Formula 110"  # Eingaben für "Als Kopie weiterverwenden"
    assert not list(tmp_path.rglob("*.tmp"))
    rk = documents.create_document(data, tmp_path, "RK", rk_payload(s), now=NOW)
    assert rk["file"].endswith("/RK-2026-0001_Reklamationsformular.pdf")


def test_number_is_not_consumed_when_pdf_fails(tmp_path, monkeypatch):
    data, s = make_data()
    documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)

    def boom(*args, **kwargs):
        raise OSError("Platte voll")

    monkeypatch.setattr(documents, "build_pdf", boom)
    with pytest.raises(documents.DocumentError):
        documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)
    monkeypatch.undo()

    assert data["counters"]["RS"] == {"2026": 1} and len(data["documents"]) == 1
    assert len(list(tmp_path.rglob("*.pdf"))) == 1 and not list(tmp_path.rglob("*.tmp"))
    assert documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)["number"] == "RS-2026-0002"


def test_invalid_input_consumes_no_number(tmp_path):
    data, s = make_data()
    bad = [
        ("RS", rs_payload(s, positions=[{"article": "  "}])),
        ("RS", rs_payload(s, addressId="gibt-es-nicht")),
        ("RK", rk_payload(s, description=" ")),
        ("RK", rk_payload(s, articles=[])),
        ("RS", {"supplierId": "unbekannt", "data": {}}),
        ("XX", rs_payload(s)),
    ]
    for doc_type, payload in bad:
        with pytest.raises(documents.DocumentError):
            documents.create_document(data, tmp_path, doc_type, payload, now=NOW)
    assert data["counters"] == {"RS": {}, "RK": {}} and data["documents"] == []
    assert not list(tmp_path.rglob("*.pdf"))


def test_number_never_reused_even_if_counter_was_lost(tmp_path):
    data, s = make_data()
    first = documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)
    data["counters"] = {"RS": {}, "RK": {}}          # z. B. altes Backup zurückgespielt
    second = documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)
    assert second["number"] == "RS-2026-0002"
    data["counters"] = {"RS": {}, "RK": {}}
    data["documents"] = []                            # Liste weg, Dateien noch da
    third = documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)
    assert third["number"] == "RS-2026-0003" and first["number"] == "RS-2026-0001"
    assert len(list(tmp_path.rglob("*.pdf"))) == 3


def test_address_snapshot_is_independent_of_later_changes(tmp_path):
    data, s = make_data()
    address = s["blocks"][2]["addresses"][1]
    entry = documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)
    before = (tmp_path / entry["file"]).read_bytes()

    address["street"] = "Neue Straße 99"
    address["city"] = "Anderswo"
    s["blocks"][2]["addresses"].remove(s["blocks"][2]["addresses"][0])

    assert entry["addressSnapshot"]["street"] == "Logistikstraße 12"
    assert entry["addressSnapshot"]["city"] == "Musterhausen"
    assert entry["addressSnapshot"]["label"] == "Retourenadresse"
    assert (tmp_path / entry["file"]).read_bytes() == before
    _, text = pdf_text(tmp_path / entry["file"])
    assert "Logistikstraße 12" in text and "Neue Straße 99" not in text

    newer = documents.create_document(data, tmp_path, "RS", rs_payload(s, addressId=address["id"]), now=NOW)
    assert newer["addressSnapshot"]["street"] == "Neue Straße 99"


def test_contact_and_customer_number_appear_in_pdf(tmp_path):
    data, s = make_data()
    contact = s["blocks"][1]["contacts"][0]
    entry = documents.create_document(data, tmp_path, "RK", rk_payload(s, contactId=contact["id"], customerNo="KD-4711"), now=NOW)
    _, text = pdf_text(tmp_path / entry["file"])
    assert entry["contactName"] == "Jürgen Müßig" and "Jürgen Müßig" in text and "KD-4711" in text
    empty = documents.create_document(data, tmp_path, "RK", rk_payload(s, customerNo=""), now=NOW)
    assert (tmp_path / empty["file"]).is_file()  # fehlende Kundennummer: Feld bleibt leer


def test_copy_gets_new_number(tmp_path):
    data, s = make_data()
    original = documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)
    copy_payload = {"supplierId": s["id"], "data": copy.deepcopy(original["data"])}
    again = documents.create_document(data, tmp_path, "RS", copy_payload, now=NOW)
    assert again["number"] == "RS-2026-0002" and again["id"] != original["id"]
    assert again["data"]["positions"] == original["data"]["positions"]
    assert (tmp_path / original["file"]).is_file() and (tmp_path / again["file"]).is_file()


def test_documents_survive_supplier_deletion(tmp_path):
    data, s = make_data()
    entry = documents.create_document(data, tmp_path, "RS", rs_payload(s), now=NOW)
    data["suppliers"].clear()
    assert documents.document_path(data, tmp_path, entry["id"]) == (tmp_path / entry["file"]).resolve()
    assert documents.supplier_folder(data, tmp_path, s["id"]).name == "Voelkl Soehne GmbH"


def test_document_path_rejects_paths_outside_data_folder(tmp_path):
    data, s = make_data()
    entry = documents.create_document(data, tmp_path / "daten", "RS", rs_payload(s), now=NOW)
    (tmp_path / "geheim.pdf").write_bytes(b"x")
    entry["file"] = "../geheim.pdf"
    with pytest.raises(documents.DocumentError):
        documents.document_path(data, tmp_path / "daten", entry["id"])
    with pytest.raises(documents.DocumentError):
        documents.document_path(data, tmp_path / "daten", "unbekannt")


def test_safe_name():
    assert documents.safe_name("Völkl & Söhne GmbH") == "Voelkl Soehne GmbH"
    assert documents.safe_name('A/B\\C:D*E?"F<G>H|') == "A B C D E F G H"
    assert documents.safe_name("  ..  ") == "Hersteller"
    assert documents.safe_name("Größe Maß") == "Groesse Mass"


# ----- JS-API -----

@pytest.fixture
def api(tmp_path, monkeypatch):
    import config
    from app import Api

    monkeypatch.setenv("SOS_DASHBOARD_CONFIG_DIR", str(tmp_path / "config"))
    data_dir = tmp_path / "daten"
    data_dir.mkdir()
    config.set_data_dir(str(data_dir))
    instance = Api()
    instance.opened, instance.revealed = [], []
    import platform_utils
    monkeypatch.setattr(platform_utils, "open_path", lambda path: instance.opened.append(Path(path)))
    monkeypatch.setattr(platform_utils, "reveal_path", lambda path: instance.revealed.append(Path(path)))
    data = instance.hersteller_datei_anlegen()["data"]
    _, supplier = make_data()
    data["suppliers"].append(supplier)
    assert instance.hersteller_speichern(data)["ok"]
    instance.data_dir, instance.supplier = data_dir, supplier
    return instance


def test_api_create_document_saves_entry_and_opens_pdf(api):
    res = api.hersteller_dokument_erzeugen("RS", rs_payload(api.supplier))
    assert res["ok"] and res["opened"] and res["revision"] == 2
    year = documents.SAMPLE_RS["date"][:4]
    assert res["document"]["number"] == f"RS-{year}-0001" and res["counters"]["RS"] == {year: 1}
    pdf = api.data_dir / res["document"]["file"]
    assert pdf.is_file() and api.opened == [pdf]

    # Nach einem Neustart ist das Dokument in der Datei vorhanden.
    from app import Api
    fresh = Api()
    data = fresh.hersteller_laden()["data"]
    assert [d["number"] for d in data["documents"]] == [f"RS-{year}-0001"]
    assert data["counters"]["RS"] == {year: 1}

    second = api.hersteller_dokument_erzeugen("RS", rs_payload(api.supplier))
    assert second["document"]["number"] == f"RS-{year}-0002"

    listed = api.hersteller_dokumente(api.supplier["id"])
    assert [d["number"] for d in listed["documents"]] == [f"RS-{year}-0002", f"RS-{year}-0001"] or \
        sorted(d["number"] for d in listed["documents"]) == [f"RS-{year}-0001", f"RS-{year}-0002"]
    assert all(d["exists"] for d in listed["documents"])


def test_api_open_document_and_folder(api):
    doc = api.hersteller_dokument_erzeugen("RK", rk_payload(api.supplier))["document"]
    pdf = (api.data_dir / doc["file"]).resolve()
    api.opened.clear()
    assert api.hersteller_dokument_oeffnen(doc["id"]) == {"ok": True} and api.opened == [pdf]
    assert api.hersteller_dokumente_ordner_oeffnen(api.supplier["id"], doc["id"]) == {"ok": True} and api.revealed == [pdf]
    assert api.hersteller_dokumente_ordner_oeffnen(api.supplier["id"]) == {"ok": True} and api.opened[-1] == pdf.parent

    pdf.unlink()
    missing = api.hersteller_dokument_oeffnen(doc["id"])
    assert not missing["ok"] and "fehlt" in missing["message"]
    assert not api.hersteller_dokumente_ordner_oeffnen("unbekannt")["ok"]


def test_api_invalid_document_reports_message_and_changes_nothing(api):
    res = api.hersteller_dokument_erzeugen("RK", rk_payload(api.supplier, description=""))
    assert res == {"ok": False, "error": "document", "message": "Bitte eine Fehlerbeschreibung eintragen."}
    assert api.opened == [] and not (api.data_dir / "dokumente").exists()
    assert api.hersteller_status()["revision"] == 1


def test_api_failed_save_removes_pdf_and_keeps_number(api, monkeypatch):
    from storage import StorageError

    def boom(data):
        raise StorageError("Speichern fehlgeschlagen: Platte voll")

    monkeypatch.setattr(api._backends["hersteller"]._storage, "save", boom)
    res = api.hersteller_dokument_erzeugen("RS", rs_payload(api.supplier))
    assert not res["ok"] and res["error"] == "io"
    assert not list(api.data_dir.rglob("*.pdf")) and api.opened == []
    monkeypatch.undo()
    year = documents.SAMPLE_RS["date"][:4]
    assert api.hersteller_dokument_erzeugen("RS", rs_payload(api.supplier))["document"]["number"] == f"RS-{year}-0001"


def test_api_create_document_detects_conflict(api):
    from app import Api

    other = Api()
    other.hersteller_speichern(other.hersteller_laden()["data"])  # anderer Rechner hat gespeichert
    res = api.hersteller_dokument_erzeugen("RS", rs_payload(api.supplier))
    assert not res["ok"] and res["error"] == "conflict"
    assert not list(api.data_dir.rglob("*.pdf"))


def test_custom_address_and_contact(tmp_path):
    data, s = make_data()
    payload = rs_payload(s, addressId="__custom__", contactId="__custom__", customContactName="Frau Muster",
                         customAddress={"company": "Servicecenter X", "street": "Weg 1", "zip": "12345", "city": "Ort", "country": "Österreich"})
    entry = documents.create_document(data, tmp_path, "RS", payload, now=NOW)
    assert entry["contactName"] == "Frau Muster"
    assert entry["addressSnapshot"]["company"] == "Servicecenter X"
    assert (tmp_path / entry["file"]).is_file()
    for bad in ({"company": "", "street": "Weg 1", "city": "Ort"}, None):
        with pytest.raises(documents.DocumentError):
            documents.create_document(data, tmp_path, "RS", rs_payload(s, addressId="__custom__", customAddress=bad), now=NOW)
    with pytest.raises(documents.DocumentError):
        documents.create_document(data, tmp_path, "RS", rs_payload(s, contactId="__custom__", customContactName=" "), now=NOW)
