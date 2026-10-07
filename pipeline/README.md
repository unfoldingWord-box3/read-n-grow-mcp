# Pipeline: canonical set and passage harvest

Run from the repo root, in order. Python 3 standard library only. Everything is written to `work/` (git-ignored).

| Step | Command | What it does | Writes | Time |
|------|---------|--------------|--------|------|
| 01 | `python3 pipeline/01_download.py` | Lists and downloads full-size and 610px pictures from the pCloud share (4 connections, resumable), hashes them | `work/full/`, `work/610/`, `work/manifest.csv`, `work/LICENSE` | about 10 min, 4 GB |
| 02 | `python3 pipeline/02_group.py` | One record per distinct picture (same full-size or same 610px bytes); links Commons files by SHA-1 | `work/commons_category.json`, `work/records_base.json` | about 2 min |
| 03 | `python3 pipeline/03_commons_refs.py` | Reads 6 Commons gallery pages, keeps references only | `work/commons_pages/`, `work/records_commons.json` | under 1 min |
| 04 | `nohup python3 pipeline/04_sttakla_refs.py > work/takla_fetch.log 2>&1 &` | Fetches St-Takla pages (1 per second), keeps the reference only | `work/takla_pages/` (raw cache, never commit), `work/takla_refs.json`, `work/records_takla.json` | about 50 min |
| 05 | `python3 pipeline/05_validate.py` | Checks references against file names, adds OBS links | `work/records.json`, `work/review_queue.csv` | seconds |

`--limit N` on step 04 fetches N pages and stops (quick test). Rerunning any step is safe: downloads and page caches resume.

Shared code is in `pipeline/lib/books.py` (book table, reference parser). Its self-test: `python3 pipeline/lib/books.py`.

Final record keys: `id, files, source_urls{filedn, commons}, width, height, sha256, sha256_610, passages[], also_in_obs[]`, plus a `_work` object (Commons titles and scene titles) that is dropped before publishing.
St-Takla caption text is never stored; only the parsed reference.
