"""Group identical pictures into one record each and link Commons files.

Reads work/manifest.csv (step 01); writes work/commons_category.json and work/records_base.json.
Usage: python3 pipeline/02_group.py
"""
import collections, csv, hashlib, json, sys, time, urllib.parse, urllib.request
from pathlib import Path

WORK = Path(__file__).resolve().parent.parent / "work"
UA = "read-n-grow-dataset/0.1 (benjamin.wright@unfoldingword.org)"
API = "https://commons.wikimedia.org/w/api.php"
CATEGORY = "Category:Media_contributed_by_the_Sweet_Publishing"
BASE = "https://filedn.com/lD0GfuMvTstXgqaJfpLL87S/sweet_images/jpg/"


def commons_files():
    """All files in the Commons category, with sha1; cached after the first run."""
    cache = WORK / "commons_category.json"
    if cache.exists():
        return json.loads(cache.read_text())
    pages, cont = [], {}
    while True:
        q = {"action": "query", "format": "json", "generator": "categorymembers", "gcmtitle": CATEGORY,
             "gcmtype": "file", "gcmlimit": "50", "prop": "imageinfo", "iiprop": "sha1|url|size", **cont}
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
        d = json.load(urllib.request.urlopen(req, timeout=60))
        pages += list(d.get("query", {}).get("pages", {}).values())
        if "continue" not in d:
            break
        cont = d["continue"]
        time.sleep(1)
    cache.write_text(json.dumps(pages))
    return pages


def sha1_of(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()


def main():
    rows = list(csv.DictReader(open(WORK / "manifest.csv")))
    full = {r["filename"]: r for r in rows if r["variant"] == "full" and int(r["size_bytes"]) > 0}
    small = {r["filename"]: r for r in rows if r["variant"] == "610"}  # includes 25 empty files on the share
    small_ok = {n: r for n, r in small.items() if int(r["size_bytes"]) > 0}
    # One picture = files sharing full-size bytes OR 610px bytes. Six full-size pairs differ by about 60
    # bytes of metadata while their 610px files are identical, so full-size bytes alone would split them.
    parent = {n: n for n in full}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    for key_of in (lambda n: full[n]["sha256"], lambda n: small_ok[n]["sha256"] if n in small_ok else None):
        seen = {}
        for name in full:
            k = key_of(name)
            if k is None:
                continue
            if k in seen:
                parent[find(name)] = find(seen[k])
            else:
                seen[k] = name
    members = collections.defaultdict(list)
    for name in full:
        members[find(name)].append(name)
    groups = {full[sorted(v)[0]]["sha256"]: v for v in members.values()}

    records, by_file = [], {}
    disagree = 0
    for sha, names in sorted(groups.items()):
        names.sort()
        r = full[names[0]]
        s610 = [small_ok[n]["sha256"] for n in names if n in small_ok]
        if len(set(s610)) > 1:
            disagree += 1
        rec = {
            "id": "sw-" + sha[:12], "files": names,
            "source_urls": {"filedn": f"{BASE}{r['folder']}/{urllib.parse.quote(names[0])}", "commons": None},
            "width": int(r["width"]), "height": int(r["height"]), "sha256": sha,
            "sha256_610": s610[0] if s610 else None,
            "passages": [], "also_in_obs": [], "_work": {},
        }
        records.append(rec)
        for n in names:
            by_file[n] = rec

    # Commons holds 610px-size files (research: sha1 equal to the 610px zip files), so try both variants.
    commons = commons_files()
    by_sha1 = collections.defaultdict(list)
    for p in commons:
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("sha1"):
            by_sha1[ii["sha1"]].append((p["title"], ii))
    hits = {"full": 0, "610": 0}
    matched_commons = set()
    for variant, table in (("full", full), ("610", small_ok)):
        for name, r in table.items():
            sha1 = sha1_of(WORK / variant / r["folder"] / name)
            for title, _ in by_sha1.get(sha1, []):
                rec = by_file[name]
                titles = rec["_work"].setdefault("commons_titles", [])
                if title not in titles:
                    titles.append(title)
                    hits[variant] += 1
                matched_commons.add(title)
    for rec in records:
        titles = sorted(rec["_work"].get("commons_titles", []))
        if titles:
            rec["_work"]["commons_title"] = titles[0]
            rec["source_urls"]["commons"] = "https://commons.wikimedia.org/wiki/" + titles[0].replace(" ", "_")

    json.dump(records, open(WORK / "records_base.json", "w"), indent=1)
    hist = collections.Counter(len(r["files"]) for r in records)
    print("full-size files:", len(full), "records:", len(records))
    print("files per record histogram:", dict(sorted(hist.items())))
    print("records whose 610px files disagree within a group:", disagree)
    print("Commons category files:", len(commons), "with sha1:", sum(len(v) for v in by_sha1.values()))
    print("Commons title matches by variant (full / 610):", hits)
    print("records with a Commons match:", sum(1 for r in records if r["source_urls"]["commons"]))
    unmatched = sorted({t for v in by_sha1.values() for t, _ in v} - matched_commons)
    print("Commons files with no local match:", len(unmatched))
    for t in unmatched:
        print("  ", t)


if __name__ == "__main__":
    main()
