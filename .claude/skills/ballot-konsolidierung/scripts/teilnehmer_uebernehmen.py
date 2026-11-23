"""Einsender-Daten aller Kommentar-Excel -> Blatt "Teilnehmer" der Reconciliation-Datei.

  Organisation                 -> Spalte "Teilnehmer"
  [Titel] Vorname Name         -> Spalte "Name"
  Email                        -> Spalte "E-Mail"
  Abgabedatum (falls Datum)    -> Spalte "Teilnahmedatum"
Spalten werden über die Überschriften in Zeile 1 gefunden. Zeilen ab --first-row müssen in
Excel vorbereitet (leer) sein; befüllte Zellen werden nie überschrieben.

Aufruf:
  python -I teilnehmer_uebernehmen.py <quellordner> <recon_in.xlsx> <recon_out.xlsx>
         [--sheet "2) Teilnehmer"] [--first-row 2] [--swap 10,22]
  --swap: Dateipräfixe, bei denen Name und Vorname in der Einreichung vertauscht sind
"""
import argparse
import os
import sys
import zipfile

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ballot_quellen import parse_date, read_submission, source_files  # noqa: E402
from xlsx_xml import put_cell, rewrite_zip, sheet_xml_path  # noqa: E402

HEADERS = {"Teilnehmer": "org", "Name": "name", "E-Mail": "email", "Teilnahmedatum": "datum"}


def header_columns(recon, sheet):
    ws = openpyxl.load_workbook(recon, read_only=True)[sheet]
    cols = {}
    for j, v in enumerate(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)), 1):
        if v in HEADERS:
            cols[HEADERS[v]] = openpyxl.utils.get_column_letter(j)
    missing = set(HEADERS.values()) - set(cols)
    if missing:
        raise SystemExit(f"Überschriften fehlen in '{sheet}': {missing}")
    return cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"), ap.add_argument("recon_in"), ap.add_argument("recon_out")
    ap.add_argument("--sheet", default="2) Teilnehmer")
    ap.add_argument("--first-row", type=int, default=2)
    ap.add_argument("--swap", default="")
    a = ap.parse_args()
    swap = {s.strip() for s in a.swap.split(",") if s.strip()}
    cols = header_columns(a.recon_in, a.sheet)

    rows, hinweise = [], []
    for f in source_files(a.src):
        s = read_submission(f)
        e = s["einsender"]
        nach, vor = e.get("Name"), e.get("Vorname")
        prefix = s["file"].split("_")[0]
        if prefix in swap:
            nach, vor = vor, nach
        datum = parse_date(e.get("Abgabedatum"))
        if e.get("Abgabedatum") and not datum:
            hinweise.append(f"{s['file']}: Abgabedatum nicht lesbar: {e.get('Abgabedatum')!r}")
        if not e.get("Organisation"):
            hinweise.append(f"{s['file']}: Organisation fehlt")
        rows.append({"file": s["file"], "org": e.get("Organisation"),
                     "name": " ".join(x for x in (e.get("Titel"), vor, nach) if x) or None,
                     "email": e.get("Email"), "datum": datum})

    with zipfile.ZipFile(a.recon_in) as z:
        path = sheet_xml_path(z, a.sheet)
        xml = z.read(path).decode("utf-8")
    for i, r in enumerate(rows, a.first_row):
        for key in ("org", "name", "email", "datum"):
            if r[key] is not None:
                xml = put_cell(xml, f"{cols[key]}{i}", r[key])
    rewrite_zip(a.recon_in, a.recon_out, {path: xml})

    for i, r in enumerate(rows, a.first_row):
        print(f"{i:>3} | {r['org'] or '-'} | {r['name']} | {r['email']} | {r['datum'] or '-'} | {r['file']}")
    print("\nHinweise:" if hinweise else "", *hinweise, sep="\n  ")
    print("\nHinweis: Datumszellen brauchen in der Vorlage einen Datumsstil; Formeln (Ergebniszeile) "
          "berechnet Excel beim Öffnen neu.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
