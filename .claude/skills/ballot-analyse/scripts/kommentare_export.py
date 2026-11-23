"""Exportiert alle Kommentare der Reconciliation-Datei als kompakte Textdatei zum Lesen.

Eine Zeile je Kommentar:  #ID [Teilnehmer] S:Seite | Z:Zeile | E:Element | B:Beschreibung | Ä:Änderung | G:Begründung | Bewertung
Lange Felder werden gekürzt (--len). Ist die Beschreibung leer, steht der Inhalt oft in der Begründung –
deshalb wird die Begründung immer mit ausgegeben.

Aufruf: python -I kommentare_export.py <recon.xlsx> <out.txt> [--sheet "4) Kommentare"] [--len 330]
Danach die Datei in Abschnitten lesen (Read mit offset/limit), nicht auf einmal.
"""
import argparse
import re
import sys

import openpyxl


def c(s, n):
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recon"), ap.add_argument("out")
    ap.add_argument("--sheet", default="4) Kommentare")
    ap.add_argument("--first-row", type=int, default=3)
    ap.add_argument("--len", type=int, default=330)
    a = ap.parse_args()
    ws = openpyxl.load_workbook(a.recon, read_only=True, data_only=True)[a.sheet]
    n = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for r in ws.iter_rows(min_row=a.first_row, values_only=True):
            if r[0] is None:
                continue
            n += 1
            f.write(f"#{r[0]} [{c(r[1], 25)}] S:{c(r[4], 90)} | Z:{c(r[5], 40)} | E:{c(r[6], 60)} | "
                    f"B:{c(r[7], a.len)} | Ä:{c(r[8], 160)} | G:{c(r[9], 200)} | {c(r[10], 8)}\n")
    print(f"{n} Kommentare -> {a.out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
