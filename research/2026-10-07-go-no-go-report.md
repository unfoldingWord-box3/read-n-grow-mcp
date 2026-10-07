# Read 'n Grow illustrations dataset and MCP server: go/no-go research report

Date: 2026-10-07. Prepared for Benjamin (project lead). Research only; nothing was built. Evidence files are in `research/data/` (listed in section 8).

## 1. Verdict

**Go with changes.** Most of the passage data already exists and costs nothing to harvest, and the vision tagging is cheap (about $25 for the whole set), so this is worth building. The project needs a narrower pitch and a different first step, though. unfoldingWord's own fia-mcp server already returns images by passage, so this project's new contribution is narrative scene illustrations and search by what a picture shows. The first step is to harvest the existing references and deduplicate the files before any AI tagging.

Four changes to the plan as written:

1. Treat the dataset as about 2,360 distinct pictures, each linked to several passages, not 3,003 files. About a fifth of the files are byte-for-byte copies of other files (F7).
2. Take passage references from data that already exists (Wikimedia Commons for the Gospels, St-Takla.org for the rest), and use the vision model to check them and to add the visible-element tags (F9, F10).
3. Host copies on Cloudflare R2. Do not depend on the pCloud (filedn.com) share or on Commons hotlinking (F22).
4. Plan for BT Servant showing images on WhatsApp and web only at first. Telegram and Signal need gateway work, and the Signal gateway has a credential leak to fix before it sends outside images (F20, F21).

## 2. Findings

Confidence is high, medium or low. "Read" means I or an agent saw it in the source; "inferred" means it is our conclusion from what we read.

### Prior art (Q1)

**F1. P1 is false as written: two MCP servers already return Bible images by passage, and BT Servant uses both.**
- Claim: unfoldingWord/fia-mcp has a tool `fia_get_pericope_media` that returns "maps, images, and videos for a pericope" (a pericope is one story-sized passage unit). klappy/aquifer-mcp (public at `https://aquifer.klappy.dev/mcp`) serves the Aquifer catalog, which includes UBS Images (1,054 items) and FIA Images (1,743), nearly all tagged with passages.
- Evidence: fia-mcp README, lines 61-66 (read with `gh api`); bt-servant-worker issue #166 shows a live response with FIA image links for Matthew 4:1-11; bt-servant-worker `tests/fixtures/aquifer-list-eng.md` lines 48-55; `aquifer.klappy.dev/health` returned HTTP 200 today.
- How to verify: `gh api repos/unfoldingWord/fia-mcp/contents/README.md -H "Accept: application/vnd.github.raw"`.
- Confidence: high.

**F2. What those servers do not do is the actual gap.** Their images are realia (objects, plants, places: "Roof", "Sleeping Mat"), maps and diagrams, plus a few Tissot paintings. None of them serves narrative scene illustrations, and the Aquifer search matches titles only, not what is drawn. There are no Sweet or Padgett images in the English UBS or FIA data. Source: BibleAquifer/UBSImages and FIAImages JSON, plus live `search`/`browse` calls against aquifer.klappy.dev. Confidence: high for English; other languages not checked.

**F3. Aquifer's passage search did not return images in testing.** `search "Luke 5:19"` returned 12 text articles and no images, even though the UBS "Roof" image is tagged Luke 5:19. Source: live calls against aquifer.klappy.dev. Confidence: medium (one tester, a few queries).

**F4. No other Bible MCP server returns images.** We checked 16 unique servers in the official registry, 20 on Glama, 11 on PulseMCP, Smithery, mcp.so and mcpservers.org; all serve text, audio links or knowledge graphs (search log, section 7). Confidence: medium-high. Registry listings were read partly through a summarizing fetch tool.

**F5. Several people have already tried to index Sweet images by passage, which shows the need and also shows how easy it is to get wrong.**
- git.door43.org/mikey/ImageDB (2019) maps 2,990 RG files to verses, but its own commit message says the verses were guessed from the number of images, and every Mark 2 image is titled "Matthew called".
- WhatsNewSaes/pockle `tools/caption_sweet.py` captions the Commons Sweet images with a vision model. This is the closest prior method, but its output is not committed.
- BadBull22/bible and SuyangLiuPaul/Yahwehs-Sword index the images by chapter only.
- jaedenschafer/bible-art-scripture-index (CC0) maps 5,911 museum artworks to passages and contains no Sweet images.

Confidence: high.

