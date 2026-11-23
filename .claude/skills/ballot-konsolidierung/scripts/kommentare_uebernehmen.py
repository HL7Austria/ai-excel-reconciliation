"""Kommentare (Quelle Spalten A–I) aller Kommentar-Excel -> Blatt "Kommentare" (Ziel C–K).

  Spalte A  #ID          fortlaufend über alle Kommentare
  Spalte B  Teilnehmer   aus dem Teilnehmer-Blatt, Zuordnung über E-Mail des Einsenders
  Spalten C–K            Nummer … Bewertung unverändert aus der Quelle
  Spalten L–Q            bleiben leer (Reconciliation)
Unveränderte Vorlagen-Beispielzeilen ("Beispiel - bitte überschreiben") werden ausgelassen.
Die Zieltabelle wird auf alle Zeilen erweitert, ebenso Datenvalidierungen (auch x14-Erweiterung)
und bedingte Formatierung, die bisher nur für die erste Datenzeile galten. Pivot-Caches auf der
Tabelle werden auf "beim Öffnen aktualisieren" gesetzt. Das Zielblatt muss ab --first-row leer sein.

Aufruf:
  python -I kommentare_uebernehmen.py <quellordner> <recon_in.xlsx> <recon_out.xlsx>
        [--sheet "4) Kommentare"] [--teilnehmer-sheet "2) Teilnehmer"] [--first-row 3]
"""
import argparse
import os
import re
import sys
import zipfile

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ballot_quellen import read_submission, source_files  # noqa: E402
from xlsx_xml import (cell_xml, pivot_caches_for_table, rewrite_zip,  # noqa: E402
                      set_refresh_on_load, sheet_xml_path, tables_of_sheet)

COLS = "ABCDEFGHIJKLMNOPQ"


def teilnehmer_map(recon, sheet):
    ws = openpyxl.load_workbook(recon, read_only=True, data_only=True)[sheet]
    head = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    it, ie = head.index("Teilnehmer"), head.index("E-Mail")
    out = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[it] == "Ergebnis":
            break
        if r[ie]:
            out[str(r[ie]).strip().lower()] = r[it]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"), ap.add_argument("recon_in"), ap.add_argument("recon_out")
    ap.add_argument("--sheet", default="4) Kommentare")
    ap.add_argument("--teilnehmer-sheet", default="2) Teilnehmer")
    ap.add_argument("--first-row", type=int, default=3)
    a = ap.parse_args()
    fr = a.first_row

    tmap = teilnehmer_map(a.recon_in, a.teilnehmer_sheet)
    records, report = [], []
    for s in map(read_submission, source_files(a.src)):
        t = tmap.get(s["email"])
        if t is None:
            raise SystemExit(f"Keine Teilnehmer-Zuordnung für {s['file']} ({s['email']})")
        records += [(t, c) for c in s["comments"]]
        report.append(f"{len(s['comments']):>3} | {t} | {s['file']}"
                      + (f"  (Beispielzeilen ausgelassen: {s['skipped_examples']})" if s["skipped_examples"] else ""))
    last = fr + len(records) - 1

    with zipfile.ZipFile(a.recon_in) as z:
        path = sheet_xml_path(z, a.sheet)
        xml = z.read(path).decode("utf-8")
        tables = tables_of_sheet(z, path)
        if len(tables) != 1:
            raise SystemExit(f"Erwartet genau eine Tabelle im Blatt, gefunden: {list(tables)}")
        tname, tpath = next(iter(tables.items()))
        txml = z.read(tpath).decode("utf-8")
        repl = {pc: set_refresh_on_load(z.read(pc).decode("utf-8")) for pc in pivot_caches_for_table(z, tname)}

    # Stile und Zeilenattribute der ersten (Vorlage-)Datenzeile übernehmen
    m = re.search(rf'<row r="{fr}"([^>]*)>(.*?)</row>', xml, re.S)
    if not m:
        raise SystemExit(f"Vorlagezeile {fr} fehlt im Blatt")
    row_attr = re.sub(r'\s*r="\d+"', "", m.group(1))
    styles = {c: s for c, s in re.findall(rf'<c r="([A-Z]+){fr}" s="(\d+)"', m.group(2))}
    tail = re.search(rf'<row r="{fr}".*</sheetData>', xml, re.S)
    if re.search(r"<v>|<is>|<f>", tail.group(0)):
        raise SystemExit("Zielblatt enthält ab der ersten Datenzeile bereits Daten – Abbruch")

    rows = []
    for n, (t, src) in enumerate(records, 1):
        i = fr + n - 1
        vals = [n, t] + src + [None] * (len(COLS) - 2 - len(src))
        rows.append(f'<row r="{i}"{row_attr}>' + "".join(
            cell_xml(f"{c}{i}", styles.get(c), v) for c, v in zip(COLS, vals)) + "</row>")
    xml = xml[:tail.start()] + "".join(rows) + "</sheetData>" + xml[tail.end():]
    xml = re.sub(r'<dimension ref="[^"]*"/>', f'<dimension ref="A1:Q{last}"/>', xml, count=1)
    for c in COLS:   # Validierungen / bedingte Formatierung der Vorlagezeile auf alle Zeilen ausdehnen
        xml = xml.replace(f'sqref="{c}{fr}"', f'sqref="{c}{fr}:{c}{last}"')
        xml = xml.replace(f"<xm:sqref>{c}{fr}</xm:sqref>", f"<xm:sqref>{c}{fr}:{c}{last}</xm:sqref>")
    txml = re.sub(r'ref="A(\d+):Q\d+"', lambda mm: f'ref="A{mm.group(1)}:Q{last}"', txml)
    repl[path], repl[tpath] = xml, txml
    rewrite_zip(a.recon_in, a.recon_out, repl)
    print(*report, sep="\n")
    print(f"Gesamt: {len(records)} Kommentare, Zeilen {fr}–{last}, Tabelle {tname}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
