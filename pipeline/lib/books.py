"""Bible book table and a verse-reference parser.

RG codes are the book codes seen in Read 'n Grow file names (derived from
research/data/manifest.csv). Books with no pictures have rg=None.
Run `python3 pipeline/lib/books.py` for the self-test.
"""
import re

# (usfm, rg code or None, English name, extra aliases)
_BOOKS = [
    ("GEN", "Ge", "Genesis", ["Gen", "Gn"]),
    ("EXO", "Ex", "Exodus", ["Exod", "Exo"]),
    ("LEV", "Le", "Leviticus", ["Lev", "Lv"]),
    ("NUM", "Nu", "Numbers", ["Num"]),
    ("DEU", "De", "Deuteronomy", ["Deut", "Dt"]),
    ("JOS", "Jo", "Joshua", ["Josh"]),
    ("JDG", "Ju", "Judges", ["Judg"]),
    ("RUT", "Ru", "Ruth", []),
    ("1SA", "1Sa", "1 Samuel", ["1 Sam"]),
    ("2SA", "2Sa", "2 Samuel", ["2 Sam"]),
    ("1KI", "1Ki", "1 Kings", ["1 Kgs"]),
    ("2KI", "2Ki", "2 Kings", ["2 Kgs"]),
    ("1CH", "1Ch", "1 Chronicles", ["1 Chron"]),
    ("2CH", "2Ch", "2 Chronicles", ["2 Chron"]),
    ("EZR", "Ezr", "Ezra", []),
    ("NEH", "Ne", "Nehemiah", ["Neh"]),
    ("EST", "Es", "Esther", ["Esth"]),
    ("JOB", "Jb", "Job", []),
    ("PSA", "Ps", "Psalms", ["Psalm", "Pslm"]),
    ("PRO", "Pr", "Proverbs", ["Prov"]),
    ("ECC", None, "Ecclesiastes", ["Eccl", "Eccles"]),
    ("SNG", None, "Song of Solomon", ["Song of Songs", "Song of Song", "Canticles", "Song"]),
    ("ISA", "Is", "Isaiah", ["Isa"]),
    ("JER", "Jer", "Jeremiah", []),
    ("LAM", None, "Lamentations", ["Lam"]),
    ("EZK", "Eze", "Ezekiel", ["Ezek"]),
    ("DAN", "Da", "Daniel", ["Dan"]),
    ("HOS", None, "Hosea", []),
    ("JOL", None, "Joel", []),
    ("AMO", None, "Amos", []),
    ("OBA", None, "Obadiah", ["Obad"]),
    ("JON", "Jon", "Jonah", []),
    ("MIC", None, "Micah", []),
    ("NAM", None, "Nahum", ["Nah"]),
    ("HAB", None, "Habakkuk", ["Hab"]),
    ("ZEP", None, "Zephaniah", ["Zeph"]),
    ("HAG", None, "Haggai", []),
    ("ZEC", None, "Zechariah", ["Zech"]),
    ("MAL", None, "Malachi", []),
    ("MAT", "Mt", "Matthew", ["Matt"]),
    ("MRK", "Mk", "Mark", []),
    ("LUK", "Lk", "Luke", []),
    ("JHN", "Jn", "John", []),
    ("ACT", "Ac", "Acts", ["Acts of the Apostles"]),
    ("ROM", None, "Romans", ["Rom"]),
    ("1CO", None, "1 Corinthians", ["1 Cor"]),
    ("2CO", None, "2 Corinthians", ["2 Cor"]),
    ("GAL", None, "Galatians", ["Gal"]),
    ("EPH", None, "Ephesians", ["Eph"]),
    ("PHP", None, "Philippians", ["Phil"]),
    ("COL", None, "Colossians", ["Col"]),
    ("1TH", None, "1 Thessalonians", ["1 Thess"]),
    ("2TH", None, "2 Thessalonians", ["2 Thess"]),
    ("1TI", "1Ti", "1 Timothy", ["1 Tim"]),
    ("2TI", "2Ti", "2 Timothy", ["2 Tim"]),
    ("TIT", "Tit", "Titus", []),
    ("PHM", None, "Philemon", ["Phlm"]),
    ("HEB", None, "Hebrews", []),
    ("JAS", "Ja", "James", ["Jas"]),
    ("1PE", None, "1 Peter", ["1 Pet"]),
    ("2PE", None, "2 Peter", ["2 Pet"]),
    ("1JN", "1Jn", "1 John", []),
    ("2JN", None, "2 John", []),
    ("3JN", None, "3 John", []),
    ("JUD", None, "Jude", []),
    ("REV", "Re", "Revelation", ["Revelation of John", "Revelation of Jesus Christ", "Rev"]),
]
assert len(_BOOKS) == 66

