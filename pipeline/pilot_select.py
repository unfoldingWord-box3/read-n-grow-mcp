"""Pick the 50-picture pilot sample, stratified as in the plan; writes work/pilot.json {ids, strata}.
Deterministic (fixed seed). Usage: python3 pipeline/pilot_select.py"""
import json, random, re
from pathlib import Path

WORK = Path(__file__).resolve().parent.parent / "work"
rng = random.Random(20261007)
records = json.load(open(WORK / "records.json"))
by_file = {f: r for r in records for f in r["files"]}


def books_of(r):
    return {re.match(r"\d+_([A-Za-z0-9]+)_", f).group(1).lower() for f in r["files"]}


def num_of(f):
    return int(f[:2])


chosen, strata = [], {}


def take(name, pool, n):
    pool = [r for r in pool if r["id"] not in {c["id"] for c in chosen}]
    got = rng.sample(pool, min(n, len(pool)))
    chosen.extend(got)
    strata.setdefault(name, []).extend(r["id"] for r in got)
    if len(got) < n:
        print(f"warning: stratum {name} short: {len(got)} of {n}")


def has(r, pred):
    return any(pred(f) for f in r["files"])


def by_book(code):
    return [r for r in records if all(b == code for b in books_of(r))]


# edge cases first so other strata cannot take them
edge = [by_file["18_Jb_02_04a1_RG.jpg"], by_file["10_2Sa_31_03_RG.jpg"]]
edge += [r for r in records if has(r, lambda f: f.startswith("54_1Ti"))][:1]
zero = [l.split() for l in open(WORK.parent / "research/data/zero_byte.txt") if l.startswith("44_Ac")]
edge.append(by_file[zero[0][0]])
chosen.extend(edge)
strata["edge"] = [r["id"] for r in edge]

take("sparse_le_ps", by_book("le"), 3)
take("sparse_le_ps", by_book("ps"), 4)
take("crowded_acts", by_book("ac"), 8)
take("gospel_commons_key", [r for r in records if any(p["source"] == "commons" for p in r["passages"])
                            and all(num_of(f) in (40, 41, 42, 43) for f in r["files"])], 10)
ot = [r for r in records if all(num_of(f) <= 39 for f in r["files"]) and len(r["files"]) == 1
      and not has(r, lambda f: re.match(r"\d+_(Le|Ps|Ex_00|De)_", f))]
take("ot_narrative", [r for r in records if has(r, lambda f: f.startswith("02_Ex_00_"))], 2)
take("ot_narrative", [r for r in records if has(r, lambda f: f.startswith("05_De_"))], 2)
take("ot_narrative", ot, 4)
take("duplicates_across_books", [r for r in records if len(books_of(r)) > 1], 6)
take("epistles_revelation", [r for r in records if all(num_of(f) >= 45 for f in r["files"])], 4)
take("random", records, 3)

order = [i for s in strata.values() for i in s]
assert len(order) == len(set(order)) == 50, len(order)
json.dump({"ids": order, "strata": strata}, open(WORK / "pilot.json", "w"), indent=1)
for name, ids in strata.items():
    print(name, len(ids), [next(r for r in records if r["id"] == i)["files"][0][:-7] for i in ids])
