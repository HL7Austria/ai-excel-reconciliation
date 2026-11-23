# HL7-Austria-Ballot-Reconciliation – Claude-Code-Skills

Skills für [Claude Code](https://claude.com/claude-code), die die Auswertung eines HL7-Austria-Ballots
unterstützen: von den eingereichten Kommentar-Excel-Dateien über die Reconciliation-Datei bis zu
GitHub-Issues mit vorbereiteten Reconciliation-Kommentaren.

Entstanden bei der Auswertung des normativen Ballots **2026-3 „ELGA e-Diagnose R4“** (26 Einreichungen,
230 Kommentare, 169 Issues) und so verallgemeinert, dass sie für weitere Ballots wiederverwendet
werden können.

> **Keine Ballot-Daten in diesem Repo.** Einreichungen, Reconciliation-Datei und daraus abgeleitete
> Projektdaten enthalten personenbezogene Daten (Namen, E-Mail-Adressen, Telefonnummern) und sind
> über `.gitignore` ausgeschlossen. Im Repo liegen nur Werkzeuge und leere Vorlagen.

## Inhalt

| Skill | Zweck |
|---|---|
| [`ballot-dateischutz`](.claude/skills/ballot-dateischutz/SKILL.md) | Klärt **vor** jeder Schreibarbeit, welche Dateien geändert werden dürfen, legt einen Prüfsummen-Snapshot an und weist am Ende nach, dass Originaldokumente unverändert sind. |
| [`ballot-konsolidierung`](.claude/skills/ballot-konsolidierung/SKILL.md) | Überträgt Einsender → Teilnehmerliste, Abstimmungsergebnis und Kommentare (mit fortlaufender #ID) in die Reconciliation-Excel und prüft die Übernahme Zelle für Zelle. |
| [`ballot-analyse`](.claude/skills/ballot-analyse/SKILL.md) | Findet Duplikate und ähnliche Kommentare, schlägt Themengruppen zur gemeinsamen Behandlung vor, ordnet Bereiche, Kurzfassungen und Bearbeitungswellen zu. |
| [`ballot-github`](.claude/skills/ballot-github/SKILL.md) | Legt GitHub-Issues (je Gruppe bzw. Einzelkommentar) mit Labels an, ergänzt je Issue einen vorbereiteten Reconciliation-Kommentar und schreibt die Issue-URLs in die Excel-Datei zurück. |

Jeder Skill enthält eine `SKILL.md` (Anleitung für Claude, auch für Menschen lesbar), seine Skripte
unter `scripts/` und ggf. Vorlagen unter `assets/`.

## Voraussetzungen

- Claude Code (CLI, VS Code-Erweiterung oder Desktop-App)
- Python 3.10+ mit `openpyxl` (`pip install openpyxl`)
- Für `ballot-github`: Konto mit Rolle **Write** im Ziel-Repo und ein Fine-grained Token
  (nur das Ziel-Repo, Berechtigung *Issues: Read and write*) – Details in der Skill-Beschreibung
- Reconciliation-Datei und Kommentarvorlage im Format von HL7 Austria
  (Blätter „Teilnehmer“, „Abstimmung“, „Kommentare“ bzw. „Einsender“, „Abstimmung“, „Kommentare“)

## Installation

Den Ordner `.claude/skills/` entweder

- in das Projektverzeichnis des jeweiligen Ballots kopieren (Skills gelten nur dort), oder
- nach `~/.claude/skills/` kopieren (Skills gelten in allen Projekten).

Claude Code erkennt die Skills automatisch und verwendet sie, wenn eine Anfrage passt
(z. B. „übernimm die Kommentare aus allen Ballot-Excel in die Reconciliation-Datei“).

## Ablauf eines Ballots

```
1. ballot-dateischutz      Schreibregeln klären, Snapshot anlegen
2. ballot-konsolidierung   Teilnehmer → (Stimmberechtigung manuell pflegen) → Abstimmung → Kommentare → Prüfung
3. ballot-analyse          Duplikate/Gruppen vorschlagen → Gruppen bestätigen → Kurzfassungen, Bereiche, Wellen
4. ballot-github           Vorschau → Labels → Issues → Issue-URLs in Excel → Reconciliation-Kommentare
5. ballot-dateischutz      Nachweis: Einreichungen unverändert
```

Alle Skripte lassen sich auch ohne Claude direkt aufrufen; Aufruf und Parameter stehen jeweils im
Kopf des Skripts.

## Wichtige Konventionen

- **Originaldokumente bleiben unangetastet.** Geschrieben wird nur in die Reconciliation-Datei und
  in freigegebene Ordner; Zwischenstände liegen in einem temporären Verzeichnis.
- **Die Reconciliation-Datei wird nie mit openpyxl gespeichert**, weil dabei Datenvalidierungen,
  Pivot-Details und Kommentare der Vorlage verloren gehen. Die Skripte ersetzen nur die betroffenen
  XML-Teile der `.xlsx`.
- **Immer über eine Kopie arbeiten** und vor dem Zurückschreiben prüfen, ob die Datei inzwischen
  (z. B. in Excel) geändert wurde. Ist sie in Excel geöffnet, kann nicht geschrieben werden.
- **Gruppierung:** Gemeinsam behandelt werden nur Kommentare mit demselben Anliegen zur selben
  Stelle. Gleicher Text an verschiedenen Stellen und nur ähnliche Kommentare werden separat behandelt.
- **Kommentar-IDs als `K-NNN`** (nie `#NNN`, das verlinkt GitHub auf Issue NNN).
- **GitHub:** Issues und Kommentare werden nacheinander mit Pause angelegt; vorhandene werden über
  eine Marker-Zeile erkannt, sodass ein abgebrochener Lauf ohne Duplikate fortgesetzt werden kann.
  Token werden nie im Chat oder in Dateien abgelegt.

## Lokale Projektdateien (nicht im Repo)

Bei der Arbeit an einem Ballot entstehen im Projektordner zusätzlich:

| Datei | Herkunft |
|---|---|
| `00_*_Reconciliation.xlsx`, Einreichungen (`*.xlsx`, `*.pdf`) | Ballot-Daten |
| `scripts/ballot_gruppen.py` | bestätigte Gruppen – Vorlage: `ballot-analyse/assets/ballot_gruppen_vorlage.py` |
| `scripts/ballot_metadaten.py` | Repo, Ballot-ID, Kurzfassungen, Wellen – Vorlage: `ballot-github/assets/ballot_metadaten_vorlage.py` |
| `ballot-reconciliation-comment*.md` | Reconciliation-Vorlagen – aus `ballot-github/assets/` |
