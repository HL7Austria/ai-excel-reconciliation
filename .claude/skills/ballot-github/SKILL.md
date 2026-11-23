---
name: ballot-github
description: Legt für einen HL7-Austria-Ballot GitHub-Issues aus den (gruppierten) Kommentaren der Reconciliation-Excel an – mit eingeklappten Originalkommentaren, Labels für Ballot/Bewertung/Bereich/Welle, vorbereiteten Reconciliation-Kommentaren je Issue und Rückschreiben der Issue-URLs in die Excel-Datei; inklusive Token-/Rechteprüfung, Rate-Limit-Schutz und Duplikatschutz. Verwenden, sobald Ballot-Kommentare als GitHub-Issues angelegt, Issue- oder Reconciliation-Vorlagen erstellt, Labels für einen Ballot angelegt oder Issue-Nummern in die Reconciliation-Datei übernommen werden sollen – auch bei Fragen wie „welche Rechte braucht das Token?“ oder „blockiert GitHub das?“.
---

# Ballot → GitHub-Issues (HL7 Austria)

Voraussetzung: konsolidierte Kommentare (Skill `ballot-konsolidierung`) und bestätigte Gruppen
(Skill `ballot-analyse`). Ergebnis: je Gruppe ein Issue, je übrigem Kommentar ein Issue, je
E-Mail-/PDF-Einreichung ein Issue; in jedem Issue ein vorbereiteter Reconciliation-Kommentar;
Issue-URL je Kommentar in der Excel-Datei.

## Einrichtung im Projekt

0. Skill `ballot-dateischutz` anwenden: klären, wo Skripte, Konfiguration und Vorlagen liegen
   dürfen (Vorlagen im Projektordner brauchen ggf. eine ausdrückliche Ausnahme), Snapshot anlegen.
1. Skripte aus `scripts/` dieses Skills nach `<projekt>/scripts/` kopieren
   (`ballot_issues.py`, `ballot_reconciliation_kommentare.py`, `xlsx_xml.py`).
2. `<projekt>/scripts/ballot_gruppen.py` – bestätigte Gruppen (Vorlage im Skill `ballot-analyse`).
3. `<projekt>/scripts/ballot_metadaten.py` aus `assets/ballot_metadaten_vorlage.py`:
   `REPO`, `BALLOT_ID`, Bereiche, **Kurzfassung + Bereich für jeden Kommentar**, Anliegen +
   Stelle je Gruppe, `EXTRA` für E-Mail/PDF-Einreichungen (nur Kernaussage, kein PDF), Wellen.
4. Reconciliation-Vorlagen `assets/ballot-reconciliation-comment.md` und
   `…-comment-group.md` ins Projektverzeichnis (Elternordner von `scripts/`) legen; der Benutzer
   passt sie bei Bedarf an – das Skript liest sie bei jedem Lauf frisch. `{{BALLOT}}` wird ersetzt;
   die Marker-Zeile `<!-- reconciliation: ballot=… -->` muss erhalten bleiben.
   `assets/ballot-issue-vorlage.md` dokumentiert das Issue-Format (der Text wird im Skript erzeugt).
   Schreibschutz-Regeln des Projekts beachten – ggf. ausdrückliche Ausnahme einholen.
5. **Labels im Repo nachsehen** (öffentliche API, ohne Token):
   `curl -s https://api.github.com/repos/<REPO>/labels?per_page=100`. Vorhandene Bewertungs-
   Labels verwenden (Namen in `BEWERTUNG_LABEL` eintragen), fehlende (Ballot, Bereiche, Wellen)
   legt das Skript an. Akzeptanz-Labels nur nach Absprache.

## Issue-Format (bewährt)

- Titel `[G13] Thema` bzw. `[K-041] Kurzfassung` / `[X01] …` – Ballot steckt im Label, nicht im Titel.
- IDs immer `K-NNN`, nie `#NNN` (GitHub verlinkt sonst auf Issue NNN); `@` vermeiden.
- Kopf: HTML-Marker `<!-- ballot=<ID>; gruppe=…; kommentare=… -->` (Duplikaterkennung, Rückführung),
  „Anliegen“, „Betroffene Stelle“, „Schwerste Bewertung“.
- Je Kommentar ein `<details>`-Block; `<summary>` = ID · Teilnehmer · Bewertung · Kurzfassung;
  darin Feldtabelle + Originaltexte als Zitat. Leerzeile nach `</summary>`/vor `</details>`;
  `|` in Tabellen maskieren.
