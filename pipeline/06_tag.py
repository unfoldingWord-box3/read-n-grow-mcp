"""Tag pictures with a vision model: what is visibly drawn, plus a check of the harvested passage references.

Reads work/records.json (step 05) and the Berean Standard Bible text (public domain, prompt only, never stored).
Writes one file per picture to work/tags/<id>.json; reruns skip pictures already tagged.
Usage: python3 pipeline/06_tag.py --ids work/pilot.json [--model M] [--workers 4] [--limit N]
       python3 pipeline/06_tag.py --all
Needs OPENROUTER_API_KEY in the environment or ~/.config/ai-keys.env.
"""
import argparse, base64, concurrent.futures, datetime, json, os, re, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bsb
from books import NAMES, parse_references, usfm_from_rg
from schema import TAGS_SCHEMA, validate

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
PROMPT_VERSION = "v1"
DEFAULT_MODEL = "anthropic/claude-sonnet-5.5"
MAX_VERSE_CHARS = 12000  # whole chapters fit; only very long passages are cut

PROMPT = """You are tagging a hand-drawn Bible illustration from the Sweet Publishing "Read 'n Grow Picture Bible" (Jim Padgett).
The picture file name(s) say it was filed under: {files}. The last number in a file name is a frame count, NOT a verse number.

{passage_block}

Rules:
- Describe only what is visibly drawn. Never invent details; if something is not clearly drawn, leave it out or list it under "uncertain".
- Name a biblical person in "identity" only if that exact name appears in the verse text above AND the drawing fits it; then basis is "passage". Otherwise identity is null, basis is "none", and "label" is a generic visual description such as "man on a mat". Never name someone from appearance alone.
- figure_count is the number of people drawn, or the string "crowd" when there are more than about 20 or they cannot be counted.
{reference_rule}
Return ONLY one JSON object with these keys, no other text:
{{"scene_summary": "one sentence on what is drawn",
 "people": [{{"label": "generic visual label", "identity": "name from the verse text or null", "basis": "passage|none"}}],
 "figure_count": 0, "places": ["..."], "objects": ["..."], "actions": ["..."],
 "setting": "indoor|outdoor|mixed", "time_of_day": "day|night|unclear", "mood": "one word",
 "uncertain": ["things you were unsure about"],
 "passage_check": {{"verdict": "agrees|partly|disagrees|no_reference", "note": "one short sentence"}}{proposed_key}}}"""

WITH_REFS = """Harvested passage references for this picture, with verse text from the Berean Standard Bible (the picture shows one moment inside or near these verses):
{blocks}"""
NO_REFS = """No passage reference is known for this picture. Its file name places it in {book_ch}. Berean Standard Bible text of that chapter:
{blocks}"""
RULE_WITH = '- passage_check.verdict: "agrees" if the drawn moment is inside one of the references above, "partly" if it is near them, "disagrees" if it clearly shows something else. Do NOT propose a different reference.'
RULE_NO = '- There is no verified passage, so every "identity" must be null (use generic labels). There is no reference to check, so passage_check.verdict is "no_reference". Set "proposed_passage" to your best reference for the drawn moment, e.g. "Mark 2:3-4", or null if you cannot tell.'


def api_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    env = Path.home() / ".config/ai-keys.env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            line = line.removeprefix("export ").strip()
            if line.startswith("OPENROUTER_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("\"'")
    if not key:
        sys.exit("OPENROUTER_API_KEY not found")
    return key


def clip(text):
    return text if len(text) <= MAX_VERSE_CHARS else text[:MAX_VERSE_CHARS].rsplit(" ", 1)[0] + " [...]"


def build_prompt(rec):
    files = ", ".join(rec["files"])
    if rec["passages"]:
        blocks = []
        for p in rec["passages"]:
            text = bsb.passage_text(p)
            blocks.append(f"- {NAMES[p['book']]} {p['ref'].split(' ', 1)[1]}: {clip(text)}")
        return PROMPT.format(files=files, passage_block=WITH_REFS.format(blocks="\n".join(blocks)),
                             reference_rule=RULE_WITH, proposed_key="")
    pairs = sorted({(re.match(r"\d+_([A-Za-z0-9]+)_(\d+)", f).group(1), int(re.match(r"\d+_[A-Za-z0-9]+_(\d+)", f).group(1)))
                    for f in rec["files"]})
    blocks, labels = [], []
    for code, ch in pairs:
        usfm = usfm_from_rg(code)
        if usfm and ch:
            blocks.append(f"{NAMES[usfm]} {ch}: {clip(bsb.chapter_text(usfm, ch))}")
            labels.append(f"{NAMES[usfm]} chapter {ch}")
    return PROMPT.format(files=files, passage_block=NO_REFS.format(book_ch=" or ".join(labels) or "an unknown chapter",
                         blocks="\n".join(blocks) or "(none)"), reference_rule=RULE_NO,
                         proposed_key=',\n "proposed_passage": "reference or null"')


def pick_image(rec):
    """Prefer a non-empty 610px file; fall back to the full-size file."""
    for variant in ("610", "full"):
        for f in rec["files"]:
            p = WORK / variant / f[:2] / f
            if p.exists() and p.stat().st_size > 0:
                return p
    raise FileNotFoundError(rec["files"])


def call(model, prompt, image, key, max_tokens=4000):
    b64 = base64.b64encode(image.read_bytes()).decode()
    body = {"model": model, "max_tokens": max_tokens, "usage": {"include": True},
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}]}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=240))
    return r["choices"][0]["message"]["content"], r.get("usage", {}), r["choices"][0].get("finish_reason")


def parse_json(text):
    obj, _ = json.JSONDecoder().raw_decode(text[text.index("{"):])
    return obj


