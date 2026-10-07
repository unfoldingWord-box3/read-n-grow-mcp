"""Download the Sweet Publishing pictures from the public pCloud share and write work/manifest.csv.

Usage: python3 pipeline/01_download.py [--limit N] [--skip-download]
Resumable: a file already present with the server's size is skipped.
"""
import argparse, csv, hashlib, json, re, struct, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://filedn.com/lD0GfuMvTstXgqaJfpLL87S/sweet_images/jpg/"
UA = "read-n-grow-dataset/0.1 (benjamin.wright@unfoldingword.org)"
WORK = Path(__file__).resolve().parent.parent / "work"
PATTERN = re.compile(r"^(\d{2})_([A-Za-z0-9]+)_(\d{2,3})_(\d{2,3})_RG\.jpg$")
LOOSE = re.compile(r"^(\d{2})_([A-Za-z0-9]+)_(\d{2,3})_(\d{2,3})([a-z]\d*)?_RG\.jpg$")


def fetch(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=60)
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"retry {url}: {e}", flush=True)
            time.sleep(2 ** i)


def listing(path):
    """Entries of a share directory, from the JSON embedded in the HTML page."""
    html = fetch(BASE + path).read().decode("utf-8")
    return json.loads(re.search(r"var directLinkData=(\{.*?\});", html, re.S).group(1))["content"]


def build_file_list():
    files = []  # (variant, folder, name, size)
    for d in listing(""):
        folder = d["name"]
        if not re.fullmatch(r"\d{2}", folder):
            continue
        for e in listing(folder + "/"):
            if "size" in e and e["name"].lower().endswith(".jpg"):
                files.append(("full", folder, e["name"], e["size"]))
        for e in listing(folder + "/610px/"):
            if "size" in e and e["name"].lower().endswith(".jpg"):
                files.append(("610", folder, e["name"], e["size"]))
        time.sleep(0.25)
    return files


def local_path(variant, folder, name):
    return WORK / variant / folder / name


def url_of(variant, folder, name):
    sub = "610px/" if variant == "610" else ""
    return f"{BASE}{folder}/{sub}{urllib.parse.quote(name)}"


def download(item):
    variant, folder, name, size = item
    dest = local_path(variant, folder, name)
    if dest.exists() and dest.stat().st_size == size:
        return "skip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    for i in range(5):
        try:
            with fetch(url_of(variant, folder, name)) as r, open(part, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)
            if part.stat().st_size != size:
                raise IOError(f"size {part.stat().st_size} != {size}")
            part.rename(dest)
            return "ok"
        except Exception as e:
            print(f"retry {variant}/{folder}/{name}: {e}", flush=True)
            time.sleep(2 ** i)
    return "fail"


def jpeg_dims(b):
    """(width, height) from the first start-of-frame marker, or None."""
    if b[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(b) - 9:
        if b[i] != 0xFF:
            i += 1
            continue
        m = b[i + 1]
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        if m == 0xFF:
            i += 1
            continue
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    return None


def write_manifest(files):
    rows = []
    for variant, folder, name, _ in sorted(files, key=lambda f: (f[0], f[1], f[2])):
        data = local_path(variant, folder, name).read_bytes()
        d = jpeg_dims(data)
        m = LOOSE.match(name)
        rows.append({
            "folder": folder, "filename": name, "variant": variant, "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "width": d[0] if d else "", "height": d[1] if d else "",
            "book_num": m.group(1) if m else "", "rg_code": m.group(2) if m else "",
            "chapter": int(m.group(3)) if m else "", "frame": m.group(4) if m else "",
            "suffix": (m.group(5) or "") if m else "",
            "matches_pattern": bool(PATTERN.match(name)),
        })
    with open(WORK / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="download only the first N files (testing)")
    ap.add_argument("--skip-download", action="store_true", help="only rebuild manifest.csv")
    args = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    lic = WORK / "LICENSE"
    if not lic.exists():
        lic.write_bytes(fetch(BASE + "LICENSE").read())
    cache = WORK / "listing.json"
    if cache.exists():
        files = [tuple(x) for x in json.loads(cache.read_text())]
    else:
        files = build_file_list()
        cache.write_text(json.dumps(files))
    if args.limit:
        files = files[:args.limit]
    print(f"{len(files)} files listed", flush=True)
    if not args.skip_download:
        t = time.time()
        with ThreadPoolExecutor(4) as ex:
            counts = {}
            for n, res in enumerate(ex.map(download, files), 1):
                counts[res] = counts.get(res, 0) + 1
                if n % 200 == 0:
                    print(f"{n}/{len(files)} {counts} {time.time() - t:.0f}s", flush=True)
        print("download:", counts, f"{time.time() - t:.0f}s", flush=True)
        if counts.get("fail"):
            sys.exit("some downloads failed; rerun to resume")
    rows = write_manifest(files)
    for v in ("full", "610"):
        vr = [r for r in rows if r["variant"] == v]
        print(f"{v}: {len(vr)} files, zero-byte {sum(r['size_bytes'] == 0 for r in vr)}")
        print("  non-pattern:", [r["filename"] for r in vr if not r["matches_pattern"]])
        print("  44_Ac_05_17_RG.jpg present:", any(r["filename"] == "44_Ac_05_17_RG.jpg" for r in vr))


if __name__ == "__main__":
    main()
