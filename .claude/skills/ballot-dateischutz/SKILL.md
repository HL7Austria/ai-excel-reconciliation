---
name: ballot-dateischutz
description: Klärt VOR jeder schreibenden Arbeit in einem Ballot- oder Projektordner, welche Dateien bearbeitet werden dürfen und welche unverändert bleiben müssen, hält das per Prüfsummen-Snapshot fest und weist am Ende nach, dass geschützte Dateien unangetastet sind. Immer zuerst verwenden, bevor in einem HL7-Ballot-Ordner (Reconciliation-Datei, eingereichte Kommentar-Excel, PDFs, Vorlagen) oder einem ähnlichen Ordner mit Originaldokumenten Dateien angelegt, geändert, gespeichert, umbenannt oder gelöscht werden – auch wenn der Auftrag nur „Daten übernehmen“, „Skript schreiben“ oder „Vorlage anlegen“ lautet; ebenso, wenn die Skills ballot-konsolidierung, ballot-analyse oder ballot-github zum Einsatz kommen.
---

# Dateischutz vor der Arbeit

Eingereichte Ballot-Kommentare sind Originaldokumente; eine versehentliche Änderung (auch ein
„unverändertes“ Speichern über openpyxl) lässt sich nicht sauber rückgängig machen und
verfälscht die Nachvollziehbarkeit. Deshalb wird **vor** dem ersten Schreibzugriff geklärt und
festgehalten, was beschrieben werden darf – und **danach** nachgewiesen, dass alles andere
unverändert ist.

## 1. Regeln ermitteln (vor jedem Schreibzugriff)

In dieser Reihenfolge nachsehen und die gefundenen Regeln zusammenführen:
1. Projekt-Skills mit Schreibregeln (z. B. `ballot-schreibschutz`), `CLAUDE.md`, Projekt-Erinnerungen.
2. Ausdrückliche Anweisungen des Benutzers in der laufenden Unterhaltung – inklusive
   **einmaliger Ausnahmen** („ausnahmsweise in X schreiben“): diese gelten nur für die genannte
   Datei und den genannten Zweck und ändern die Dauerregel nicht.
3. Gibt es keine Regel: Ordnerinhalt ansehen und den Benutzer **fragen**, statt zu raten.
   Vorschlag als Standard für Ballot-Ordner: beschreibbar nur die Reconciliation-Datei
   (`00_*_Reconciliation.xlsx`) und ein Skriptordner (`scripts/**`); alles andere geschützt;
   Zwischenstände, Exporte, Backups ins Scratchpad.

Ergebnis dem Benutzer kurz bestätigen lassen, wenn es neu ermittelt oder unklar ist:
```
python -I scripts/dateischutz.py zeigen <ordner> --erlaubt "00_*_Reconciliation.xlsx" "scripts/**"
```

## 2. Snapshot anlegen
```
python -I scripts/dateischutz.py snapshot <ordner> <scratchpad>/dateischutz.json --erlaubt <muster …>
```
Snapshot liegt im Scratchpad, nie im geschützten Ordner. Bei langen Sitzungen nach jeder
bestätigten Regeländerung einen neuen Snapshot anlegen.

## 3. Während der Arbeit
- Geschützte Dateien nur lesen; für Skripte, die sie öffnen, Kopien im Scratchpad verwenden
  (vermeidet auch Konflikte mit in Excel geöffneten Dateien).
- Schreiben in erlaubte Dateien nur über eine Kopie + Abgleich (`cmp`) vor dem Zurückkopieren.
- Ist eine Änderung an einer geschützten Datei fachlich nötig: **nicht durchführen**, sondern
  dem Benutzer erklären, was und warum geändert werden müsste, und die Entscheidung abwarten.
- Neue Dateien (Vorlagen, Notizen, Exporte) nur dort, wo ein Muster es erlaubt; sonst nachfragen.

## 4. Nachweis am Ende
```
python -I scripts/dateischutz.py pruefen <ordner> <scratchpad>/dateischutz.json
```
Exit 0 = keine Verstöße. Ergebnis knapp berichten („geändert: Reconciliation-Datei; neu:
scripts/x.py; geschützte Dateien unverändert“). Bei Verstößen sofort melden, nichts
eigenmächtig zurückdrehen – der Benutzer entscheidet.

Änderungen, die der Benutzer selbst parallel macht (z. B. in Excel), erscheinen ebenfalls als
„geändert“ – bei erlaubten Dateien unkritisch, bei geschützten nachfragen statt annehmen.
