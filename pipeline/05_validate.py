"""Check references against file names, attach OBS links, write work/records.json and work/review_queue.csv.

Reads work/records_takla.json (step 04). Usage: python3 pipeline/05_validate.py
"""
import collections, csv, json, random, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from books import usfm_from_rg

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
RG = re.compile(r"^(\d{2})_([A-Za-z0-9]+)_(\d{2,3})_(\d{2,3})([a-z]\d*)?_RG\.jpg$")
STRICT = re.compile(r"^\d{2}_[A-Za-z0-9]+_\d{2,3}_\d{2,3}_RG\.jpg$")
KNOWN_BAD = {"10_2Sa_31_03_RG.jpg"}  # probably 1 Samuel 31; kept under 2Sa, flagged for review
WEAK_MARGIN = 0.1


def file_book_chapter(name):
    m = RG.match(name)
    return (usfm_from_rg(m.group(2)), int(m.group(3))) if m else (None, None)


def passage_reason(passage, files):
    """None if the passage fits one of the files, else 'ref_mismatch' or 'chapter_out_of_range'."""
    book_seen = False
    chapters = {passage["chapter"], passage.get("chapter_end", passage["chapter"])}
    for f in files:
        book, ch = file_book_chapter(f)
        if book != passage["book"]:
            continue
        book_seen = True
        if ch == 0 or chapters & {ch, ch + 1}:
            return None
    return "chapter_out_of_range" if book_seen else "ref_mismatch"


def main():
    records = json.load(open(WORK / "records_takla.json"))
    by_file = {f: r for r in records for f in r["files"]}
    queue = []

    def add(rec, reason, passages=()):
        queue.append({
            "id": rec["id"], "files": ";".join(rec["files"]), "reason": reason,
            "passages": ";".join(p["ref"] for p in passages),
            "sources": ";".join(sorted({p["source"] for p in passages})),
            "chapter0": any(file_book_chapter(f)[1] == 0 for f in rec["files"]),
        })

    for rec in records:
        bad = collections.defaultdict(list)
        for p in rec["passages"]:
            reason = passage_reason(p, rec["files"])
            if reason:
                p["confidence"] = "low"
                bad[reason].append(p)
        for reason in ("ref_mismatch", "chapter_out_of_range"):
            if bad[reason]:
                add(rec, reason, bad[reason])
        if not rec["passages"]:
            add(rec, "no_reference")
        if any(not STRICT.match(f) or f in KNOWN_BAD for f in rec["files"]):
            add(rec, "bad_filename", rec["passages"])

    # OBS (Open Bible Stories) frames that are crops of these pictures
    obs_skipped = obs_unknown = obs_linked = 0
    for row in csv.DictReader(open(ROOT / "research/data/obs_to_sweet.csv")):
        if float(row["margin"]) < WEAK_MARGIN:
            obs_skipped += 1
            continue
        recs = {id(by_file[f]): by_file[f] for f in row["all_identical_rg"].split() if f in by_file}
        if not recs:
            obs_unknown += 1
            continue
        frame = re.sub(r"^obs-en-|\.jpg$", "", row["obs"])
        for rec in recs.values():
            if frame not in rec["also_in_obs"]:
                rec["also_in_obs"].append(frame)
                obs_linked += 1
    for rec in records:
        rec["also_in_obs"].sort()

    json.dump(records, open(WORK / "records.json", "w"), indent=1)
    with open(WORK / "review_queue.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "files", "reason", "passages", "sources", "chapter0"])
        w.writeheader()
        w.writerows(queue)

    n = len(records)
    withp = [r for r in records if r["passages"]]
    print(f"total records: {n}")
    print(f"with at least one passage: {len(withp)} ({100 * len(withp) / n:.1f}%)")
    print("by source (records):", dict(collections.Counter(s for r in withp for s in {p["source"] for p in r["passages"]})))
    print("by confidence (passages):", dict(collections.Counter(p["confidence"] for r in records for p in r["passages"])))
    print("review queue:", len(queue), dict(collections.Counter(q["reason"] for q in queue)))
    print("no_reference rows that are chapter-0 pictures:", sum(1 for q in queue if q["reason"] == "no_reference" and q["chapter0"]))
    print(f"OBS: {obs_linked} links added, {obs_skipped} weak (margin < {WEAK_MARGIN}) skipped, {obs_unknown} unknown files")
    print("sample of 10 records:")
    for r in random.Random(0).sample(records, 10):
        ps = ", ".join(f"{p['ref']} [{p['source']}/{p['confidence']}]" for p in r["passages"]) or "(none)"
        print(f"  {r['id']} files={r['files']} passages={ps} obs={r['also_in_obs']}")


if __name__ == "__main__":
    main()
