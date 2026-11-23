"""Legt in jedem Ballot-Issue einen vorbereiteten Reconciliation-Kommentar an.

Vorlagen (werden bei jedem Lauf frisch gelesen):
  ballot-reconciliation-comment.md        Einzel-Issues (K-NNN, X01)
  ballot-reconciliation-comment-group.md  Gruppen-Issues – Tabelle wird je Kommentar vorbefüllt
                                          (ID + Teilnehmer; Akzeptanz/Anmerkung bleiben Platzhalter)

Aufruf:
  vorschau <outdir>   Kommentartexte nach <outdir>/reconciliation/*.md schreiben (offline)
  anlegen  <outdir>   Kommentare anlegen (benötigt GITHUB_TOKEN)

<outdir> ist das Verzeichnis mit issues.json aus ballot_issues.py. Die Teilnehmer der
Gruppentabelle werden aus den Issue-Texten in issues.json gelesen (keine Excel-Datei nötig).
Absicherungen: Vorabprüfung (Token/Rechte/Limit), Issues werden über die Marker-Zeile im Repo
gefunden, ein Issue mit bereits vorhandenem Reconciliation-Kommentar (Marker
"<!-- reconciliation: ballot=<ID>") wird übersprungen, Rate-Limit-Behandlung aus ballot_issues.py,
3 s Pause zwischen Kommentaren, Ergebnis in reconciliation_ergebnis.json.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ballot_gruppen import GROUPS  # noqa: E402
from ballot_metadaten import BALLOT_ID  # noqa: E402
from ballot_issues import (API, PAUSE, NetzFehler, api, get_all, kid,  # noqa: E402
                           load_issues, preflight, vorhandene)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_SINGLE = os.path.join(BASE, "ballot-reconciliation-comment.md")
TPL_GROUP = os.path.join(BASE, "ballot-reconciliation-comment-group.md")
RECON_MARKER = f"<!-- reconciliation: ballot={BALLOT_ID}"
ROW_HINT_RE = re.compile(r"^<!--\s*Zeile je referenziertem Kommentar wiederholen\s*-->\n\n?", re.M)
# Feldtabelle im Issue-Text: "| ID | K-075 |" gefolgt von "| Teilnehmer | … |" (bereits Markdown-maskiert)
TEILN_RE = re.compile(r"^\| ID \| (K-\d{3}) \|\n\| Teilnehmer \| (.*) \|$", re.M)


def teilnehmer_aus_body(body):
    return {k: t for k, t in TEILN_RE.findall(body)}


def render_single(tpl, key):
    out = tpl.replace("K-{{NNN}}", key)
    if "{{NNN}}" in out:
        raise SystemExit("Einzel-Vorlage enthält unerwartete {{NNN}}-Platzhalter")
    return out


def render_group(tpl, g, members, teilnehmer):
    lines = tpl.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("| K-{{NNN}}")]
    if len(idx) != 1:
        raise SystemExit("Gruppen-Vorlage: genau eine Tabellenzeile '| K-{{NNN}} …' erwartet")
    row_tpl = lines[idx[0]]
    rows = [row_tpl.replace("K-{{NNN}}", kid(n)).replace("{{TEILNEHMER}}", teilnehmer[kid(n)])
            for n in members]
    out = "\n".join(lines[:idx[0]] + rows + lines[idx[0] + 1:])
    out = ROW_HINT_RE.sub("", out)
    out = out.replace("{{GRUPPE}}", g).replace("{{K-IDS}}", ",".join(kid(n) for n in members))
    if "{{NNN}}" in out or "{{TEILNEHMER}}" in out:
        raise SystemExit("Gruppen-Vorlage: nicht ersetzte ID/Teilnehmer-Platzhalter")
    return out


def build(outdir):
    tpl_s = open(TPL_SINGLE, encoding="utf-8").read()
    tpl_g = open(TPL_GROUP, encoding="utf-8").read()
    bodies = {}
    for i in load_issues(outdir):
        k = i["key"]
        if k in GROUPS:
            members = GROUPS[k][1]
            if members != i["kommentare"]:
                raise SystemExit(f"{k}: Gruppenmitglieder weichen von issues.json ab")
            teilnehmer = teilnehmer_aus_body(i["body"])
            fehlend = [kid(n) for n in members if kid(n) not in teilnehmer]
            if fehlend:
                raise SystemExit(f"{k}: Teilnehmer im Issue-Text nicht gefunden für {fehlend}")
            bodies[k] = render_group(tpl_g, k, members, teilnehmer)
        else:
            bodies[k] = render_single(tpl_s, k)
        bodies[k] = bodies[k].replace("{{BALLOT}}", BALLOT_ID)
        if RECON_MARKER not in bodies[k]:
            raise SystemExit(f"{k}: Vorlage enthält keine Marker-Zeile '{RECON_MARKER} …' "
                             "(sonst keine Duplikaterkennung möglich)")
    return bodies


def cmd_vorschau(outdir):
    bodies = build(outdir)
    d = os.path.join(outdir, "reconciliation")
    os.makedirs(d, exist_ok=True)
    for k, b in bodies.items():
        with open(os.path.join(d, f"{k}.md"), "w", encoding="utf-8") as f:
            f.write(b)
    print(f"{len(bodies)} Reconciliation-Kommentare -> {d}")


def cmd_anlegen(outdir):
    bodies = build(outdir)
    issues = load_issues(outdir)
    preflight()
    found = vorhandene(issues)
    missing = [i["key"] for i in issues if i["key"] not in found]
    if missing:
        raise SystemExit(f"Issues im Repo nicht gefunden: {missing[:10]} … – Abbruch")
    res_path = os.path.join(outdir, "reconciliation_ergebnis.json")
    result = json.load(open(res_path, encoding="utf-8")) if os.path.exists(res_path) else {}
    neu = 0
    for i in issues:                                   # Reihenfolge wie beim Anlegen der Issues
        k = i["key"]
        nr = found[k]["number"]
        if k in result:
            continue
        existing = [c for c in get_all(f"{API}/issues/{nr}/comments")
                    if RECON_MARKER in (c.get("body") or "")]
        if existing:
            result[k] = {"issue": nr, "comment_id": existing[0]["id"], "url": existing[0]["html_url"]}
            print(f"  #{nr} {k}: Reconciliation-Kommentar bereits vorhanden – übersprungen")
        else:
            try:
                c, _ = api("POST", f"{API}/issues/{nr}/comments", {"body": bodies[k]})
            except NetzFehler as e:
                raise SystemExit(f"Verbindungsfehler bei {k} (#{nr}): {e}\n"
                                 "Bitte erneut starten – vorhandene Kommentare werden erkannt.")
            result[k] = {"issue": nr, "comment_id": c["id"], "url": c["html_url"]}
            neu += 1
            print(f"  #{nr} {k}: Kommentar angelegt")
            time.sleep(PAUSE)
        json.dump(result, open(res_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Fertig: {neu} neu angelegt, {len(result)} von {len(issues)} Issues haben einen Reconciliation-Kommentar.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cmd, *args = sys.argv[1:]
    {"vorschau": cmd_vorschau, "anlegen": cmd_anlegen}[cmd](*args)