USFM_CODES = [b[0] for b in _BOOKS]
NAMES = {b[0]: b[2] for b in _BOOKS}
_BY_RG = {b[1].lower(): b[0] for b in _BOOKS if b[1]}
_ROMAN = {"1": "I", "2": "II", "3": "III"}


def usfm_from_rg(code):
    """USFM code for an RG file-name code (case-insensitive), or None."""
    return _BY_RG.get(code.lower())


def _alias_map():
    m = {}
    for usfm, rg, name, extra in _BOOKS:
        names = [name, usfm] + extra + ([rg] if rg else [])
        for n in names:
            variants = {n}
            if n[0].isdigit():
                variants.add(n.replace(" ", "", 1))
                if n[1] == " ":  # roman variants of spaced names only ("1 Samuel"), never of codes like "1Sa"
                    variants.add(_ROMAN[n[0]] + " " + n[2:])
            for v in variants:
                m[v.lower()] = usfm
    return m


_ALIASES = _alias_map()
_BOOK_RE = re.compile(
    r"(?<![A-Za-z0-9])(" + "|".join(
        re.escape(a).replace(r"\ ", r"\s+") for a in sorted(_ALIASES, key=len, reverse=True)
    ) + r")\.?\s*(?=\d)", re.I)
_ITEM_RE = re.compile(r"^(\d+)[a-z]?(?:\s*[-–]\s*(?:(\d+)\s*:\s*)?(\d+)[a-z]?)?$", re.I)
_CHAP_RE = re.compile(r"^(\d+)(?:\s*[-–]\s*(\d+))?$")


def _book_of(alias):
    a = re.sub(r"\s+", " ", alias.lower())
    return _ALIASES.get(a) or _ALIASES[a.replace(" ", "")]


def _make(book, ch, vs, ve, ch_end=None):
    p = {"ref": "", "book": book, "chapter": ch, "verse_start": vs, "verse_end": ve}
    if ch_end is not None and ch_end != ch:
        p["chapter_end"] = ch_end
        p["ref"] = f"{book} {ch}:{vs}-{ch_end}:{ve}" if vs is not None else f"{book} {ch}-{ch_end}"
    elif vs is None:
        p["ref"] = f"{book} {ch}"
    elif vs == ve:
        p["ref"] = f"{book} {ch}:{vs}"
    else:
        p["ref"] = f"{book} {ch}:{vs}-{ve}"
    return p


_SINGLE_CHAPTER = {"OBA", "PHM", "2JN", "3JN", "JUD"}  # a lone number after these is a verse of chapter 1


def _parse_body(book, body, unparsed):
    out, cur = [], None
    for seg in body.split(";"):
        seg = seg.strip().strip(".")
        if not seg:
            continue
        m = re.match(r"^(\d+)\s*:\s*(.*)$", seg)
        if m:
            cur, rest = int(m.group(1)), m.group(2)
            if cur < 1:
                unparsed.append(f"{book} {seg}")
                continue
        elif cur is not None and _ITEM_RE.match(seg.split(",")[0].strip()):
            rest = seg  # "35:1-7; 9-15": the sources use ";" between verse ranges of one chapter
        elif book in _SINGLE_CHAPTER and cur is None:
            cur, rest = 1, seg
        elif _CHAP_RE.match(seg):
            a, b = _CHAP_RE.match(seg).groups()
            if int(a) < 1 or (b and int(b) <= int(a)):
                unparsed.append(f"{book} {seg}")
                continue
            out.append(_make(book, int(a), None, None, int(b) if b else None))
            cur = None
            continue
        else:
            unparsed.append(f"{book} {seg}")
            continue
        for item in rest.split(","):
            item = item.strip().strip(".")
            cm = re.match(r"^(\d+)\s*:\s*(.+)$", item)  # "Matthew 10:16-36, 11:1": new chapter mid-list
            if cm:
                cur, item = int(cm.group(1)), cm.group(2)
            im = _ITEM_RE.match(item)
            if not im:
                unparsed.append(f"{book} {cur}:{item}")
                continue
            vs = int(re.match(r"\d+", item).group())
            s_raw = re.match(r"\d+", item).group()
            e_ch, e_raw = im.group(2), im.group(3)
            ve, ch_end = vs, cur
            if e_raw is not None:
                ve = int(e_raw)
                if e_ch:
                    ch_end = int(e_ch)
                elif ve < vs and len(e_raw) < len(s_raw):  # "15-6" means 15-16
                    ve = int(s_raw[:len(s_raw) - len(e_raw)] + e_raw)
                    if ve <= vs:
                        ve = -1
                if ch_end < cur or (ch_end == cur and ve < vs):
                    ve = -1
            if vs < 1 or ve < 1:
                unparsed.append(f"{book} {cur}:{item}")
                continue
            out.append(_make(book, cur, vs, ve, ch_end))
    return out