**F6. Commons structured data barely covers these files.** Only 112 of 2,358 files have "depicts" (P180) statements, and those are generic ("figure", "Adam and Eve"). File descriptions are template text naming the chapter only. Source: CirrusSearch `haswbstatement:P180` within the category, plus `wbgetentities` on sample files. Confidence: high.

### Inventory (Q2)

**F7. The set is 3,003 files but only about 2,360 distinct pictures.**
- Claim: the 610px zip has 3,003 .jpg entries, matching the website's per-book total (P2 confirmed). 25 entries are empty (0 bytes). Among the 2,978 real files there are 425 groups of byte-identical copies, leaving 2,341 distinct pictures in the zip. The pCloud host has 3,004 files and 2,359 distinct pictures by MD5 checksum. Example: `41_Mk_02_04_RG` and `42_Lk_05_02_RG` are the same file, because the same picture serves parallel Gospel accounts.
- Evidence: `research/data/manifest.csv`, `sweet_dupgroups.json`, `rg_md5.txt`. I checked the Mk_02_04 = Lk_05_02 pair myself in `rg_md5.txt`.
- How to verify: `unzip -l` on the zip; hash the files.
- Confidence: high.

**F8. P3 needs correcting: the last number in a file name is a frame count, not a verse.** The pattern is `BB_Code_CC_FF_RG.jpg`: book number, book code, chapter, frame. 365 of 386 chapters run 01..n with no gaps. Exodus 2 has frames up to 28 but only 25 verses. Frame order does not always follow verse order (Lk_01_04 shows 1:19-20 and Lk_01_05 shows 1:18). The "chapter" is where a story segment starts: 41_Mk_02_23 shows Mark 3:1. No file name has a verse range.

Edge cases:
- Chapter 00 intro frames: `02_Ex_00_01..23` and `05_De_00_01..08`.
- Two names with a letter suffix: `18_Jb_02_04a1` and `18_Jb_02_06a1`.
- An impossible chapter: `10_2Sa_31_03`, since 2 Samuel has 24 chapters. It is probably 1 Samuel 31.
- A three-digit chapter: `19_Ps_119_01`.
- Mixed capitals: `02_EX_05_09`, `42_LK_01_06`, `42_LK_04_22`.
- Two `54_1Ti` files sit in the Romans folder.

Psalms and Epistles follow the same pattern. Twenty worked examples are in the inventory notes behind this report. Source: `research/data/manifest.csv`. Confidence: high.

**F9. Open-licensed verse references exist for the Gospels.** The Commons gallery page "Gospel harmony (Sweet Publishing)" and related gallery pages caption each Gospel picture with a reference and a title, for example "Luke 01:05-7 / Announcement of the Baptist's birth". Matched by identical bytes, that covers 572 distinct pictures (24% of the set and about 97% of Gospel files). Commons page text is CC BY-SA 4.0 (Commons siteinfo API, checked today). Source: `research/data/commons_passage_captions.csv`. Confidence: high.

**F10. St-Takla.org has a verse reference for 94% of the pictures, but its license is unclear.**
- Claim: St-Takla.org, a Coptic church site, hosts the Sweet set under matching names (`sweet-bible-Mt_08_14` = `40_Mt_08_14_RG`). Each page carries a caption that ends in a reference. It covers 2,209 of 2,359 distinct pictures. With Commons added, 2,282 pictures (97%) have a reference and 77 have none.
- Evidence: I fetched the Mt_08_14 page myself. Its JSON-LD description quotes the verse and ends "(Matthew 8: 33)". Coverage was computed from `takla_items.txt`, `rg_uncovered.txt` and `commons_passage_captions.csv`.
- Problems: the page states only `"copyrightNotice":"St-Takla.org"`, and we found no license. The caption quotes Bible text, and the one I read is in the wording of a copyrighted modern translation (my inference from the wording). Many captions copy FreeBibleimages slide text word for word. In a 29-item sample, 2 references disagreed with the file's book or chapter.
- How to verify: fetch any `st-takla.org/Gallery/Bible/Illustrations/sm/<book>/sweet-bible-<code>.html` page.
- Confidence: high on coverage, low on whether reuse is allowed. Taking only the bare reference, which is a fact, is lower risk. That is an inference, not legal advice.

**F11. Commons holds almost the whole distinct set.** "Media contributed by the Sweet Publishing" holds 2,358 files (the category count of 2,395 also includes 35 subcategories and 2 pages). 2,331 of those are byte-identical to zip pictures. Only 10 distinct zip pictures are missing from Commons. Commons numbering differs from RG for Exodus and Deuteronomy, so mapping must use hashes, not names. The drop from 2,898 (2014) to 2,358 fits the removal of duplicates, but we did not check the 2014 history. Source: `research/data/commons_map.csv`. Confidence: high for the counts, low for the reason behind the drop.

