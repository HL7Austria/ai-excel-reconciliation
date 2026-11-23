"""Bestätigte Gruppierung der Ballot-Kommentare (Stand JJJJ-MM-TT).

Schlüssel = Gruppen-ID, Werte = (Titel, [#ID aus Blatt "Kommentare" Spalte A]).
Alle hier nicht genannten Kommentare werden als Einzel-Issues behandelt.
Regel: Gleicher Text an verschiedenen Stellen bzw. nur ähnliche Kommentare werden NICHT gruppiert.
Entscheidungen: <hier dokumentieren, z. B. "K-089 separat">
"""

GROUPS = {
    "G01": ("Titel der Gruppe", [1, 101, 145]),
    "G02": ("…", [7, 157]),
}


def check():
    ids = [i for _, members in GROUPS.values() for i in members]
    assert len(ids) == len(set(ids)), "Kommentar in mehreren Gruppen"
    return len(GROUPS), len(ids)


if __name__ == "__main__":
    print("Gruppen: %d, gruppierte Kommentare: %d" % check())