def parse_references(text):
    """Parse reference text into (passages, unparsed_pieces)."""
    passages, unparsed = [], []
    text = text.strip().replace("\u060c", ",")  # Arabic comma
    ms = list(_BOOK_RE.finditer(text))
    if not ms:
        return [], ([text] if text else [])
    if text[:ms[0].start()].strip(" ,;/()"):
        unparsed.append(text[:ms[0].start()].strip())
    bodies = []  # (book, body); "Joshua 3:1 - Joshua 4:24" is merged into "3:1-4:24"
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        book = _book_of(m.group(1))
        body = text[m.end():end].strip(" ,;/()")
        if bodies and bodies[-1][0] == book and bodies[-1][1].endswith(("-", "\u2013")):
            body = bodies.pop()[1] + body
        bodies.append((book, body))
    for book, body in bodies:
        passages += _parse_body(book, body, unparsed)
    return passages, unparsed


if __name__ == "__main__":
    def one(t):
        p, u = parse_references(t)
        assert not u, (t, u)
        return p

    assert usfm_from_rg("EX") == "EXO" and usfm_from_rg("LK") == "LUK" and usfm_from_rg("1sa") == "1SA"
    assert usfm_from_rg("Jb") == "JOB" and usfm_from_rg("Xx") is None
    assert len({b[1] for b in _BOOKS if b[1]}) == 36
    p = one("Luke 01:05-7")[0]
    assert p == {"ref": "LUK 1:5-7", "book": "LUK", "chapter": 1, "verse_start": 5, "verse_end": 7}, p
    assert one("Matthew 8: 33")[0]["ref"] == "MAT 8:33"
    assert one("Mark 2:1-12")[0]["ref"] == "MRK 2:1-12"
    assert [x["ref"] for x in one("Luke 4:4, 9-11")] == ["LUK 4:4", "LUK 4:9-11"]
    g = one("Genesis 1")[0]
    assert g["ref"] == "GEN 1" and g["verse_start"] is None and g["verse_end"] is None
    c = one("Luke 5:39-6:5")[0]
    assert c["ref"] == "LUK 5:39-6:5" and c["chapter"] == 5 and c["chapter_end"] == 6 and c["verse_end"] == 5
    assert [x["ref"] for x in one("Matthew 10:16-36,39-42, 11:1")] == ["MAT 10:16-36", "MAT 10:39-42", "MAT 11:1"]
    c2 = one("Joshua 3: 1 - Joshua 4: 24")[0]
    assert c2["ref"] == "JOS 3:1-4:24" and c2["chapter_end"] == 4, c2
    assert one("Job 42: 10\u060c 12")[1]["ref"] == "JOB 42:12"
    assert parse_references("Mark 6: 47-18")[0] == []
    assert one("John 01:39b")[0]["ref"] == "JHN 1:39"
    assert one("Luke 21:08-9")[0]["ref"] == "LUK 21:8-9"
    assert one("Luke 1:15-6")[0]["ref"] == "LUK 1:15-16"
    assert [x["ref"] for x in one("Matthew 26:58 / Luke 22:55")] == ["MAT 26:58", "LUK 22:55"]
    assert one("1 Corinthians 13:4")[0]["ref"] == "1CO 13:4" and one("1Co 13:4")[0]["book"] == "1CO"
    assert one("Psalm 23:1")[0]["book"] == "PSA" and one("Psalms 23:1")[0]["book"] == "PSA"
    assert one("Song of Songs 2:1")[0]["book"] == "SNG" and one("Song of Solomon 2:1")[0]["book"] == "SNG"
    assert one("Revelation of John 1:1")[0]["book"] == "REV"
    assert one("John 3:16")[0]["book"] == "JHN" and one("1 John 3:16")[0]["book"] == "1JN"
    p, u = parse_references("04:05-7 / The Temptation")
    assert p == [] and u
    p, u = parse_references("Luke 4:x")
    assert p == [] and u == ["LUK 4:x"], u
    for bad in ("Jesus in 2", "Peter in 12", "in 3 days", "SongofSongs 2:1", "Luke 3:3-2:1", "Genesis 5-2",
                "Luke 0:0", "Luke 1:25-5"):
        assert parse_references(bad)[0] == [] or parse_references(bad)[1], bad
    assert [x["ref"] for x in one("Genesis 35: 1-7; 9-15")] == ["GEN 35:1-7", "GEN 35:9-15"]
    assert one("Jude 3")[0]["ref"] == "JUD 1:3" and one("3 John 4")[0]["ref"] == "3JN 1:4"
    assert [x["ref"] for x in one("Genesis 1; 3")] == ["GEN 1", "GEN 3"]
    print("books.py self-test passed")
