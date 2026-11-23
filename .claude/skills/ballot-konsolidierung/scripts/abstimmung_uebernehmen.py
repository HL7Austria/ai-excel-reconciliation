"""Allgemeines Abstimmungsergebnis (Position 1) aller Kommentar-Excel -> Blatt "Abstimmung".

  Stimme der Einreichung                 -> Spalte "Zustimmung / Ablehnung"
  Teilnehmer aus dem Teilnehmer-Blatt    -> Spalte "Teilnehmer"   (Zuordnung über E-Mail)
  Stimmberechtigt Ja / Nein              -> Spalte "Mitglied"     ("Mitglied" / "Kein Mitglied")
Reihenfolge = Reihenfolge der Teilnehmerliste. Zieltabellen-Überschriften in --header-row.
Bereits befüllte Zellen werden nur mit --overwrite ersetzt (z. B. Beispielzeile des Benutzers).
Pivot-Caches auf der Abstimmungstabelle werden auf "beim Öffnen aktualisieren" gesetzt.

Aufruf:
  python -I abstimmung_uebernehmen.py <quellordner> <recon_in.xlsx> <recon_out.xlsx>
        [--sheet "3) Abstimmung"] [--teilnehmer-sheet "2) Teilnehmer"] [--header-row 2] [--overwrite]
"""
import argparse
import os
import sys
import zipfile

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ballot_quellen import read_submission, source_files  # noqa: E402
from xlsx_xml import (pivot_caches_for_table, put_cell, rewrite_zip,  # noqa: E402
                      set_refresh_on_load, sheet_xml_path, tables_of_sheet)


def find_cols(ws, row, names):
    cols = {}
    for j, v in enumerate(next(ws.iter_rows(min_row=row, max_row=row, values_only=True)), 1):
        if v in names:
            cols[v] = openpyxl.utils.get_column_letter(j)
    if set(names) - set(cols):
        raise SystemExit(f"Überschriften fehlen in '{ws.title}': {set(names) - set(cols)}")
    return cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"), ap.add_argument("recon_in"), ap.add_argument("recon_out")
    ap.add_argument("--sheet", default="3) Abstimmung")
    ap.add_argument("--teilnehmer-sheet", default="2) Teilnehmer")
    ap.add_argument("--header-row", type=int, default=2)
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()

    wb = openpyxl.load_workbook(a.recon_in, read_only=True, data_only=True)
    tws = wb[a.teilnehmer_sheet]
    tcols = find_cols(tws, 1, ["Teilnehmer", "E-Mail", "Stimmberechtigt"])
    idx = {k: openpyxl.utils.column_index_from_string(v) - 1 for k, v in tcols.items()}
    teilnehmer = []
    for r in tws.iter_rows(min_row=2, values_only=True):
        t, e, s = r[idx["Teilnehmer"]], r[idx["E-Mail"]], r[idx["Stimmberechtigt"]]
        if t == "Ergebnis":
            break
        if t or e:
            teilnehmer.append((t, (e or "").strip().lower(), s))
    acols = find_cols(wb[a.sheet], a.header_row, ["Zustimmung / Ablehnung", "Teilnehmer", "Mitglied"])
    wb.close()

    votes = {s["email"]: s for s in map(read_submission, source_files(a.src))}
    with zipfile.ZipFile(a.recon_in) as z:
        path = sheet_xml_path(z, a.sheet)
        xml = z.read(path).decode("utf-8")
        repl = {}
        for tname in tables_of_sheet(z, path):
            for pc in pivot_caches_for_table(z, tname):
                repl[pc] = set_refresh_on_load(z.read(pc).decode("utf-8"))

    report = []
    for i, (t, email, stimm) in enumerate(teilnehmer, a.header_row + 1):
        s = votes.pop(email, None)
        mitglied = {"Ja": "Mitglied", "Nein": "Kein Mitglied"}.get(stimm)
        for col, val in ((acols["Zustimmung / Ablehnung"], s and s["vote"]),
                         (acols["Teilnehmer"], t), (acols["Mitglied"], mitglied)):
            if val:
                xml = put_cell(xml, f"{col}{i}", val, overwrite=a.overwrite)
        report.append(f"{i:>3} | {t} | {(s and s['vote']) or '(keine Stimme)'} | {mitglied} | "
                      f"{s['file'] if s else 'KEINE QUELLDATEI'}")
    repl[path] = xml
    rewrite_zip(a.recon_in, a.recon_out, repl)
    print(*report, sep="\n")
    if votes:
        print("Quelldateien ohne Teilnehmer-Eintrag:", [v["file"] for v in votes.values()])


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
