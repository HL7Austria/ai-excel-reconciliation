"""Lesen der eingereichten Kommentar-Excel-Dateien (HL7-Austria-Kommentarvorlage).

Vorlage-Aufbau (Stand Ballot 2026-3; Blattnamen werden per Stichwort gesucht):
  "… Einsender"   Schlüssel/Wert-Zeilen: Organisation, Name, Vorname, Titel, Email, Abgabedatum, HL7 Mitglied
  "… Abstimmung"  Zeile mit Position 1 → Spalte 3 = Stimme
  "… Kommentare"  ab Zeile 3, Spalten A–I: Nummer, Bezugnehmend auf, Seite-Nr, Zeilen-Nr, Element,
                  Beschreibung, Vorgeschlagene Änderung, Begründung/Kommentar/Frage, Bewertung
Alle Dateien werden nur lesend geöffnet.
"""
import datetime as dt
import glob
import os
import re
import unicodedata

import openpyxl

TEMPLATE_EXAMPLE = "Beispiel - bitte überschreiben"   # unveränderte Beispielzeile der Vorlage
VALID_VOTES = {"Zustimmung", "Zustimmung mit Kommentar", "Stimmenthaltung", "Ablehnung mit Kommentar"}
MONATE = {"jänner": 1, "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6, "juli": 7,
          "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12}


def norm(v):
    if isinstance(v, str):
        v = unicodedata.normalize("NFC", v).strip()
        return v or None
    return v


def empty(v):
    return v is None or (isinstance(v, str) and not v.strip())


def source_files(src_dir, exclude_prefix="00_"):
    """Alle Kommentar-Excel-Dateien (ohne Reconciliation-Datei und Office-Sperrdateien)."""
    return sorted(f for f in glob.glob(os.path.join(src_dir, "*.xlsx"))
                  if not os.path.basename(f).startswith((exclude_prefix, "~$")))


def sheet_by_keyword(wb, keyword):
    for n in wb.sheetnames:
        if keyword.lower() in n.lower():
            return wb[n]
    raise KeyError(f"Kein Blatt mit '{keyword}' in {wb.sheetnames}")


def read_kv(ws):
    """Schlüssel/Wert-Paare; Spaltenposition egal (leere Zellen werden übersprungen)."""
    out = {}
    for row in ws.iter_rows(values_only=True):
        v = [x for x in row if x is not None]
        if v and isinstance(v[0], str):
            out[norm(v[0])] = norm(v[1]) if len(v) > 1 else None
    return out


def parse_date(v):
    """datetime/date oder Text wie '19/11/2026', '19.11.2026', '19. November 2026'."""
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        m = re.fullmatch(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", v.strip())
        if m:
            return dt.date(int(m[3]), int(m[2]), int(m[1]))
        m = re.fullmatch(r"(\d{1,2})\.\s*(\w+)\s+(\d{4})", v.strip())
        if m and m[2].lower() in MONATE:
            return dt.date(int(m[3]), MONATE[m[2].lower()], int(m[1]))
    return None


def read_submission(path):
    """Liest Einsender, Stimme und Kommentare einer Einreichung."""
    wb = openpyxl.load_workbook(path, data_only=True)
    eins = read_kv(sheet_by_keyword(wb, "einsender"))
    vote = None
    for row in sheet_by_keyword(wb, "abstimmung").iter_rows(values_only=True):
        v = [x for x in row if x is not None]
        if len(v) > 2 and v[0] == 1:
            vote = norm(v[2])
    if vote not in VALID_VOTES:          # z. B. Hinweistext "← Bitte tragen sie hier …"
        vote = None
    comments, skipped = [], []
    for row in sheet_by_keyword(wb, "kommentare").iter_rows(min_row=3, max_col=9, values_only=True):
        r = list(row) + [None] * (9 - len(row))
        if not any(not empty(x) for x in r[2:9]):       # A/B sind in der Vorlage vorbelegt
            continue
        if isinstance(r[5], str) and r[5].strip() == TEMPLATE_EXAMPLE:
            skipped.append(r[0])
            continue
        # Texte unverändert übernehmen (nur Unicode-NFC); reine Leerzeichen-Zellen -> leer
        comments.append([None if empty(x) else (unicodedata.normalize("NFC", x) if isinstance(x, str) else x)
                         for x in r])
    wb.close()
    return {
        "file": unicodedata.normalize("NFC", os.path.basename(path)),
        "email": (eins.get("Email") or "").strip().lower(),
        "einsender": eins,
        "vote": vote,
        "comments": comments,
        "skipped_examples": skipped,
    }
