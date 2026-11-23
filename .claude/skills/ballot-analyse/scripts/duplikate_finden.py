"""Findet exakte und ähnliche Kommentare (Kandidaten – die Entscheidung trifft der Mensch).

1. Exakte Duplikate: gleiche Beschreibung + Änderung + Begründung (Satzzeichen/Groß-Klein ignoriert)
   – inkl. Seite/Zeile/Element, damit „gleicher Text an verschiedenen Stellen“ sichtbar wird.
2. Ähnliche Paare: Wort-Jaccard (Wörter ≥ 3 Zeichen) über Beschreibung+Änderung+Begründung ≥ --ganz
   oder nur Beschreibung ≥ --beschr. Schnell (keine difflib – die ist bei ~200 Kommentaren zu langsam).

Aufruf: python -I duplikate_finden.py <recon.xlsx> [--sheet "4) Kommentare"] [--ganz 0.4] [--beschr 0.5]
"""
import argparse
import itertools
import re
import sys

import openpyxl


def toks(s):
    return {w for w in re.findall(r"\w+", str(s or "").lower()) if len(w) > 2}


def jac(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def short(s, n=150):
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recon")
    ap.add_argument("--sheet", default="4) Kommentare")
    ap.add_argument("--first-row", type=int, default=3)
    ap.add_argument("--ganz", type=float, default=0.4)
    ap.add_argument("--beschr", type=float, default=0.5)
    a = ap.parse_args()
    ws = openpyxl.load_workbook(a.recon, read_only=True, data_only=True)[a.sheet]
    rows = [r for r in ws.iter_rows(min_row=a.first_row, values_only=True) if r[0] is not None]
    full = lambda r: " ".join(str(x or "") for x in r[7:10])  # noqa: E731

    groups = {}
    for r in rows:
        groups.setdefault(re.sub(r"\W+", "", full(r).lower()), []).append(r)
    exact = [g for k, g in groups.items() if k and len(g) > 1]
    print(f"EXAKTE DUPLIKATE: {len(exact)}")
    for g in exact:
        print(f"  Text: {short(g[0][7], 120)}")
        for r in g:
            print(f"    #{r[0]} {r[1]} (Ref {r[2]}) | Seite: {short(r[4], 70)} | Zeile: {r[5]} | Element: {short(r[6], 50)}")

    T = {r[0]: toks(full(r)) for r in rows}
    B = {r[0]: toks(r[7]) for r in rows}
    pairs = []
    for x, y in itertools.combinations(rows, 2):
        if len(T[x[0]]) < 6 or len(T[y[0]]) < 6:
            continue
        jf, jb = jac(T[x[0]], T[y[0]]), jac(B[x[0]], B[y[0]])
        if jf >= a.ganz or (jb >= a.beschr and len(B[x[0]]) >= 6):
            pairs.append((max(jf, jb), jf, jb, x, y))
    pairs.sort(key=lambda p: -p[0])
    print(f"\nÄHNLICHE PAARE: {len(pairs)}")
    for _, jf, jb, x, y in pairs:
        print(f"--- gesamt {jf:.2f} / Beschr {jb:.2f}: #{x[0]} {x[1]} (Ref {x[2]}) <-> #{y[0]} {y[1]} (Ref {y[2]})")
        print("   A:", short(x[7]))
        print("   B:", short(y[7]))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
