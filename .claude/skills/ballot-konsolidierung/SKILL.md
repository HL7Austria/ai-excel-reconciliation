---
name: ballot-konsolidierung
description: Konsolidiert eingereichte HL7-Austria-Ballot-Kommentardateien (Excel-Kommentarvorlage mit Blättern Einsender/Abstimmung/Kommentare) in die Reconciliation-Excel-Datei – Teilnehmerliste, Abstimmungsergebnis, Kommentare mit fortlaufender #ID – und prüft die Übernahme Zelle für Zelle. Verwenden, sobald Ballot-Einreichungen, Kommentar-Excel, „Einsender“, „Teilnehmer“, „Abstimmung“, „Kommentare übernehmen“ oder eine *_Reconciliation.xlsx im Spiel sind, auch wenn nur ein Teilschritt (z. B. nur Teilnehmer oder nur Abstimmung) verlangt wird.
---

# Ballot-Konsolidierung (HL7 Austria)

Überträgt die Inhalte der einzelnen Kommentar-Excel-Dateien eines Ballots in die
Reconciliation-Datei und prüft das Ergebnis. Die Skripte liegen in `scripts/` dieses Skills und
werden mit `python -I <skill>/scripts/<skript>.py …` direkt aufgerufen.

## Grundregeln (aus der Praxis – bitte einhalten)

- **Zuerst Skill `ballot-dateischutz`:** erlaubte/geschützte Dateien klären und Snapshot
  anlegen; am Ende Nachweis, dass Einreichungen unverändert sind. In Ballot-Ordnern darf
  typischerweise nur die Reconciliation-Datei geändert werden; Einreichungen sind
  Originaldokumente. Hilfsdateien und Zwischenstände ins Scratchpad.
- **Nie mit openpyxl speichern.** openpyxl entfernt beim Speichern x14-Datenvalidierungen,
  Pivot-Details und Kommentare der Vorlage. Die Skripte ersetzen nur die betroffenen XML-Teile
  im ZIP (`xlsx_xml.py`). openpyxl nur zum *Lesen* verwenden.
- **Immer über eine Kopie arbeiten:** Reconciliation-Datei ins Scratchpad kopieren → Skript
  schreibt `recon_out.xlsx` → prüfen → vor dem Zurückkopieren mit `cmp` sicherstellen, dass das
  Original seit der Kopie unverändert ist (der Benutzer arbeitet oft parallel in Excel) →
  zurückkopieren → nochmals `cmp`.
- **„Permission denied“ / „Device or resource busy“** heißt fast immer: Datei ist in Excel
  geöffnet. Lesen geht über `cp` ins Scratchpad; zum Schreiben den Benutzer bitten, Excel zu
  schließen – nicht versuchen, die Sperre zu umgehen.
- **Nichts überschreiben.** Die Skripte brechen ab, wenn Zielzellen schon befüllt sind
  (Ausnahme: `--overwrite` nach Rückfrage, z. B. für eine Beispielzeile des Benutzers).
- **Zuordnung über E-Mail**, nicht über Zeilenposition – der Benutzer ändert die
  Teilnehmerliste (Namen von Privatpersonen, Stimmberechtigt) zwischendurch.
- **Vor jedem Schritt den aktuellen Stand neu kopieren** und bei abweichenden Zählungen
  (z. B. 232 → 230 Kommentare) nachfragen bzw. prüfen, ob IDs noch dieselben Inhalte haben.

## Ablauf

### 1. Bestandsaufnahme
Struktur der Reconciliation-Datei ansehen (Blattnamen, Überschriften, Tabellen) und alle
Einreichungen lesen (Einsender, Stimme, Anzahl Kommentare). PDF-/E-Mail-Einreichungen haben
kein Formular – erfassen und dem Benutzer melden, nicht raten.

### 2. Teilnehmer – `teilnehmer_uebernehmen.py`
```
python -I scripts/teilnehmer_uebernehmen.py <quellordner> <recon_in> <recon_out> [--swap 10,22]
```
Organisation → Teilnehmer, „[Titel] Vorname Name“ → Name, Email → E-Mail, Abgabedatum →
Teilnahmedatum (Text wie „19/11/2026“ oder „19. November 2026“ wird umgewandelt).
Vorher prüfen und melden: vertauschte Name/Vorname (am E-Mail-Präfix erkennbar → `--swap`
mit Dateipräfixen), fehlende Organisation, unplausible Daten (z. B. Vorlagenwert 2011),
doppelte Personen mit verschiedenen Rollen. Spaltennamen werden über die Kopfzeile gefunden.

### 3. Abstimmung – `abstimmung_uebernehmen.py`
Setzt voraus, dass der Benutzer „Stimmberechtigt“ in der Teilnehmerliste gepflegt hat.
Stimme (Position 1) → „Zustimmung / Ablehnung“, Teilnehmer → „Teilnehmer“, Stimmberechtigt
Ja/Nein → „Mitglied“/„Kein Mitglied“. Hinweistexte der Vorlage statt Stimme = keine Stimme
(melden). Pivot-Caches der Tabelle werden beim Öffnen aktualisiert.

### 4. Kommentare – `kommentare_uebernehmen.py`
Quelle A–I → Ziel C–K, Teilnehmer → B, #ID fortlaufend → A, L–Q leer. Unveränderte
Vorlagen-Beispielzeilen („Beispiel - bitte überschreiben“) werden ausgelassen und gemeldet;
echte Kommentare, die nur zusätzlich den Vorlagen-Hinweistext enthalten, bleiben drin.
Tabelle, Datenvalidierungen (inkl. x14) und bedingte Formatierung werden auf alle Zeilen
erweitert. Zusätzlich melden: Einreichungen mit eigenen Zusatzblättern (können weitere
Kommentare enthalten) und Einreichungen, die die Vorlage komplett gefüllt haben.

### 5. Prüfung – `kommentare_pruefen.py`
```
python -I scripts/kommentare_pruefen.py <quellordner> <recon.xlsx> --reconciliation-leer
```
Unabhängiger Abgleich Zelle für Zelle (Anzahl, Reihenfolge, Inhalte, Teilnehmer, #ID).
Auf Nachfrage „sind Kopierfehler passiert?“ genau dieses Skript gegen die *gespeicherte* Datei
laufen lassen und das Ergebnis mit Zahlen berichten.

## Bericht an den Benutzer
Kurz: was übernommen wurde (Anzahl, Zeilenbereich), welche Zellen bewusst leer blieben, und
eine Liste der Auffälligkeiten aus den Quelldaten (vertauschte Namen, fehlende Angaben, Text-
statt Datumswerte, Beispielzeilen, fehlende Stimmen, Nicht-Excel-Einreichungen).