**F12. Download defects.** The 25 empty files are fine on pCloud at full size. `44_Ac_05_17_RG` is on the website but missing from the zip. The zip also carries 3,049 macOS junk files. Source: `research/data/zero_byte.txt`. Confidence: high.

**F13. P6 is confirmed, with small corrections.** Medium zip: 464,738,208 bytes. High-quality zip: 3,979,442,635 bytes. Both are hosted on filedn.com (a pCloud public folder), not on unfoldingword.org. OBS 360px zip: 37.7 MB. OBS 2160px zip: 807 MB (P6 said about 755 MB). Source: `curl -sI`. Confidence: high.

**F14. OBS has 598 frames, and nearly all are cropped Sweet pictures.** At least 560 of the 598 frames match one Sweet picture (about 523 distinct pictures). OBS references are per story only ("A Bible story from: Genesis 1-2"), and no published frame-to-Sweet mapping exists that we could find. `research/data/obs_to_sweet.csv` is now one. Confidence: medium-high, because a crop-tolerant image matcher was used and one pair was checked by eye.

**F15. FreeBibleimages (FBI) has 213 Sweet story sets (3,461 slides).** Each set carries a passage range and per-slide description text. The slide images are recropped to 4:3 and color-adjusted, and their names do not contain the RG code. Source: data embedded in freebibleimages.org/illustrations/?search=sweet, decoded to `research/data/fbi_all_sets.csv`. Confidence: high.

### Licensing (Q3). This is not legal advice.

