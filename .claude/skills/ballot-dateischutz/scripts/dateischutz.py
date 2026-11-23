"""Dateischutz: Prüfsummen-Snapshot eines Ordners vor der Arbeit, Abgleich danach.

  snapshot <ordner> <snapshot.json> [--erlaubt MUSTER ...]
      Hält Größe + SHA-256 aller Dateien fest und speichert die Liste der erlaubten Muster
      (glob relativ zum Ordner, z. B. "00_*_Reconciliation.xlsx" "scripts/**").
  pruefen  <ordner> <snapshot.json>
      Meldet geänderte, neue und gelöschte Dateien und ob sie unter ein erlaubtes Muster fallen.
      Exit-Code 1, wenn eine geschützte Datei verändert, gelöscht oder unerlaubt neu angelegt wurde.
  zeigen   <ordner> [--erlaubt MUSTER ...]
      Listet, welche Dateien nach den Mustern beschreibbar bzw. geschützt sind (vor dem Start zur Bestätigung).

Ausgeschlossen werden Office-Sperrdateien (~$*), __pycache__ und .git. Snapshot ins Scratchpad legen,
nicht in den geschützten Ordner.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import sys

IGNORE_DIRS = {"__pycache__", ".git"}


def files(root):
    for d, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in IGNORE_DIRS]
        for f in fs:
            if f.startswith("~$"):
                continue
            p = os.path.join(d, f)
            yield os.path.relpath(p, root).replace("\\", "/"), p


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def erlaubt(rel, muster):
    return any(fnmatch.fnmatchcase(rel, m) or (m.endswith("/**") and rel.startswith(m[:-2])) for m in muster)


def cmd_snapshot(root, out, muster):
    data = {"ordner": os.path.abspath(root), "erlaubt": muster,
            "dateien": {rel: {"size": os.path.getsize(p), "sha256": sha(p)} for rel, p in files(root)}}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    n_s = sum(1 for r in data["dateien"] if not erlaubt(r, muster))
    print(f"Snapshot: {len(data['dateien'])} Dateien, davon {n_s} geschützt -> {out}")


def cmd_zeigen(root, muster):
    rels = sorted(r for r, _ in files(root))
    print("BESCHREIBBAR:")
    for r in rels:
        if erlaubt(r, muster):
            print("  ", r)
    print("GESCHÜTZT (dürfen nicht verändert werden):")
    for r in rels:
        if not erlaubt(r, muster):
            print("  ", r)
    print("Neue Dateien sind nur erlaubt, wenn sie einem Muster entsprechen:", muster or "(keine)")


def cmd_pruefen(root, snap):
    data = json.load(open(snap, encoding="utf-8"))
    muster, alt = data["erlaubt"], data["dateien"]
    neu = {rel: p for rel, p in files(root)}
    verstoss, ok = [], []
    for rel, info in alt.items():
        if rel not in neu:
            (ok if erlaubt(rel, muster) else verstoss).append(f"gelöscht:  {rel}")
        elif os.path.getsize(neu[rel]) != info["size"] or sha(neu[rel]) != info["sha256"]:
            (ok if erlaubt(rel, muster) else verstoss).append(f"geändert:  {rel}")
    for rel in sorted(set(neu) - set(alt)):
        (ok if erlaubt(rel, muster) else verstoss).append(f"neu:       {rel}")
    print(f"Geprüft: {len(alt)} Dateien im Snapshot, {len(neu)} aktuell")
    print("Erlaubte Änderungen:", *(ok or ["keine"]), sep="\n  ")
    print("VERSTÖSSE:" if verstoss else "Verstöße: keine", *verstoss, sep="\n  ")
    sys.exit(1 if verstoss else 0)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["snapshot", "pruefen", "zeigen"])
    ap.add_argument("ordner")
    ap.add_argument("snapshot", nargs="?")
    ap.add_argument("--erlaubt", nargs="*", default=[])
    a = ap.parse_args()
    if a.cmd == "snapshot":
        cmd_snapshot(a.ordner, a.snapshot, a.erlaubt)
    elif a.cmd == "pruefen":
        cmd_pruefen(a.ordner, a.snapshot)
    else:
        cmd_zeigen(a.ordner, a.erlaubt)
