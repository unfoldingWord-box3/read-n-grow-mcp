"""Build the review page for a set of tagged pictures (pilot now, flagged records in PR 4).

Step 1: python3 pipeline/review_data.py prep  --ids work/pilot.json --name pilot
        -> work/review/<name>/images/<id>.jpg (the picture to upload) and work/review/<name>/data.json
Step 2: upload the images to the artifact's asset store, save the result as work/review/<name>/imgs.json {id: url}
Step 3: python3 pipeline/review_data.py page --name pilot
        -> work/review/<name>/page.html (pipeline/review_page.html with the data filled in)
"""
import argparse, json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"

RUBRIC = [
    {"key": "ref", "label": "The reference contains the moment that is drawn"},
    {"key": "complete", "label": "Every listed object and action is really drawn"},
    {"key": "identity", "label": "Every named person is in the passage and fits the picture (pass if none)"},
    {"key": "count", "label": "Figure count is within about 20%, or \"crowd\" is right"},
    {"key": "summary", "label": "The summary is accurate"},
]
GATES = {"pilot": {"min_pass": 45, "ref_match": 0.95}}
TITLES = {"pilot": ("Pilot review: 50 pictures",
                    "Mark each of the five checks Pass or Fail. The pilot passes at 45 of 50, with no wrong identity and at least 95% of Commons-captioned references matching.")}


def load_items(ids_file, strata=None):
    records = {r["id"]: r for r in json.load(open(WORK / "records.json"))}
    spec = json.load(open(ids_file))
    spec_n = len(spec["ids"] if isinstance(spec, dict) else spec)
    ids = spec["ids"] if isinstance(spec, dict) else spec
    stratum = {i: s for s, v in (spec.get("strata", {}) if isinstance(spec, dict) else {}).items() for i in v}
    items = []
    for i in ids:
        t = json.load(open(WORK / "tags" / f"{i}.json"))
        if "tags" not in t:
            print("warning: no usable tags for", i)
            continue
        r = records[i]
        items.append({"id": i, "files": r["files"], "stratum": stratum.get(i, "flagged").replace("_", " "),
                      "answer_key": stratum.get(i) == "gospel_commons_key", "passages": r["passages"],
                      "proposed_passage": t.get("proposed_passage"), "tags": t["tags"], "flags": t["flags"], "image": t["image"]})
    if len(items) != spec_n:
        sys.exit(f"only {len(items)} of {spec_n} pictures are tagged; finish 06_tag.py first")
    return items


def prep(a):
    out = WORK / "review" / a.name
    (out / "images").mkdir(parents=True, exist_ok=True)
    items = load_items(a.ids)
    for it in items:
        name = it["image"]
        src = WORK / "610" / name[:2] / name
        if not src.exists() or src.stat().st_size == 0:
            src = WORK / "full" / name[:2] / name
        shutil.copy(src, out / "images" / f"{it['id']}.jpg")
    title, sub = TITLES.get(a.name, (a.name, ""))
    data = {"title": title, "subtitle": sub, "collection": a.name, "rubric": RUBRIC, "gate": GATES.get(a.name), "items": items}
    json.dump(data, open(out / "data.json", "w"))
    print(len(items), "pictures;", sum(1 for _ in (out / "images").iterdir()), "images in", out / "images")


def page(a):
    out = WORK / "review" / a.name
    data = (out / "data.json").read_text()
    imgs = (out / "imgs.json").read_text() if (out / "imgs.json").exists() else "{}"
    html = (Path(__file__).resolve().parent / "review_page.html").read_text()
    html = html.replace("/*DATA*/null", data.replace("</", "<\\/")).replace("/*IMGS*/{}", imgs)
    (out / "page.html").write_text(html)
    print("wrote", out / "page.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["prep", "page"])
    ap.add_argument("--ids")
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    prep(a) if a.mode == "prep" else page(a)
