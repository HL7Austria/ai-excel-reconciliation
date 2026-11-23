"""GitHub-Issues für einen HL7-Austria-Ballot erzeugen.

Konfiguration in ballot_metadaten.py (Projekt-scripts/): REPO, BALLOT_ID, optional KOMMENTARE_SHEET.

Schritte (jeweils einzeln aufrufen):
  vorschau <recon.xlsx> <outdir>      Issue-Texte als Dateien + issues.json erzeugen (kein Netzwerkzugriff)
  pruefen  <outdir>                   Token/Rechte/Rate-Limit prüfen und bereits vorhandene Issues erkennen
  labels   <outdir>                   fehlende Labels (ballot-<ID>, Bereiche, Wellen) im Repo anlegen
  anlegen  <outdir>                   Issues aus issues.json anlegen; Ergebnis in ergebnis.json (wiederaufsetzbar)
  excel    <recon_in> <recon_out> <outdir>   Issue-URLs in Spalte M von "4) Kommentare" schreiben

Absicherungen:
  - Vorabprüfung: Token gültig, Schreibrecht (push) im Repo, verbleibendes Rate-Limit
  - Keine Duplikate: vor jedem Lauf werden alle Issues des Repos nach der Marker-Zeile
    (<!-- ballot=<ID>; … -->) durchsucht und als bereits angelegt übernommen
  - Rate-Limits: primäres Limit -> Warten bis x-ratelimit-reset; sekundäres Limit -> Retry-After
    bzw. steigende Wartezeit; andere 403/4xx-Fehler -> sofortiger Abbruch
  - Netzwerkfehler beim Anlegen -> Abbruch (kein blinder Retry); erneuter Start erkennt Angelegtes
  - Nach dem ersten neu angelegten Issue wird geprüft, ob alle Labels gesetzt wurden
  - Sequentiell, 3 s Pause zwischen Issues (≈ 20/min, deutlich unter 80/min bzw. 500/h)

Für pruefen/labels/anlegen wird die Umgebungsvariable GITHUB_TOKEN benötigt.
Quelldateien werden nur gelesen; die Reconciliation-Datei wird per ZIP/XML-Patch geschrieben.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from xml.sax.saxutils import escape

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ballot_gruppen import GROUPS  # noqa: E402
import ballot_metadaten as _cfg  # noqa: E402
from ballot_metadaten import (BALLOT_ID, BALLOT_LABEL, BEREICHE, BEWERTUNG_LABEL,  # noqa: E402
                              BEWERTUNG_RANG, GRUPPEN_META, KURZ, REPO, WELLE_LABEL, welle)
from xlsx_xml import sheet_xml_path  # noqa: E402

X01 = getattr(_cfg, "X01", None)                     # optionale Nicht-Excel-Einreichung
EXTRA = getattr(_cfg, "EXTRA", [X01] if X01 else [])  # Liste solcher Einreichungen
KOMMENTARE_SHEET = getattr(_cfg, "KOMMENTARE_SHEET", "4) Kommentare")

API_ROOT = "https://api.github.com"
API = f"{API_ROOT}/repos/{REPO}"
FIELDS = ["ID", "Teilnehmer", "Referenz-Nr", "Bezugnehmend auf", "Seite-Nr", "Zeilen-Nr",
          "Element", "Beschreibung", "Vorgeschlagene Änderung", "Begründung, Kommentar, Frage", "Bewertung"]
LABEL_FARBEN = {BALLOT_LABEL: "5319e7",
                **{v: "c5def5" for v in BEREICHE.values()},
                **{v: "fbca04" for v in WELLE_LABEL.values()}}
MARKER_RE = re.compile(rf"<!-- ballot={re.escape(BALLOT_ID)}; (?:gruppe=(G\d+)|kommentar=([A-Z]+[-\d]+))[;\s]")
PAUSE = 3


# ---------------------------------------------------------------- Daten
def kid(n):
    return f"K-{int(n):03d}"


def bew_key(b):
    m = re.match(r"\([A-Z-]+\)", str(b or ""))
    return m.group(0) if m else None


def read_comments(recon):
    ws = openpyxl.load_workbook(recon, read_only=True, data_only=True)[KOMMENTARE_SHEET]
    out = {}
    for row in ws.iter_rows(min_row=3, max_col=11, values_only=True):
        if row[0] is None:
            continue
        out[int(row[0])] = dict(zip(FIELDS, row))
    return out


# ---------------------------------------------------------------- Markdown
def cell(v):
    s = "–" if v is None or str(v).strip() == "" else str(v).strip()
    return s.replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def quote(v):
    s = "" if v is None else str(v).replace("\r\n", "\n").strip()
    if not s:
        return "> _(leer)_"
    return "\n".join("> " + line if line.strip() else ">" for line in s.split("\n"))


def stelle(c):
    parts = [str(c[f]).strip() for f in ("Seite-Nr", "Zeilen-Nr", "Element") if c[f] and str(c[f]).strip()]
    return " · ".join(parts) if parts else "–"


def comment_block(n, c):
    b = bew_key(c["Bewertung"])
    rows = "\n".join(f"| {f} | {cell(kid(n) if f == 'ID' else c[f])} |"
                     for f in ("ID", "Teilnehmer", "Referenz-Nr", "Bezugnehmend auf", "Seite-Nr",
                               "Zeilen-Nr", "Element", "Bewertung"))
    return (f"<details>\n<summary><b>{kid(n)}</b> · {c['Teilnehmer']} · {b.strip('()') if b else '–'} · "
            f"{escape(KURZ[n][1])}</summary>\n\n| Feld | Inhalt |\n|---|---|\n{rows}\n\n"
            f"**Beschreibung**\n{quote(c['Beschreibung'])}\n\n"
            f"**Vorgeschlagene Änderung**\n{quote(c['Vorgeschlagene Änderung'])}\n\n"
            f"**Begründung, Kommentar, Frage**\n{quote(c['Begründung, Kommentar, Frage'])}\n\n</details>\n")


def issue_body(marker, anliegen, stelle_txt, bewertung, blocks):
    return (f"<!-- {marker} -->\n\n## Anliegen\n{anliegen}\n\n"
            f"**Betroffene Stelle:** {stelle_txt}\n**Schwerste Bewertung:** {bewertung}\n\n"
            f"## Kommentare\n\n" + "\n".join(blocks))


def labels_for(key, bereich, bewertung):
    return [BALLOT_LABEL, BEWERTUNG_LABEL[bewertung], BEREICHE[bereich],
            WELLE_LABEL[welle(key, bereich, bewertung)]]


def build(recon):
    comments = read_comments(recon)
    missing = set(KURZ) ^ set(comments)
    if missing:
        raise SystemExit(f"IDs in Excel und KURZ stimmen nicht überein: {sorted(missing)}")
    bad = [n for n, c in comments.items() if bew_key(c["Bewertung"]) not in BEWERTUNG_LABEL]
    if bad:
        raise SystemExit(f"Unbekannte Bewertung bei: {bad}")
    grouped = {n for _, members in GROUPS.values() for n in members}
    issues = []
    for g, (title, members) in GROUPS.items():
        bereich, anliegen, st = GRUPPEN_META[g]
        worst = min((bew_key(comments[n]["Bewertung"]) for n in members), key=BEWERTUNG_RANG.index)
        worst_full = next(comments[n]["Bewertung"] for n in members if bew_key(comments[n]["Bewertung"]) == worst)
        ids = ",".join(kid(n) for n in members)
        issues.append({
            "key": g, "kommentare": members,
            "title": f"[{g}] {title}",
            "labels": labels_for(g, bereich, worst),
            "body": issue_body(f"ballot={BALLOT_ID}; gruppe={g}; kommentare={ids}", anliegen, st, worst_full,
                               [comment_block(n, comments[n]) for n in members]),
        })
    for n in sorted(comments):
        if n in grouped:
            continue
        c = comments[n]
        bereich, kurz = KURZ[n]
        issues.append({
            "key": kid(n), "kommentare": [n],
            "title": f"[{kid(n)}] {kurz}",
            "labels": labels_for(kid(n), bereich, bew_key(c["Bewertung"])),
            "body": issue_body(f"ballot={BALLOT_ID}; kommentar={kid(n)}", kurz, stelle(c), c["Bewertung"],
                               [comment_block(n, c)]),
        })
    for x in EXTRA:                       # Einreichungen ohne Kommentarformular (E-Mail/PDF)
        xb = (f"<details>\n<summary><b>{x['id']}</b> · {x['teilnehmer']} · {bew_key(x['bewertung']).strip('()')} · "
              f"{x['kurz']}</summary>\n\n| Feld | Inhalt |\n|---|---|\n| ID | {x['id']} |\n"
              f"| Teilnehmer | {x['teilnehmer']} |\n| Einsender | {x['einsender']} |\n"
              f"| Eingang | {x['eingang']} |\n| Bewertung | {x['bewertung']} |\n\n"
              f"**Kernfragestellung**\n{quote(x['text'])}\n\n</details>\n")
        issues.append({
            "key": x["id"], "kommentare": [],
            "title": f"[{x['id']}] {x['kurz']}",
            "labels": labels_for(x["id"], x["bereich"], bew_key(x["bewertung"])),
            "body": issue_body(f"ballot={BALLOT_ID}; kommentar={x['id']}", x["kurz"],
                               "allgemein (E-Mail, kein Kommentarformular)", x["bewertung"], [xb]),
        })
    # Marker müssen eindeutig und vom MARKER_RE erkennbar sein
    keys = [marker_key(i["body"]) for i in issues]
    if keys != [i["key"] for i in issues]:
        raise SystemExit("Marker-Zeilen nicht eindeutig erkennbar")
    return issues


def marker_key(body):
    m = MARKER_RE.search(body or "")
    return (m.group(1) or m.group(2)) if m else None


# ---------------------------------------------------------------- GitHub API
class NetzFehler(Exception):
    pass


def _token():
    t = os.environ.get("GITHUB_TOKEN", "").strip()
    if not t:
        raise SystemExit("GITHUB_TOKEN ist nicht gesetzt")
    return t


def api(method, url, data=None):
    """Ruft die GitHub-API auf. Wartet nur bei echten Rate-Limits, bricht sonst sofort ab."""
    body = json.dumps(data).encode() if data is not None else None
    backoff = 60
    for attempt in range(6):
        req = urllib.request.Request(url, method=method, data=body, headers={
            "Authorization": f"Bearer {_token()}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "ballot-issues-script"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read() or b"null"), r.headers
        except urllib.error.HTTPError as e:
            text = e.read().decode(errors="replace")
            remaining = e.headers.get("x-ratelimit-remaining")
            retry_after = e.headers.get("retry-after")
            if e.code in (403, 429) and remaining == "0":
                wait = max(5, int(e.headers.get("x-ratelimit-reset", time.time() + 60)) - int(time.time()) + 5)
                print(f"  Primäres Rate-Limit erreicht – warte {wait}s bis zum Reset …")
            elif e.code in (403, 429) and (retry_after or "secondary rate limit" in text.lower()):
                wait = int(retry_after) if retry_after else backoff
                backoff = min(backoff * 2, 900)
                print(f"  Sekundäres Rate-Limit – warte {wait}s …")
            else:
                raise SystemExit(f"{method} {url} -> HTTP {e.code} (kein Rate-Limit, Abbruch):\n{text[:600]}")
            if attempt == 5:
                raise SystemExit("Rate-Limit hält an – Abbruch. Später erneut starten.")
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise NetzFehler(f"{method} {url}: {e}")


def get_all(url):
    items, page = [], 1
    sep = "&" if "?" in url else "?"
    while True:
        batch, _ = api("GET", f"{url}{sep}per_page=100&page={page}")
        items += batch
        if len(batch) < 100:
            return items
        page += 1


def preflight():
    user, _ = api("GET", f"{API_ROOT}/user")
    repo, _ = api("GET", API)
    perms = repo.get("permissions") or {}
    rl, _ = api("GET", f"{API_ROOT}/rate_limit")
    core = rl["resources"]["core"]
    print(f"Angemeldet als: {user['login']}")
    print(f"Rechte in {REPO}: " + ", ".join(k for k, v in perms.items() if v))
    print(f"Rate-Limit: {core['remaining']}/{core['limit']} verbleibend")
    if not perms.get("push"):
        raise SystemExit("Kein Schreibrecht (Rolle Write) im Repo – Labels würden beim Anlegen verworfen. Abbruch.")
    if core["remaining"] < 400:
        raise SystemExit("Zu wenig Rate-Limit für einen vollständigen Lauf – später erneut starten.")


def vorhandene(issues):
    """Sucht bereits angelegte Ballot-Issues im Repo (alle Zustände) anhand der Marker-Zeile."""
    wanted = {i["key"]: i for i in issues}
    found = {}
    for gh in get_all(f"{API}/issues?state=all"):
        if "pull_request" in gh:
            continue
        k = marker_key(gh.get("body"))
        if k in wanted:
            if k in found:
                print(f"  WARNUNG: {k} existiert mehrfach (#{found[k]['number']} und #{gh['number']})")
                continue
            found[k] = {"number": gh["number"], "url": gh["html_url"], "kommentare": wanted[k]["kommentare"]}
    return found


def load_issues(outdir):
    return json.load(open(os.path.join(outdir, "issues.json"), encoding="utf-8"))


def cmd_pruefen(outdir):
    preflight()
    found = vorhandene(load_issues(outdir))
    print(f"Bereits im Repo vorhanden: {len(found)} Ballot-Issues")


def cmd_labels(outdir):
    preflight()
    existing = {l["name"] for l in get_all(f"{API}/labels")}
    needed = sorted({l for i in load_issues(outdir) for l in i["labels"]})
    for name in needed:
        if name in existing:
            continue
        if name not in LABEL_FARBEN:
            raise SystemExit(f"Label '{name}' fehlt im Repo und wird nicht automatisch angelegt")
        api("POST", f"{API}/labels", {"name": name, "color": LABEL_FARBEN[name]})
        print("Label angelegt:", name)
        time.sleep(1)
    print("Labels vollständig.")


def cmd_anlegen(outdir):
    issues = load_issues(outdir)
    preflight()
    existing_labels = {l["name"] for l in get_all(f"{API}/labels")}
    missing_labels = sorted({l for i in issues for l in i["labels"]} - existing_labels)
    if missing_labels:
        raise SystemExit(f"Labels fehlen im Repo, zuerst 'labels' ausführen: {missing_labels}")

    res_path = os.path.join(outdir, "ergebnis.json")
    result = json.load(open(res_path, encoding="utf-8")) if os.path.exists(res_path) else {}
    found = vorhandene(issues)                       # Abgleich mit dem Repo -> keine Duplikate
    for k, v in found.items():
        if k not in result:
            print(f"  bereits vorhanden, übernommen: {k} -> #{v['number']}")
        result[k] = v
    json.dump(result, open(res_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    first_checked = False
    for i in issues:                                 # Reihenfolge wie in issues.json
        if i["key"] in result:
            continue
        try:
            r, _ = api("POST", f"{API}/issues", {"title": i["title"], "body": i["body"], "labels": i["labels"]})
        except NetzFehler as e:
            raise SystemExit(f"Verbindungsfehler bei {i['key']}: {e}\n"
                             "Bitte erneut starten – bereits angelegte Issues werden erkannt.")
        result[i["key"]] = {"number": r["number"], "url": r["html_url"], "kommentare": i["kommentare"]}
        json.dump(result, open(res_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"#{r['number']:>4}  {i['title']}")
        if not first_checked:
            got = {l["name"] for l in r.get("labels", [])}
            if got != set(i["labels"]):
                raise SystemExit(f"Labels wurden nicht vollständig gesetzt (#{r['number']}): erwartet "
                                 f"{sorted(i['labels'])}, erhalten {sorted(got)}. Abbruch.")
            first_checked = True
        time.sleep(PAUSE)
    print(f"Fertig: {len(result)} von {len(issues)} Issues angelegt.")


# ---------------------------------------------------------------- Excel (Spalte M)
def cmd_excel(recon_in, recon_out, outdir):
    result = json.load(open(os.path.join(outdir, "ergebnis.json"), encoding="utf-8"))
    url_by_id = {n: v["url"] for v in result.values() for n in v["kommentare"]}
    with zipfile.ZipFile(recon_in) as zin:
        sheet_path = sheet_xml_path(zin, KOMMENTARE_SHEET)
        xml = zin.read(sheet_path).decode("utf-8")
        rows = {int(m.group(2)): int(m.group(1)) for m in
                re.finditer(r'<c r="A(\d+)"[^>]*><v>(\d+)</v></c>', xml)}
        done = 0
        for n, url in sorted(url_by_id.items()):
            r = rows[n]
            m = re.search(rf'<c r="M{r}"( s="\d+")?(/>|>.*?</c>)', xml, re.S)
            if m is None:
                raise SystemExit(f"Zelle M{r} nicht gefunden")
            if m.group(2) != "/>":
                raise SystemExit(f"Zelle M{r} (K-{n:03d}) ist nicht leer – Abbruch")
            new = f'<c r="M{r}"{m.group(1) or ""} t="inlineStr"><is><t>{escape(url)}</t></is></c>'
            xml = xml[:m.start()] + new + xml[m.end():]
            done += 1
        with zipfile.ZipFile(recon_out, "w") as zout:
            for item in zin.infolist():
                data = xml.encode("utf-8") if item.filename == sheet_path else zin.read(item)
                zout.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED)
    print(f"{done} Issue-URLs in Spalte M geschrieben.")


def cmd_vorschau(recon, outdir):
    issues = build(recon)
    os.makedirs(outdir, exist_ok=True)
    json.dump(issues, open(os.path.join(outdir, "issues.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for i in issues:
        with open(os.path.join(outdir, f"{i['key']}.md"), "w", encoding="utf-8") as f:
            f.write(f"# {i['title']}\n\nLabels: {', '.join(i['labels'])}\n\n---\n\n{i['body']}")
    n_g = sum(1 for i in issues if i["key"].startswith("G"))
    print(f"{len(issues)} Issues ({n_g} Gruppen, {len(issues) - n_g} Einzel) -> {outdir}")
    from collections import Counter
    print("Wellen:", dict(sorted(Counter(l for i in issues for l in i["labels"] if l.startswith("welle-")).items())))
    print("Labels:", sorted({l for i in issues for l in i["labels"]}))
    print("max. Body-Länge:", max(len(i["body"]) for i in issues))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cmd, *args = sys.argv[1:]
    cmds = {"vorschau": cmd_vorschau, "pruefen": cmd_pruefen, "labels": cmd_labels,
            "anlegen": cmd_anlegen, "excel": cmd_excel}
    cmds[cmd](*args)
