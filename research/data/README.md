# Evidence files

Copied from the research session's scratch folder on 2026-10-07. They back the
numbers in `../2026-10-07-go-no-go-report.md`. Counts in the report are of data
rows (a file's header line is not counted); a few counts, such as the 2,331
byte-identical Commons files, came from checks that are not recorded here.

| File | What it is | Source and terms |
|---|---|---|
| `manifest.csv` | Every file in the 610px zip: name, size, dimensions, parsed book/chapter/frame | Derived from the Sweet images (CC BY-SA 3.0) |
| `rg_md5.txt` | MD5 per file on the pCloud host (3,004 files); the source of the 2,359 distinct pictures | Derived from the Sweet images |
| `sweet_dupgroups.json` | Groups of byte-identical files in the zip (SHA-1 to file names) | Derived |
| `zero_byte.txt` | The 25 empty zip files; the last lines are debug output | Derived |
| `commons_map.csv` | Wikimedia Commons file title to RG file name, with the caption text | Commons page text, CC BY-SA 4.0 |
| `commons_passage_captions.csv` | Gallery-page captions matched to RG files by identical bytes | Commons page text, CC BY-SA 4.0 |
| `takla_items.txt` | St-Takla item names (names only, no caption text) | Item names only |
| `rg_uncovered.txt` | RG files with no St-Takla item | Derived |
| `obs_to_sweet.csv` | Open Bible Stories frame to Sweet picture, by image matching | Derived |
| `vision_pilot_6img_results.jsonl`, `vision_pilot_tag.py` | The 6-image model comparison and its script | Our own work |

CSV files use CRLF line endings.

`fbi_all_sets.csv` (FreeBibleimages story-set descriptions) was removed from the repository after PR review because it republishes third-party text; it remains in the git history of PR #1. The report's section 2, F15 counts came from it.
