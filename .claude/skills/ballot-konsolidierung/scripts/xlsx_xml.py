"""Hilfsfunktionen, um einzelne Teile einer .xlsx-Datei gezielt zu ersetzen.

Warum: openpyxl entfernt beim Speichern u. a. Datenvalidierungs-Erweiterungen (x14),
Pivot-Details und Kommentare. Die Reconciliation-Vorlagen von HL7 Austria nutzen genau
diese Features. Daher wird nie über openpyxl gespeichert, sondern das ZIP neu geschrieben
und nur die geänderten XML-Teile werden ersetzt.
"""
import posixpath
import re
import zipfile

def _rels(zf, path):
    """Liefert {rId: Ziel (absolut im ZIP)} für eine .rels-Datei."""
    try:
        xml = zf.read(path).decode("utf-8")
    except KeyError:
        return {}
    base = posixpath.dirname(posixpath.dirname(path))  # .../_rels/x.rels -> ...
    out = {}
    for m in re.finditer(r"<Relationship\b([^>]*)/?>", xml):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        tgt = attrs.get("Target", "")
        if attrs.get("TargetMode") == "External":
            continue
        full = posixpath.normpath(tgt.lstrip("/") if tgt.startswith("/") else posixpath.join(base, tgt))
        out[attrs["Id"]] = (full, attrs.get("Type", ""))
    return out


def sheet_xml_path(zf, sheet_name):
    """Pfad des Worksheet-XML zu einem Blattnamen, z. B. 'xl/worksheets/sheet4.xml'."""
    wb = zf.read("xl/workbook.xml").decode("utf-8")
    for m in re.finditer(r"<sheet\b([^>]*)/>", wb):
        attrs = dict(re.findall(r'([\w:]+)="([^"]*)"', m.group(1)))
        name = (attrs.get("name", "").replace("&amp;", "&").replace("&quot;", '"')
                .replace("&lt;", "<").replace("&gt;", ">").replace("&apos;", "'"))
        if name == sheet_name:
            rid = attrs["r:id"]
            return _rels(zf, "xl/_rels/workbook.xml.rels")[rid][0]
    raise KeyError(f"Blatt '{sheet_name}' nicht gefunden")


def tables_of_sheet(zf, sheet_path):
    """{Tabellenname: Pfad} aller Tabellen (ListObjects) eines Blatts."""
    rels = _rels(zf, posixpath.join(posixpath.dirname(sheet_path), "_rels",
                                    posixpath.basename(sheet_path) + ".rels"))
    out = {}
    for path, typ in rels.values():
        if typ.endswith("/table"):
            xml = zf.read(path).decode("utf-8")
            out[re.search(r'\bname="([^"]+)"', xml).group(1)] = path
    return out


def pivot_caches_for_table(zf, table_name):
    """Pfade aller Pivot-Cache-Definitionen, deren Quelle die Tabelle ist."""
    out = []
    for n in zf.namelist():
        if n.startswith("xl/pivotCache/pivotCacheDefinition") and n.endswith(".xml"):
            if re.search(rf'<worksheetSource name="{re.escape(table_name)}"', zf.read(n).decode("utf-8")):
                out.append(n)
    return out


def set_refresh_on_load(xml):
    if "refreshOnLoad=" in xml:
        return xml
    return xml.replace("<pivotCacheDefinition ", '<pivotCacheDefinition refreshOnLoad="1" ', 1)


def rewrite_zip(src, dst, replacements, full_calc=True):
    """Schreibt src nach dst und ersetzt die Teile in replacements {pfad: str}.
    full_calc: Excel beim Öffnen alle Formeln neu berechnen lassen (Ergebniszeilen etc.)."""
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        repl = dict(replacements)
        if full_calc and "xl/workbook.xml" not in repl:
            wb = zin.read("xl/workbook.xml").decode("utf-8")
            if "<calcPr" in wb and "fullCalcOnLoad=" not in wb:
                repl["xl/workbook.xml"] = wb.replace("<calcPr", '<calcPr fullCalcOnLoad="1"', 1)
        for item in zin.infolist():
            data = repl[item.filename].encode("utf-8") if item.filename in repl else zin.read(item)
            zout.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED)


ILLEGAL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def inline_str_cell(ref, style, text):
    from xml.sax.saxutils import escape
    s = f' s="{style}"' if style else ""
    t = ILLEGAL_XML.sub("", escape(str(text)).replace("\r\n", "\n"))
    return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{t}</t></is></c>'


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def cell_xml(ref, style, value):
    """Zell-XML für str / int / float / date / None (Stil wird übernommen)."""
    import datetime as dt
    s = f' s="{style}"' if style else ""
    if value is None:
        return f'<c r="{ref}"{s}/>'
    if isinstance(value, bool):
        return f'<c r="{ref}"{s} t="b"><v>{int(value)}</v></c>'
    if isinstance(value, dt.datetime):
        value = value.date()
    if isinstance(value, dt.date):                       # Excel-Seriennummer; Zelle braucht Datumsstil
        return f'<c r="{ref}"{s}><v>{(value - dt.date(1899, 12, 30)).days}</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"{s}><v>{value}</v></c>'
    return inline_str_cell(ref, style, value)


CELL_RE = r'<c r="{ref}"(?: s="(\d+)")?[^>]*?(?:/>|>.*?</c>)'


def get_cell(xml, ref):
    """(style, inhalt_vorhanden) einer Zelle oder (None, False), falls nicht vorhanden."""
    m = re.search(CELL_RE.format(ref=ref), xml, re.S)
    if not m:
        return None, False
    return m.group(1), bool(re.search(r"<v>|<is>|<f>", m.group(0)))


def put_cell(xml, ref, value, overwrite=False):
    """Setzt eine Zelle im Worksheet-XML; behält den vorhandenen Stil.
    Bricht ab, wenn die Zelle schon Inhalt hat (außer overwrite=True)."""
    col, row = re.match(r"([A-Z]+)(\d+)", ref).groups()
    m = re.search(CELL_RE.format(ref=ref), xml, re.S)
    if m:
        if not overwrite and re.search(r"<v>|<is>|<f>", m.group(0)):
            raise SystemExit(f"Zelle {ref} ist nicht leer – Abbruch (nichts überschreiben)")
        return xml[:m.start()] + cell_xml(ref, m.group(1), value) + xml[m.end():]
    rm = re.search(rf'<row r="{row}"[^>]*?(/>|>(.*?)</row>)', xml, re.S)
    if not rm:
        raise SystemExit(f"Zeile {row} existiert im Blatt nicht – bitte Tabelle in Excel vorbereiten")
    if rm.group(1) == "/>":
        new_row = rm.group(0)[:-2] + ">" + cell_xml(ref, None, value) + "</row>"
        return xml[:rm.start()] + new_row + xml[rm.end():]
    inner = rm.group(2)
    pos = len(inner)
    for cm in re.finditer(r'<c r="([A-Z]+)\d+"', inner):
        if col_index(cm.group(1)) > col_index(col):
            pos = cm.start()
            break
    inner = inner[:pos] + cell_xml(ref, None, value) + inner[pos:]
    start = rm.start(2)
    return xml[:start] + inner + xml[rm.end(2):]