_SMALL = {"the", "of", "and"}


def is_named_in(identity, text):
    """True if every capitalised word of the identity appears, capitalised, as a whole word in the verse text.
    Case-sensitive on purpose: "woman" and "angel" are descriptions, not names."""
    words = [w for w in re.findall(r"[A-Za-z]+", re.sub(r"\(.*?\)", "", identity)) if w.lower() not in _SMALL]
    if not words or not all(w[0].isupper() for w in words):
        return False
    return all(re.search(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", text) for w in words)


def enforce_identities(tags, rec):
    """An identity survives only if its name appears in the verse text of one of the picture's passages."""
    text = " ".join(bsb.passage_text(p) for p in rec["passages"])
    removed = 0
    for person in tags["people"]:
        ident = (person.get("identity") or "").strip()
        if ident and not (person["basis"] == "passage" and is_named_in(ident, text)):
            removed += 1
            person["identity"], person["basis"] = None, "none"
        elif not ident:
            person["identity"], person["basis"] = None, "none"
    if removed:
        tags["uncertain"].append(f"{removed} identity guess(es) removed: the name is not in the verse text")
    return removed


def valid_proposal(text, rec):
    """A model-proposed reference counts only if it is one passage in a book the file names point to."""
    ps, un = parse_references(text)
    file_books = {usfm_from_rg(re.match(r"\d+_([A-Za-z0-9]+)_", f).group(1)) for f in rec["files"]}
    if len(ps) == 1 and not un and ps[0]["book"] in file_books and bsb.load().get((ps[0]["book"], ps[0]["chapter"])):
        return {**ps[0], "source": "vision", "confidence": "low"}
    return None


def tag_one(rec, model, key):
    """Tag one picture; a failure writes nothing, so a rerun retries it."""
    out = WORK / "tags" / f"{rec['id']}.json"
    if out.exists():
        return "skip"
    prompt, image = build_prompt(rec), pick_image(rec)
    cost, tokens, err, tags, finish, note = 0.0, 0, None, None, None, ""
    for attempt in range(3):
        try:
            text, usage, finish = call(model, prompt + note, image, key)
            cost += usage.get("cost") or 0
            tokens += usage.get("completion_tokens") or 0
            tags = parse_json(text)
            errs = validate(tags, TAGS_SCHEMA)
            if not errs:
                break
            err, tags = "; ".join(errs[:5]), None
            note = f"\n\nYour previous answer was invalid: {err}. Return valid JSON only."
        except ValueError as e:  # unparseable JSON: tell the model
            err, tags = f"{type(e).__name__}: {e}"[:300], None
            note = "\n\nYour previous answer was not valid JSON. Return one JSON object only."
        except Exception as e:  # network or HTTP error: wait, do not blame the model
            err, tags = f"{type(e).__name__}: {e}"[:300], None
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    if tags is None:
        print(f"FAILED {rec['id']} {rec['files'][0]}: {err}", flush=True)
        return "failed"
    removed = enforce_identities(tags, rec)
    proposed = None
    if not rec["passages"] and tags.get("proposed_passage"):
        proposed = valid_proposal(tags["proposed_passage"], rec)
    if not rec["passages"] or not proposed:
        tags.pop("proposed_passage", None)
    flags = []
    if removed:
        flags.append("identity_removed")
    if rec["passages"] and tags["passage_check"]["verdict"] != "agrees":
        flags.append("passage_" + tags["passage_check"]["verdict"])
    if not rec["passages"]:
        flags.append("vision_reference" if proposed else "no_reference")
    if tags["uncertain"]:
        flags.append("uncertain")
    rec_out = {"id": rec["id"], "image": image.name, "cost": cost, "completion_tokens": tokens, "finish_reason": finish,
               "tags": tags, "proposed_passage": proposed, "flags": flags,
               "tagged_by": {"model": model, "date": datetime.date.today().isoformat(), "prompt_version": PROMPT_VERSION}}
    (WORK / "tags").mkdir(exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    tmp.write_text(json.dumps(rec_out, indent=1))
    tmp.rename(out)
    return "ok"


def safe_tag(rec, model, key):
    try:
        return tag_one(rec, model, key)
    except Exception as e:  # one bad record (missing image, odd name) must not end the run
        print(f"ERROR {rec['id']}: {type(e).__name__}: {e}", flush=True)
        return "error"


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ids", help="JSON file with a list of record ids, or an object with an 'ids' list")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    records = json.load(open(WORK / "records.json"))
    if a.ids:
        want = json.load(open(a.ids))
        want = want["ids"] if isinstance(want, dict) else want
        by_id = {r["id"]: r for r in records}
        records = [by_id[i] for i in want]
    if a.limit:
        records = records[:a.limit]
    key = api_key()
    bsb.load()  # load once before the worker threads start
    counts, t0 = {}, time.time()
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for i, status in enumerate(ex.map(lambda r: safe_tag(r, a.model, key), records), 1):
            counts[status] = counts.get(status, 0) + 1
            if i % 25 == 0 or i == len(records):
                print(f"{i}/{len(records)} {counts} {time.time() - t0:.0f}s", flush=True)
    files = [json.load(open(WORK / "tags" / f"{r['id']}.json")) for r in records if (WORK / "tags" / f"{r['id']}.json").exists()]
    print(f"tagged: {len(files)} of {len(records)} (rerun to retry the rest); cost this and earlier runs $%.3f" % sum(f["cost"] for f in files))
    flags = {}
    for f in files:
        for fl in f["flags"]:
            flags[fl] = flags.get(fl, 0) + 1
    print("flags:", flags)


if __name__ == "__main__":
    main()