**F16. P4 needs correcting: OBS images are CC BY-SA 3.0, not 4.0.**
- Claim: the OBS text is CC BY-SA 4.0. The OBS images are Sweet images under CC BY-SA 3.0.
- Evidence: the en_obs LICENSE.md says "All images used in these stories are © Sweet Publishing" under a CC BY-SA 3.0 license (https://git.door43.org/unfoldingWord/en_obs/raw/branch/master/LICENSE.md). openbiblestories.org/license says the same.
- Confidence: high.

Other licensing points, each read from the source:
- Sweet images: CC BY-SA 3.0 Unported. The uW page asks for credit to "Sweet Publishing" with a link to sweetpublishing.com (unfoldingword.org/sweet-publishing). Commons uses the credit "Distant Shores Media/Sweet Publishing", and the file pages say "Biblical illustrations by Jim Padgett, courtesy of Sweet Publishing, Ft. Worth, TX, and Gospel Light, Ventura, CA. Copyright 1984." Confidence: high.
- sweetpublishing.com now loads a church-supply store (Ruthart, Inc.), and the dsmedia.org link in the Commons template does not load. Confidence: medium (checked from one machine).
- Combining 3.0 and 4.0: under CC's compatibility rules, adaptations of BY-SA 3.0 material may be licensed BY-SA 4.0, and only in that direction. Each Sweet image keeps its 3.0 terms. Source: creativecommons.org/compatible-licenses. Confidence: high.
- FreeBibleimages: no evidence of AI editing. "A.I. adaptations" on their pages is a permission checkbox. They call their files "digitally adjusted compilations" and claim copyright on them. They also add terms the CC license does not have ("faithful to the Biblical account"; no reposting full sets). P4's plan to source from uW instead is correct. Source: freebibleimages.org/help/reuse/ and set pages. Confidence: high.
- Theographic: CC BY-SA 4.0, but its own bibliography lists TIPNR (a STEPBible names dataset) as "CC BY-NC", a non-commercial license. STEPBible's current README says CC BY 4.0. Source: robertrouse/theographic-bible-metadata `docs/data-source-bibliography.md`. Confidence: high on what the files say; the legal effect is unknown.
- Vision model terms: Anthropic's Commercial Terms say the customer owns its outputs, with a ban on using them to train competing models (anthropic.com/legal/commercial-terms). Google's and OpenAI's terms are similar. These clauses bind unfoldingWord as the customer, not people who later download a CC BY-SA dataset (inferred). Confidence: medium.

### Tagging (Q4)

**F17. Measured: one model tagged the samples correctly, and the cheaper models invented details.**
- Claim: on 6 test images (Ge 22, Le 1, Ps 23, Mk 2 twice, Acts 2), Claude Sonnet 5.5 was accurate on all 6 and named people only where the passage supported it. Claude Haiku 4.5 said men were "lowering a man through a roof" in two Mark 2 frames that show no roof opening, added a knife to the Genesis 22 ram picture that is not drawn, and called the Psalm 23 shepherd "David". Qwen3-VL 235B also called the shepherd "David". GPT-5.4-mini and Qwen copied the prompt's placeholder "v1-v2" as the verse guess while reporting "high" confidence. Part of that is my prompt's fault. Gemini 3.6 Flash was accurate but used about 1,000 reasoning tokens per image and ran out of output room on 2 images.
- Evidence: `research/data/vision_pilot_6img_results.jsonl` and `vision_pilot_tag.py`. I compared each output against the images myself.
- Confidence: medium. Six images is a small sample.

**F18. Measured token use and extrapolated cost.** All prices are OpenRouter list prices on 2026-10-07. Images are 831×610.

| Model | Measured input tokens per image (image + about 300 words of prompt) | Measured output tokens | Measured cost per image | Extrapolated cost for 2,360 pictures |
|---|---|---|---|---|
| Claude Sonnet 5.5 | 1,050 | 718 | $0.0093 | about $22 (about $11 with the batch price) |
| Gemini 3.6 Flash | 1,321 | 1,353 | $0.0061 | about $14, but it needs a larger output limit |
| Claude Haiku 4.5 | 931 | 432 | $0.0031 | about $7 |
| GPT-5.4-mini | 866 | 210 | $0.0016 | about $4 |
| Qwen3-VL 235B | 739 | 330 | $0.0006 | about $1.40 |

The test run cost $0.125 in total. The extrapolation assumes the remaining pictures behave like the six samples. Cost does not decide anything here, because even three passes with the best model stay under $75.

**F19. Theographic adds little that the passage itself does not.** It links 3,067 people, 1,274 places, 450 events and 23 people groups (4,814 entities) to verses. P5's "about 53,000" is the number of links (28,240 people + 7,310 places + 17,570 events), not verses; the Bible has 31,102 verses. For Mark 2:1-12 it lists only God, Jesus Christ and Capernaum: the paralyzed man and his four friends are missing because they are unnamed. For Acts 2:1-13 it lists 12 places that are only mentioned, not drawn. Source: my own count over the Theographic JSON files. Confidence: high.

### Delivery (Q5)

**F20. BT Servant can probably show these images on WhatsApp and web today without code changes, but not on Telegram, Signal or voice.**
- Claim: the worker's system prompt tells Claude to write any tool-returned `.jpg` URL as markdown image syntax. The WhatsApp gateway pulls those URLs out of the reply and sends them as native images, with no caption. Telegram has no photo-sending code and skips non-audio attachments. Signal sends only items in an `attachments` list. Voice mode drops the image rule.
- Evidence (repos cloned today):
  - bt-servant-worker `src/services/claude/system-prompt.ts:155-176` (worker commit 273a5bc); I read it.
  - bt-servant-whatsapp-gateway `src/services/media-extractor.ts:24,38`; I read it.
  - bt-servant-whatsapp-gateway `message-handler.ts:435,466-488`; the agent read these.
  - bt-servant-telegram-gateway `telegram/client.ts` and `response-dispatch.ts:173-175`; the agent read these.
- How to verify: register a test MCP server in a staging org and send one message per channel.
- Confidence: high on the code, medium on the behavior, which nobody has run.

**F21. Credential leak in the Signal gateway (security).**
- Claim: before it sends an attachment, the Signal gateway downloads the URL and sends the engine API key as a Bearer header to whatever host the URL points at. Today the attachments come from the worker. If image attachments ever point at R2, Commons or any other outside host, the key goes to that host.
- Evidence: bt-servant-signal-gateway `src/bt_signal_gateway/media.py`, `download_to_temp`. The line `headers = {"Authorization": f"Bearer {settings.engine_api_key}"}` is applied to every URL (commit b353b75; I read it).
- Confidence: high. This repo is not one of yours, so I filed nothing. It needs to go to the BT Servant team.

**F22. MCP and hosting facts.**
- BT Servant passes only `text` blocks to Claude and caps responses at 1 MB. A base64 image block is either dropped or pasted into the model's context as a JSON string. Source: bt-servant-worker `discovery.ts:283-288` and `services/mcp/types.ts:118`.
- The default transport is a stateless JSON-RPC POST that expects a plain JSON reply. The tool timeout is 30 seconds. The catalog shows Claude only the first sentence of each tool description, cut at 80 characters. Source: `catalog.ts:75-110`.
- Channel limits: WhatsApp images up to 5 MB by link or media ID. Telegram `sendPhoto` up to 5 MB by URL or 10 MB by upload, with a 1,024-character caption. Signal through signal-cli needs a local file. Sources: Meta and Telegram developer docs.
- R2 storage is $0.015 per GB-month with no egress fees, so about 4.4 GB of images costs about $0.07 a month, or nothing within the free tier. Source: developers.cloudflare.com/r2/pricing/. The cost figure is an estimate.
- Commons allows hotlinking but does not recommend it. Bots must send a descriptive User-Agent, which Meta's and Telegram's fetchers will not do for us. Only standard thumbnail widths are served. The pCloud share has no service guarantee, and we do not know who owns the account.

Confidence: high.

### Global use (Q6)

**F23. Passage lookup should work in any language; scene search needs one extra piece (inferred).** The worker does not translate user messages into English. Claude writes the tool arguments itself (bt-servant-worker `services/language/detect.ts` is used for telemetry only). Claude routinely turns "Marcos 2" into a reference, and translation-helps-mcp already accepts localized book names, so passage lookup is language-independent. For scene search, Claude may pass the query in the user's language. A multilingual embedding model on the server (Cloudflare Workers AI `@cf/baai/bge-m3` is listed as multilingual) would match those queries against English tags without translating the tags. This is inference; nobody has tested it.

### Demand (Q7)

**F24. There is indirect evidence of demand and no direct request.**
- bt-servant-worker #166 shows production users already receiving passage images from FIA.
- bt-servant-worker #110 (closed) set up the FIA coach to show resources inline during translation.
- bt-servant-worker #280 (open) is about rendering media inline under WhatsApp's size limit.
- Five independent developers have built Sweet passage indexes (F5).

We found no forum post, issue or request from translators, teachers or OBS teams asking for verse-searchable or scene-searchable Sweet images. Searched: forum.door43.org, unfoldingWord GitHub issues, and general web search. Confidence: medium.

## 3. Decisions

These are my recommendations. D8 and D9 go to you because they involve other teams or legal risk.

- **D1. Use the distinct picture, not the file name, as the record**, and give each record every file name and every passage it serves. This removes 637 duplicates and makes "what illustrates Luke 5:19?" find the picture filed under Mark 2.
- **D2. Harvest references first and use vision second.** Use Commons captions for the Gospels, then bare references from St-Takla once D8 is answered. Check each reference's book and chapter against the file name. The vision model confirms each reference and generates one only for the 77 uncovered pictures and any mismatches. This follows your "just find the data" preference and costs less review time.
- **D3. Use Claude Sonnet 5.5 for tagging**, through OpenRouter at the batch price. It was the only tested model that kept to the rules on naming people (F17), and the whole run costs about $11 to $22.
- **D4. Leave Theographic out of version 1.** The passage text already gives the named people, and Theographic misses unnamed figures, lists places that are not drawn, and has the non-commercial question in its sources (F19, F16).
- **D5. Host copies on Cloudflare R2 behind a custom domain**, in two sizes: the 610px set for chat, and the full-size set for download. It costs about nothing, and unfoldingWord controls the links.
- **D6. Return image URLs in a text block plus structured JSON**, with the credit line in the same text. Do not send base64 by default, because BT Servant drops it and it can break the 1 MB cap.
- **D7. Ship three tools** (section 6) and put the purpose in the first 80 characters of each description.
- **D8 (escalate). Ask before using St-Takla references.** Ask St-Takla, or have unfoldingWord's counsel confirm that reusing bare references is acceptable. Without them, about 70% of the pictures (the non-Gospel ones) need the vision model to propose a reference and a person to check it.
- **D9 (escalate). Build a small standalone server, and offer the dataset to the Aquifer and FIA maintainers.** Scene search and the attribution handling are specific enough to justify one more server, but BT Servant will then have three image sources, and Claude may pick the wrong one. Someone on the BT Servant team should agree to this before it is registered.

## 4. Risks

- **R1. The St-Takla references may not be reusable** (F10). If they are not, the review effort for the non-Gospel pictures goes up a lot.
- **R2. Wrong identities or invented details.** Two of five models named the Psalm 23 shepherd "David", and one drew a roof scene that was not in the picture (F17). Guardrails: give the model the passage first; allow a name only if that person appears in the passage text; otherwise use a generic label; record uncertainty in its own field; have a person review every picture where the vision output disagrees with the harvested reference.
- **R3. Channel gaps.** Telegram and Signal users will see nothing or raw markdown until those gateways change (F20).
- **R4. The Signal key leak** becomes live the moment anyone adds outside image attachments (F21).
- **R5. Attribution can get lost.** WhatsApp images go out with no caption, so the credit depends on Claude keeping it in the reply text.
- **R6. Tool confusion.** BT Servant will have three image servers. The 80-character description cut-off makes clear names important.
- **R7. Source decay.** The pCloud share has an unknown owner, the zip has defects (F12), and the sweetpublishing.com link now goes to a store.
- **R8. Demand is not proven** (F24).
- **R9. Images of Jesus.** Some audiences BT Servant serves may object to pictures of Jesus or of prophets. This needs a policy decision, not a technical fix (inferred; no evidence gathered).

## 5. Open questions for people

- **Q1 (lawyer or unfoldingWord).** May we reuse the bare passage references from St-Takla? Should we ask St-Takla, or FreeBibleimages, whose slide text St-Takla appears to copy?
- **Q2 (lawyer).** Is an AI-written tag set an adaptation of the images? Can it be copyrighted at all? Is CC BY-SA 4.0 the right license for it? Does the TIPNR non-commercial listing matter if we ever use Theographic?
- **Q3 (unfoldingWord).** Which credit line is canonical: the uW page's "Sweet Publishing", the Commons "Distant Shores Media/Sweet Publishing", or the Padgett and Gospel Light line? Where should the link point now that sweetpublishing.com is a store?
- **Q4 (BT Servant team).** Will you accept a new image server (D9)? Who will add Telegram photo sending and Signal image support, and fix the Signal key leak (F21)?
- **Q5 (unfoldingWord).** Is there a policy on sending pictures of Jesus in sensitive contexts (R9)?
- **Q6 (Benjamin).** Who reviews the 50-image pilot? I estimate 1 to 2 hours.
- **Q7 (unfoldingWord).** Who owns the filedn.com (pCloud) account behind the download links?

## 6. Build plan

The first usable version is an open dataset covering every distinct picture with passage references and visible-element tags, and a public MCP server with three tools that BT Servant can call on WhatsApp and web. All effort figures are estimates for agent-assisted work, not measured.

1. **Canonical image set** (half a day). Download the full-size and 610px sets from pCloud. Recover the 25 empty files and Ac_05_17. Group files by hash and give each picture a stable ID. Done when 2,359 or so pictures each list every file name.
2. **Harvest passages** (1 day). Bring in the Commons Gospel captions (the script already exists in scratch). Bring in the St-Takla bare references if Q1 allows. Check each reference's book and chapter against the file name. Add OBS frame links from `obs_to_sweet.csv`. Done when every picture has zero or more references with a source label, and a mismatch list exists.
3. **Pilot of 50 pictures** (1 day, plus 1 to 2 hours of review). Use the schema and rubric below.
4. **Full tagging run** (1 day, about $11 to $22). Run every picture. Queue for human review every picture with a mismatch, an "uncertain" entry, or no harvested reference.
5. **Publish the dataset** (half a day). JSON and CSV on GitHub or Door43 (DCS), with the license and credits from section 3 and Q2/Q3.
6. **Images on R2** (half a day). Use clean keys such as `sweet/<id>-610.jpg` behind a custom domain.
7. **MCP server** (2 days). A Cloudflare Worker using stateless JSON-RPC. Embed scene summaries and tags with bge-m3 when the dataset is built; with only about 2,360 vectors, the Worker can search them directly with no vector database.
8. **BT Servant staging test** (half a day). Register the server in a staging org and send test messages on WhatsApp and web.

**Tag schema** (one record per distinct picture):

```
id, files[] (RG names), image_urls {medium, full}, width, height
passages[]: {ref: "MRK 2:3-4", source: commons|sttakla|vision|manual, confidence}
also_in_obs[]: ["16-12"]
scene_summary: one sentence
people[]: {label: "man lying on a mat", identity: "Jesus" | null, basis: passage|none}
figure_count: integer, or "crowd" above about 20
places[], objects[], actions[]
setting: indoor|outdoor|mixed;  time_of_day: day|night|unclear;  mood: one word, optional
uncertain[]: free text
tagged_by: {model, date, prompt_version};  reviewed_by: person or null
```

**Pilot of 50 pictures:**
- 8 sparse pictures from Leviticus (all 7) and Psalms.
- 8 crowded scenes from Acts.
- 10 Gospel pictures with Commons captions, used as the answer key.
- 8 Old Testament narrative pictures, including the Exodus chapter 00 frames and Deuteronomy.
- 6 duplicate pictures that serve several books.
- 4 from the Epistles and Revelation.
- 4 edge cases: the Job `a1` names, 2Sa_31_03, the misfiled 1 Timothy files, and one recovered empty file.
- 2 at random.

**Pass/fail rubric**, scored per picture by a person:
- The passage reference contains the moment that is drawn.
- No listed object or action is missing from the drawing.
- Every named person appears in the passage and fits the drawing.
- The figure count is within about 20%, or "crowd" is correct.
- The summary is accurate.

The pilot passes if at least 45 of 50 pictures pass, no picture has a wrong identity, the references match at least 95% of the Commons-captioned subset, and the right picture lands in the top 5 for at least 16 of 20 test searches (for example "men lowering a man through a roof", which should find 41_Mk_02_05).

**Tools:**

| Tool | Input | Output |
|---|---|---|
| `fetch_illustrations_for_passage` | `{reference: "MRK 2:1-12", limit?: 5}` | `{reference, illustrations: [{id, url, full_url, passages, scene_summary, attribution, license, license_url}], total}` |
| `search_illustrations` | `{query, book?, limit?: 5}`; the description asks for an English query, but other languages still work through embeddings | same items plus `score` |
| `get_illustration` | `{id}` | the full record, with all tags, file names, OBS frames and source links |

Each response has a short text summary with the URLs and the credit line, then the JSON as text and as `structuredContent`, plus `_meta.downstream_api_calls: 0`. A response stays under about 10 KB.

**Attribution string** for each picture, pending Q3:
`Illustration by Jim Padgett, © Sweet Publishing, from the Read 'n Grow Picture Bible. CC BY-SA 3.0 https://creativecommons.org/licenses/by-sa/3.0/`

**Explicitly out of scope for version 1**, each worth one sentence:
- Telegram, Signal and voice delivery. That is BT Servant gateway work.
- Tags translated into other languages.
- Iconclass codes. Iconclass is an art-classification vocabulary that has codes for Bible scenes.
- FreeBibleimages slide text.
- Theographic.
- Adding Sweet to Aquifer itself.
- Edited or recropped images.
- An OBS-specific tool. OBS links travel as a data field instead.

## 7. Search log

- **MCP registries:**
  - Official registry `/v0/servers?search=` for bible (79 rows, 16 unique servers), scripture, biblical, christian, illustration, "bible art", sermon, church, gospel and jesus. "bible image" timed out.
  - Glama `?query=bible`, Smithery `?q=bible`, PulseMCP `?q=bible`, mcp.so `search?q=bible` and mcpservers.org `search?query=bible`. mcp.so and mcpservers.org were read with curl after WebFetch got a 403.
- **GitHub repo search** (`gh search repos`): "bible mcp", "bible image", "bible illustration", "sweet publishing", "padgett bible", "read n grow", "bible pictures api", "bible images api", "bible art dataset", "scripture mcp", "biblical art", "aquifer mcp", and owner BibleAquifer.
- **GitHub code search** (`gh search code`): `"_RG.jpg"`, `"Bible Illustrations by Sweet Media"`, `"Read'n Grow"`, `"sweet_images"`, `"Jim Padgett"`, `"Sweet Publishing"` with json, csv and tsv extensions, `Mk_02_04_RG`, `Ge_01_01_RG`, `SweetPublishingBibleIllustrations`, and the filedn folder ID. Some code searches hit the API rate limit; the xml, yaml and freebibleimages-json variants were not rerun.
- **unfoldingWord issues** (`gh search issues --owner unfoldingWord`): sweet publishing, padgett, illustration, picture, images, "image search", "obs images". Per-repo searches in translation-helps-mcp, bt-servant-engine, bt-servant-worker and obs-5m-mcp.
- **Repos read** (shallow clones): bt-servant-worker, bt-servant-engine, the WhatsApp, Telegram and Signal gateways, bt-servant-web-client, bt-servant-admin-portal, bt-servant-message-broker, translation-helps-mcp, obs-5m-mcp, fia-mcp (README), klappy/aquifer-mcp, and BibleAquifer UBSImages, FIAImages and BiblicaOpenBibleMaps.
- **Live calls:** aquifer.klappy.dev (health, tools/list, search, browse, get, related); api.aquifer.bible swagger, which we read but did not call because it needs a key.
- **Hugging Face API:** bible, sweet publishing, padgett, bible illustration, bible art, biblical, christian art, religious art, iconclass, ArtDL. **Kaggle API:** "bible images", bible, "religious art", "christian art".
- **Wikimedia Commons API:** categoryinfo and categorymembers for "Media contributed by the Sweet Publishing", "Bible illustrations by Sweet Media" and "Jim Padgett"; CirrusSearch with P180 and P921; `wbgetentities` on sample files; `action=raw` on gallery pages including "Gospel harmony (Sweet Publishing)"; siteinfo rightsinfo.
- **Door43:** `api/v1/repos/search` for image, images, obs-images, sweet and illustration; en_obs LICENSE.md, manifest.yaml, and content files 01, 05, 13 and 22; forum.door43.org `search.json` for images, pictures, illustrations and "sweet publishing".
- **Websites:**
  - unfoldingword.org/sweet-publishing and its book pages.
  - filedn.com folders, LICENSE, and probes for index files.
  - freebibleimages.org search and set pages, story downloads, and /help/reuse/.
  - st-takla.org album and item pages.
  - sweetpublishing.com. distantshores.org redirected or failed.
  - openbiblestories.org/license.
  - archive.org metadata for the printed book. It is loan-only and not usable.
  - techteam25/SPadv (Story Producer).
- **License texts:** CC BY-SA 3.0 and 4.0 legal code, the CC FAQ, CC compatible-licenses, Anthropic Commercial Terms, Gemini API terms, and the OpenAI Services Agreement (Wayback copy; openai.com returned 403).
- **Docs:** MCP specification (latest, tools), Meta WhatsApp image messages and media, the Telegram Bot API, Cloudflare R2 pricing and public buckets, Workers AI bge-m3, the Wikimedia User-Agent and robot policies, and Commons reuse and thumbnail-size pages.
- **Web searches:** Logos media search, Bible image MCP, Visual Commentary on Scripture, Iconclass, ArtDL, YouVersion, Story Producer templates, the book's ISBN, St-Takla terms, translator demand.

Pages that failed:
- dsmedia.org and distantshores.org did not load.
- The freebibleimages /about/terms-of-use/ page returned 404 and their contributor listing is built in JavaScript; we used the data embedded in the page instead.
- openbibleimages.org is a JavaScript app with no readable content.
- Meta's media-object field table did not render, so the HTTPS requirement for WhatsApp links is checked only in BT Servant's code.

## 8. Closing

**What I verified, and how:**
- The fia-mcp media tool, from its README. Aquifer is up (HTTP 200).
- The Signal key header, the worker media rule and the WhatsApp extractor, by reading the code.
- A St-Takla caption and reference, by fetching the page.
- One duplicate pair, in the MD5 list.
- The Commons text license, through the siteinfo API.
- bt-servant-worker issues #110, #166 and #280, with `gh`.
- The Theographic counts, from my own script over its JSON.
- The vision test: six images through five models, with every output compared to the picture by eye.

**What agents verified that I did not re-check:** the full inventory and duplicate counts, OBS matching, Commons mapping, the FreeBibleimages counts, the license page wording, the channel limits and R2 pricing. Each agent reported URLs, commands or file paths, and I spot-checked the items listed above.

**What I did not verify, and why:**
- That a markdown image actually shows on WhatsApp or web. Nothing was deployed.
- How well St-Takla references hold up beyond a 29-item sample.
- The 2014 Commons count.
- The 4 GB zip, which was not downloaded.
- Whether Aquifer's image passage search is broken or was only empty in our test.
- Any legal conclusion.

**Assumptions:**
- The six test images represent the set.
- OpenRouter prices hold.
- Commons gallery captions are accurate. They are community-edited.

**Process note:** I did not file an or-misfire issue for the models that failed the tagging test, because it was a deliberate comparison, not delegated work. Say so if you want them logged.

**Evidence files** (copied from session scratch into `research/data/`, not committed): `manifest.csv`, `sweet_dupgroups.json`, `rg_md5.txt`, `commons_map.csv`, `commons_passage_captions.csv`, `obs_to_sweet.csv`, `fbi_all_sets.csv`, `takla_items.txt`, `rg_uncovered.txt`, `zero_byte.txt`, `vision_pilot_6img_results.jsonl`, `vision_pilot_tag.py`.

**Biggest gap to close next:** the answer to Q1 on St-Takla, because it decides whether about 1,700 pictures need human review of AI-proposed references. The cheapest technical check is the staging test in build step 8, using a single hand-made record. It would show whether the WhatsApp and web path really works before any tagging money is spent.