- Reconciliation (Akzeptanz, Lösung, Umsetzung) **nicht im Issue-Text**, sondern als eigener
  Kommentar; bei Gruppen Tabelle je Kommentar vorbefüllt (ID, Teilnehmer).

## Token und Rechte (Benutzer richtet ein – keine Zugangsdaten auslesen!)

Nie gespeicherte Credentials (git credential, Umgebung) abfragen. Der Benutzer führt die
Schritte mit Netzwerkzugriff selbst aus; Token nie im Chat.
- **Fine-grained Token**: Resource owner = Organisation (z. B. HL7Austria), nur das Ziel-Repo,
  Repository permission **Issues: Read and write** (Metadata read automatisch), kurze Laufzeit.
  Ggf. Freigabe durch Org-Owner nötig (Status „pending“), bei SAML-SSO Token autorisieren.
- **Konto braucht Rolle Write** im Repo – mit Triage legt die API Issues an, verwirft Labels aber stillschweigend.
- Eingabe verdeckt: Git Bash `read -rs -p "GitHub-Token: " GITHUB_TOKEN; echo; export GITHUB_TOKEN`;
  PowerShell `Read-Host -AsSecureString` + Konvertierung. Bei Klartext in der History:
  `history -d N; history -w` bzw. `~/.bash_history` bereinigen – und Token widerrufen.
- Befehle passend zur Shell angeben (VS Code unter Windows startet oft PowerShell; in Git Bash
  Pfade als `/c/Users/…`, lange statt 8.3-Kurzpfade). „No such file“ → zuerst `pwd`,
  `test -f scripts/…`, `test -f "$OUT/issues.json"` prüfen lassen.

## Ablauf

```
python -I scripts/ballot_issues.py vorschau <recon.xlsx> <out>     # offline, Dateien je Issue zum Durchsehen
python -I scripts/ballot_issues.py pruefen  <out>                  # Token, Write-Recht, Rate-Limit, vorhandene Issues
python -I scripts/ballot_issues.py labels   <out>                  # fehlende Labels anlegen
python -I scripts/ballot_issues.py anlegen  <out>                  # ~3 s je Issue, wiederaufsetzbar
python -I scripts/ballot_issues.py excel    <recon_in> <recon_out> <out>   # Issue-URL je Kommentar in Spalte M
python -I scripts/ballot_reconciliation_kommentare.py vorschau <out>
python -I scripts/ballot_reconciliation_kommentare.py anlegen  <out>
```
`<out>` im Scratchpad. Vor dem Anlegen: Vorschau vom Benutzer freigeben lassen, auf
Benachrichtigungen aller Repo-Beobachter hinweisen (1 je Issue bzw. Kommentar), Kommentar-IDs
müssen fixiert sein. Vorschau auf `#\d+`- und `@name`-Muster scannen. `excel` nur auf eine Kopie
anwenden und wie im Skill `ballot-konsolidierung` zurückschreiben (Excel geschlossen, `cmp`);
Spalte M ist im Skript fest – bei anderer Vorlage anpassen. Die Zuordnung Issue ↔ Kommentar
lässt sich jederzeit über die Marker-Zeilen rekonstruieren (`pruefen`).

## Eingebaute Absicherungen (bei Änderungen erhalten)
- Vorabprüfung: Login, `permissions.push`, ≥ 400 verbleibende Requests.
- Duplikatschutz: alle Issues (state=all) bzw. Issue-Kommentare nach Marker durchsuchen, vorhandene übernehmen.
- Rate-Limits: primär → bis `x-ratelimit-reset` warten; sekundär → `Retry-After` bzw. 60/120/240 s;
  andere 4xx (z. B. 403 fehlende Rechte) → sofort abbrechen.
- Netzwerkfehler beim POST → Abbruch statt Retry (Neustart erkennt Angelegtes).
- Nach dem ersten neuen Issue prüfen, ob alle Labels gesetzt wurden.
- Sequentiell, 3 s Pause (≈ 20/min; GitHub-Grenzen ≈ 80 Inhalte/min, 500/h).
Änderungen an der API-Logik offline mit gemocktem `api()` testen (Rate-Limit-, 403-, Netzfehler-
und Duplikatfälle), bevor ein echter Lauf startet.
