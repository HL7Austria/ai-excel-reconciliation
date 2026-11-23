"""Unabhängige Prüfung der Kommentar-Übernahme: Reconciliation-Datei Zelle für Zelle gegen die Quellen.

Prüft: Anzahl, Reihenfolge, Inhalte C–K (exakt, nur Unicode-NFC und Leerzeichen-Zellen toleriert),
Teilnehmer (über E-Mail), lückenlose #ID, Spalten L–Q leer (mit --reconciliation-leer).

Aufruf:
  python -I kommentare_pruefen.py <quellordner> <recon.xlsx> [--sheet "4) Kommentare"]
        [--teilnehmer-sheet "2) Teilnehmer"] [--first-row 3] [--reconciliation-leer]
"""
import argparse
import os
import sys
import unicodedata

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ballot_quellen import empty, read_submission, source_files  # noqa: E402
from kommentare_uebernehmen import teilnehmer_map  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"), ap.add_argument("recon")
    ap.add_argument("--sheet", default="4) Kommentare")
    ap.add_argument("--teilnehmer-sheet", default="2) Teilnehmer")
    ap.add_argument("--first-row", type=int, default=3)
    ap.add_argument("--reconciliation-leer", action="store_true")
    a = ap.parse_args()

    tmap = teilnehmer_map(a.recon, a.teilnehmer_sheet)
    src = [(s["file"], tmap.get(s["email"]), c) for s in map(read_submission, source_files(a.src))
           for c in s["comments"]]
    ws = openpyxl.load_workbook(a.recon, data_only=True)[a.sheet]
    tgt = [r for r in ws.iter_rows(min_row=a.first_row, values_only=True) if r[0] is not None]
    print(f"Quelle: {len(src)} Kommentare, Ziel: {len(tgt)} Zeilen")
    errs = []
    for i, ((f, t, s), g) in enumerate(zip(src, tgt), 1):
        if g[0] != i:
            errs.append((i, "#ID", g[0]))
        if g[1] != t:
            errs.append((i, "Teilnehmer", g[1], t))
        if a.reconciliation_leer and any(x is not None for x in g[11:17]):
            errs.append((i, "L–Q nicht leer"))
        for j, (x, y) in enumerate(zip(s, g[2:11])):
            if x == y or (empty(x) and y is None):
                continue
            if isinstance(x, str) and isinstance(y, str) and unicodedata.normalize("NFC", x) == y:
                continue
            errs.append((i, f, "CDEFGHIJK"[j], repr(x)[:60], repr(y)[:60]))
    if len(src) != len(tgt):
        errs.append(("Anzahl", len(src), len(tgt)))
    print("Abweichungen:", len(errs))
    for e in errs[:40]:
        print("  ", e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
