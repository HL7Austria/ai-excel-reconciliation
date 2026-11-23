---
name: ballot-analyse
description: Analysiert die Kommentare eines HL7-Austria-Ballots in der Reconciliation-Excel – findet Duplikate, schlägt Themengruppen für gemeinsame Behandlung vor, ordnet Bereiche, Kurzfassungen und Bearbeitungswellen zu und hält bestätigte Gruppen als ballot_gruppen.py fest. Verwenden bei Fragen wie „gibt es Duplikate?“, „welche Kommentare können gemeinsam behandelt werden?“, „in welcher Reihenfolge abarbeiten?“, „Gruppen für GitHub-Issues“, oder wenn Ballot-Kommentare thematisch sortiert, priorisiert oder für Issues vorbereitet werden sollen.
---

# Ballot-Analyse (HL7 Austria)

Aus den konsolidierten Kommentaren (Blatt „Kommentare“ der Reconciliation-Datei, siehe Skill
`ballot-konsolidierung`) werden Duplikate, Gruppen, Bereiche und Prioritäten abgeleitet.
Nur lesen – Ergebnisse werden im Chat vorgeschlagen und erst nach Bestätigung festgehalten.
Bevor etwas festgehalten wird (z. B. `ballot_gruppen.py`), mit Skill `ballot-dateischutz`
klären, wo geschrieben werden darf.

## Gruppierungsregeln (vom Benutzer festgelegt – verbindlich)

- **Gemeinsam behandelt** werden nur Kommentare, die **dasselbe Anliegen zur selben Stelle**
  vorbringen – typischerweise von verschiedenen Einreichern (z. B. zwei Organisationen mit fast
  wortgleichen Kommentaren, drei Einreicher zur selben Invariante).
- **Nicht zusammenführen**, sondern separat behandeln:
  - gleicher Text, aber für **verschiedene Stellen/Elemente/Kapitel** (ein Einreicher kopiert
    seinen Kommentar auf mehrere Profile),
  - **ähnliche, aber inhaltlich verschiedene** Kommentare (z. B. $delete vs. $entered-in-error,
    neue vs. weggefallene Codes).
  Solche Fälle höchstens zur Information auflisten – keine gemeinsame Lösung, keine Querverweise.
- Grenzfälle (Teilüberschneidung, gegensätzliche Positionen zum selben Thema, „siehe oben“-
  Kommentare, zwei Aspekte in einer Gruppe) **einzeln zur Entscheidung vorlegen**.

## Ablauf

1. **Aktuellen Stand kopieren** (Scratchpad) und Kommentare exportieren:
   `python -I scripts/kommentare_export.py <recon.xlsx> <scratch>/kommentare.txt`
   Die Datei in Abschnitten lesen (≈100 Zeilen je Read) – alle Kommentare inhaltlich lesen,
   nicht nur Kennzahlen auswerten.
2. **Kandidaten maschinell suchen:**
   `python -I scripts/duplikate_finden.py <recon.xlsx>`
   Exakte Duplikate zeigen Seite/Zeile/Element – daran erkennt man „gleicher Text, andere Stelle“.
3. **Themengruppen bilden** (über das maschinelle Ergebnis hinaus, aus dem Lesen): je Gruppe
   ID (G01…), Titel, Kommentar-IDs, schwerste Bewertung (Rang: NEG-S > NEG-G > Z-F > Z-V >
   Z-K > Z-T > K) und ein Hinweis bei Grenzfällen. Darstellung als Tabellen nach Bereich
   (Leitfaden, Fachlicher Rahmen, Profile, Operationen, Terminologie), am Ende eine
   nummerierte Liste der offenen Einzelentscheidungen.
4. **Bestätigung einholen**, dann festhalten in `<projekt>/scripts/ballot_gruppen.py`
   (Format: `assets/ballot_gruppen_vorlage.py`, inkl. `check()` gegen Mehrfachzuordnung).
   Eine Projekt-Erinnerung/Notiz mit Datum und Entscheidungen anlegen.
5. **Kurzfassungen, Bereiche, Wellen** (falls GitHub-Issues folgen – Skill `ballot-github`):
   für *jeden* Kommentar eine Kurzfassung (≤ ~60 Zeichen, sachlich, beschreibt das Anliegen)
   und einen Bereich; je Gruppe Anliegen (1–2 Sätze) + betroffene Stelle. Format:
   `ballot-github/assets/ballot_metadaten_vorlage.py`.

## Bearbeitungsreihenfolge (Wellen) – Empfehlung

Kriterien: Was verhindert die Annahme (NEG-Kommentare hinter Ablehnungen) und welche
Entscheidung determiniert andere?
1. **Grundsatzentscheidungen** (Fachlicher Rahmen, negativ): Konzept/Umfang, Rollen/Rechte,
   Löschkonzept, Abstimmung mit Stakeholdern – früh starten, sie brauchen Zeit.
2. **Datenmodell/Semantik** (Profile/Operationen, negativ): Statuslogik, leere Listen,
   Verantwortung/Herkunft – fachlich zusammenhängende Einzel-Issues gemeinsam *besprechen*,
   aber getrennt *entscheiden*.
3. **Technische Grundlagen mit Außenwirkung**: feste Abhängigkeitsversionen, Terminologie-
   Versionen, Fehlerkatalog.
4. **Fragen und Vorschläge** (Z-F vor Z-V/Z-K) – parallelisierbar.
5. **Tippfehler/Kosmetik** – gesammelt in einem PR zum Schluss.
Als Labels `welle-1…5` abbilden (flexibler als Anlegereihenfolge).

## Bericht
Zahlen zuerst (wie viele Gruppen/Kommentare/Einzelkommentare), dann Tabellen, dann offene
Entscheidungen. Kommentar-IDs immer als K-NNN schreiben (GitHub-sicher).
