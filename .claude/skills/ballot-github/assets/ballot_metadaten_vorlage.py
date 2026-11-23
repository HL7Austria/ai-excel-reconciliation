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
    1: ("L", "Auf feste AT-Core-Version aufbauen"),
    2: ("P", "Unklar, warum manche optionalen Elemente entfernt wurden"),
    # …
}

GRUPPEN_META = {
    "G01": ("L", "Der IG referenziert … mit #current statt einer festen Version.", "dependencies.html"),
    # …
}

EXTRA = [
    # {"id": "X01", "bereich": "R", "teilnehmer": "<Organisation>", "einsender": "<Name, Funktion>",
    #  "eingang": "E-Mail vom TT.MM.JJJJ an tc-fhir@hl7.at", "bewertung": "(Z-F) Zustimmung mit Frage",
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
