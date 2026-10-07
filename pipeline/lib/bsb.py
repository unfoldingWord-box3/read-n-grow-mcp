"""Berean Standard Bible text (public domain), used only inside tagging prompts, never stored in the dataset."""
import collections, re, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import books

URL = "https://bereanbible.com/bsb.txt"
PATH = Path(__file__).resolve().parent.parent.parent / "work" / "bsb" / "bsb.txt"
_LINE = re.compile(r"^(.+?) (\d+):(\d+)\t(.*)$")
_cache = None


def load():
    """{(usfm, chapter): {verse: text}}; downloads the plain-text file on first use."""
    global _cache
    if _cache is None:
        if not PATH.exists():
            PATH.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(URL, headers={"User-Agent": "read-n-grow-dataset/0.1 (benjamin.wright@unfoldingword.org)"})
            PATH.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        _cache = collections.defaultdict(dict)
        for line in PATH.read_text(encoding="utf-8-sig").splitlines():
            m = _LINE.match(line)
            if m:
                _cache[(books._book_of(m.group(1)), int(m.group(2)))][int(m.group(3))] = m.group(4).strip()
    return _cache


def chapter_text(book, ch):
    return " ".join(f"{v} {t}" for v, t in sorted(load().get((book, ch), {}).items()))


def passage_text(p):
    """Verse text for a passage dict from books.parse_references; whole chapters and cross-chapter ranges included."""
    b, ch = p["book"], p["chapter"]
    ch_end = p.get("chapter_end") or ch
    out = []
    for c in range(ch, ch_end + 1):
        verses = load().get((b, c), {})
        lo = p["verse_start"] if (c == ch and p["verse_start"] is not None) else 1
        hi = p["verse_end"] if (c == ch_end and p["verse_end"] is not None) else (max(verses) if verses else 0)
        out += [f"{v} {verses[v]}" for v in range(lo, hi + 1) if v in verses]
    return " ".join(out)


if __name__ == "__main__":
    assert len(load()) > 1100 and sum(len(v) for v in load().values()) == 31102
    assert "lowered the paralytic" in passage_text({"book": "MRK", "chapter": 2, "verse_start": 3, "verse_end": 5})
    assert passage_text({"book": "JUD", "chapter": 1, "verse_start": 3, "verse_end": 3}).startswith("3 ")
    assert "Gen" not in passage_text({"book": "GEN", "chapter": 1, "verse_start": None, "verse_end": None})[:5]
    print("bsb.py self-test passed")
