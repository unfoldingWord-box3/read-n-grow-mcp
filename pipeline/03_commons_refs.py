"""Attach Bible references from Wikimedia Commons gallery captions.

Only the parsed references are kept (plus the scene title, as an unpublished working field).
Reads work/records_base.json; writes work/records_commons.json; caches pages in work/commons_pages/.
Usage: python3 pipeline/03_commons_refs.py
"""
import csv, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from books import parse_references

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
UA = "read-n-grow-dataset/0.1 (benjamin.wright@unfoldingword.org)"
LINE = re.compile(r"^(?:File:|Image:)?([^|\[\]]+?\.jpe?g)\s*\|(.*)$", re.I)
PAGE_BOOK = {"Gospel of Luke": "Luke", "Gospel of Matthew": "Matthew", "Gospel of John": "John", "Gospel of Mark": "Mark"}
HAS_REF = re.compile(r"\d+\s*:\s*\d+")


def get_page(title):
    fn = WORK / "commons_pages" / (re.sub(r"[^A-Za-z0-9]+", "_", title) + ".txt")
    if not fn.exists():
        fn.parent.mkdir(exist_ok=True)
        time.sleep(1)
        url = "https://commons.wikimedia.org/w/index.php?" + urllib.parse.urlencode({"title": title, "action": "raw"})
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        fn.write_text(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
    return fn.read_text()


def parse_caption(caption, page_book=""):
    """-> (passages, scene_title, unparsed pieces). page_book prefixes bookless refs like "04:05-7"."""
    caption = re.sub(r"<!--.*?-->", "", caption, flags=re.S)
    caption = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", caption).replace("''", "")
    caption = re.sub(r"<(?!br)[^>]*>", "", caption)
    passages, unparsed, title = [], [], None
    for piece in re.split(r"<br\s*/?>|\s+/\s+", caption):
        piece = piece.strip()
        if not piece:
            continue
        if page_book and re.match(r"^\d+\s*:", piece):
            piece = page_book + " " + piece
        p, u = parse_references(piece)
        if p and not u:
            passages += p
        elif p or HAS_REF.search(piece):  # partly parsed: keep nothing, so a lost reference is not hidden
            unparsed.append(piece)
        elif title is None:
            title = piece
    return passages, title, unparsed


def main():
    records = json.load(open(WORK / "records_base.json"))
    rows = list(csv.DictReader(open(ROOT / "research/data/commons_passage_captions.csv")))
    pages = sorted({r["page"] for r in rows})
    by_title = {}
    for rec in records:
        for t in rec["_work"].get("commons_titles", []):
            by_title[t] = rec
    by_file = {f: rec for rec in records for f in rec["files"]}

    gained, lines_seen, unparsed_all, unknown = set(), 0, [], set()
    for pg in pages:
        for line in get_page(pg).splitlines():
            m = LINE.match(line.strip())
            if not m:
                continue
            title = "File:" + m.group(1).strip().replace("_", " ")
            passages, scene, unparsed = parse_caption(m.group(2), PAGE_BOOK.get(pg, ""))
            lines_seen += 1
            for u in unparsed:
                unparsed_all.append((pg, title, u))
            rec = by_title.get(title)
            if not rec:
                if passages:
                    unknown.add(title)
                continue
            if scene:
                rec["_work"].setdefault("commons_scene_title", scene)
            for p in passages:
                if all(x["ref"] != p["ref"] for x in rec["passages"]):
                    rec["passages"].append({**p, "source": "commons", "confidence": "high"})
                    gained.add(rec["id"])

    json.dump(records, open(WORK / "records_commons.json", "w"), indent=1)

    expected = set()
    for r in rows:
        if parse_caption(r["caption"], PAGE_BOOK.get(r["page"], ""))[0]:
            for f in re.split(r"[;\s]+", r["rg_files_same_bytes"]):
                if f in by_file:
                    expected.add(by_file[f]["id"])
    print("gallery pages:", len(pages), "gallery lines:", lines_seen)
    print("records with Commons refs:", len(gained))
    print("research CSV implies pictures with a ref:", len(expected),
          "| only in CSV:", len(expected - gained), "| only here:", len(gained - expected))
    print("gallery files with a ref but no matching local record:", len(unknown))
    print("unparsed caption pieces:", len(unparsed_all))
    for pg, t, u in unparsed_all:
        print("  ", pg, "|", t[5:50], "|", u[:80])


if __name__ == "__main__":
    main()
