"""Attach Bible references from St-Takla.org picture pages (references only, never caption text).

Raw pages are cached in work/takla_pages/ (git-ignored, never committed). Only items that map to an RG file
are fetched. Reads work/records_commons.json; writes work/takla_refs.json and work/records_takla.json.
Usage: python3 pipeline/04_sttakla_refs.py [--limit N]     (fetch ~1 page/second; run with nohup)
"""
import argparse, json, re, sys, time, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from books import parse_references

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
UA = "read-n-grow-dataset/0.1 (benjamin.wright@unfoldingword.org)"
URL = "https://st-takla.org/Gallery/Bible/Illustrations/sm/{album}/sweet-bible-{code}.html"
ITEM = re.compile(r"^(\d?[A-Za-z]+)_(\d+)_(\d+)([a-z]?)$")
RG = re.compile(r"^(\d{2})_([A-Za-z0-9]+)_(\d{2,3})_(\d{2,3})([a-z]\d*)?_RG\.jpg$")
LDJSON = re.compile(r'<script type="application/ld\+json">(\{"@context".*?)</script>', re.S)
REF_IN_DESC = re.compile(r"\(((?:[1-3]\s?)?[A-Z][A-Za-z ]*?\s*\d+\s*:\s*\d[^()]*)\)")  # first English "(Book n: n)"


def fetch_page(album, code):
    """Cache one page; returns False if the server says 404."""
    fn = WORK / "takla_pages" / f"{code}.html"
    if fn.exists():
        return True
    if fn.with_suffix(".404").exists():
        return False
    fn.parent.mkdir(exist_ok=True)
    for i in range(5):
        time.sleep(1)
        try:
            req = urllib.request.Request(URL.format(album=album, code=code), headers={"User-Agent": UA})
            fn.write_bytes(urllib.request.urlopen(req, timeout=60).read())
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                fn.with_suffix(".404").write_text("")
                return False
            print(f"retry {code}: HTTP {e.code}", flush=True)
        except Exception as e:
            print(f"retry {code}: {type(e).__name__}", flush=True)
        time.sleep(2 ** i)
    print(f"gave up {code}", flush=True)
    return False


def reference_of(html):
    """First English bracketed reference in the JSON-LD description, as text; the caption is dropped."""
    m = LDJSON.search(html)
    if not m:
        return None
    try:
        desc = json.loads(m.group(1)).get("description", "")
        if not isinstance(desc, str):
            desc = ""
    except ValueError:
        return None
    r = REF_IN_DESC.search(desc)
    return r.group(1) if r else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="fetch at most N uncached pages (testing)")
    args = ap.parse_args()

    records = json.load(open(WORK / "records_commons.json"))
    rg_key = {}
    for rec in records:
        for f in rec["files"]:
            m = RG.match(f)
            if m:
                rg_key[(m.group(2).lower(), int(m.group(3)), m.group(4), m.group(5) or "")] = rec

    items = [l.strip() for l in open(ROOT / "research/data/takla_items.txt") if l.strip()]
    todo, no_rg = [], []
    for it in items:
        album, name = it.split("/sweet-bible-")
        m = ITEM.match(name)
        key = (m.group(1).lower(), int(m.group(2)), m.group(3).zfill(2), m.group(4)) if m else None
        if key in rg_key:
            todo.append((album, name, rg_key[key]))
        else:
            no_rg.append(name)

    fetched = 0
    for album, name, _ in todo:
        if args.limit and fetched >= args.limit:
            break
        if not (WORK / "takla_pages" / f"{name}.html").exists():
            fetched += 1
        fetch_page(album, name)
        if fetched and fetched % 100 == 0:
            print(f"fetched {fetched}", flush=True)
    if args.limit:
        print("limited run: fetched", fetched, "new pages; skipping parse")
        return

    refs, no_ref, failed, gained, missing = {}, [], [], set(), []
    for album, name, rec in todo:
        fn = WORK / "takla_pages" / f"{name}.html"
        if not fn.exists():
            missing.append(name)
            continue
        text = reference_of(fn.read_text(encoding="utf-8", errors="replace"))
        if not text:
            no_ref.append(name)
            continue
        passages, bad = parse_references(text)
        if bad or not passages:
            failed.append(name)  # a partly parsed reference would be misleading: attach nothing
            continue
        refs[name] = [p["ref"] for p in passages]
        have = {(p["book"], p["chapter"], p.get("chapter_end"), p["verse_start"], p["verse_end"]) for p in rec["passages"]}
        for p in passages:
            k = (p["book"], p["chapter"], p.get("chapter_end"), p["verse_start"], p["verse_end"])
            if k not in have:
                have.add(k)
                rec["passages"].append({**p, "source": "sttakla", "confidence": "medium"})
                gained.add(rec["id"])
    json.dump(refs, open(WORK / "takla_refs.json", "w"), indent=0)
    json.dump(records, open(WORK / "records_takla.json", "w"), indent=1)

    print("items listed:", len(items), "| mapped to an RG file:", len(todo), "| not mapped to an RG file:", len(no_rg))
    print("pages cached:", len(todo) - len(missing), "| unavailable (404/not fetched):", len(missing), missing[:20])
    print("items with a parsed reference:", len(refs), "| items with no bracketed reference:", len(no_ref))
    print("references that failed to parse (codes only):", failed)
    print("records gaining a St-Takla reference:", len(gained))


if __name__ == "__main__":
    main()
