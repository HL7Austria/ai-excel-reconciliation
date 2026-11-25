"""Projekt-Konfiguration und Metadaten für die GitHub-Issues eines Ballots.

Als <projekt>/scripts/ballot_metadaten.py ablegen (neben ballot_gruppen.py und den Skripten).
KURZ:          #ID -> (Bereich, Kurzfassung)  – Kurzfassung = Summary-Zeile bzw. Titel bei Einzel-Issues
GRUPPEN_META:  Gruppe -> (Bereich, Anliegen, Betroffene Stelle)
EXTRA:         Einreichungen ohne Kommentarformular (E-Mail/PDF) – PDF wird nicht ins Issue übernommen
"""

# ---------------------------------------------------------------- Projekt
REPO = "HL7Austria/<Repo-Name>"           # Ziel-Repo
BALLOT_ID = "JJJJ-N"                      # z. B. "2026-3"; steht in Marker-Zeilen und im Label
KOMMENTARE_SHEET = "4) Kommentare"        # Blatt der Reconciliation-Datei
BALLOT_LABEL = f"ballot-{BALLOT_ID}"
# Teilnehmer in Issues nur als Kennung (Nr aus Spalte "Nr" des Teilnehmer-Blatts); None = Klarnamen
PARTICIPANT_ID = "ballot-participant-{nr}"
TEILNEHMER_SHEET = "2) Teilnehmer"

BEREICHE = {
    "L": "Leitfaden",
    "R": "Fachlicher Rahmen",
    "P": "Profile",
    "O": "Operationen",
    "T": "Terminologie",
}

# Bewertung (Präfix in Spalte "Bewertung") -> Label im Repo (vorher im Repo nachsehen!)
BEWERTUNG_LABEL = {
    "(NEG-S)": "negativ - schwerwiegend",
    "(NEG-G)": "negativ - geringfügig",
    "(Z-K)": "Zustimmung mit Kommentar",
    "(Z-V)": "Zustimmung mit Vorschlag",
    "(Z-F)": "Zustimmung mit Frage",
    "(Z-T)": "Zustimmung - Tippfehler",
    "(K)": "Kommentar",
}
BEWERTUNG_RANG = ["(NEG-S)", "(NEG-G)", "(Z-F)", "(Z-V)", "(Z-K)", "(Z-T)", "(K)"]

# ---------------------------------------------------------------- Inhalte (für JEDEN Kommentar)
KURZ = {
    # 1: ("L", "<Kurzfassung, ≤ ~60 Zeichen, ohne Hinweis auf den Einreicher>"),
}

GRUPPEN_META = {
    # "G01": ("L", "<Anliegen, 1–2 Sätze>", "<Betroffene Stelle, z. B. Seite des IG>"),
}

# Besser: E-Mail-/PDF-Einreicher in die Teilnehmerliste und den Kommentar ins Kommentar-Blatt
# eintragen – dann bleibt EXTRA leer. Sonst Teilnehmer nur als Kennung, keine Namen.
EXTRA = [
    # {"id": "X01", "bereich": "R", "teilnehmer": "ballot-participant-<Nr>",
    #  "eingang": "E-Mail vom TT.MM.JJJJ an <Adresse>", "bewertung": "(Z-F) Zustimmung mit Frage",
    #  "kurz": "<Kurzfassung>", "text": "<Kernfragestellung wörtlich>"},
]

# ---------------------------------------------------------------- Bearbeitungswellen
WELLE_EXPLIZIT = {
    # "G06": 1, "K-089": 2, "G01": 3, "K-016": 5, …
}
WELLE_LABEL = {n: f"welle-{n}" for n in range(1, 6)}


def welle(key, bereich, bewertung):
    """Explizit > NEG nach Bereich (R→1, P/O→2, sonst 3) > Tippfehler→5 > sonst 4."""
    if key in WELLE_EXPLIZIT:
        return WELLE_EXPLIZIT[key]
    if bewertung in ("(NEG-S)", "(NEG-G)"):
        return {"R": 1, "P": 2, "O": 2}.get(bereich, 3)
    if bewertung == "(Z-T)":
        return 5
    return 4
