# STATE: Read 'n Grow illustrations

## What this project is

An open dataset (Phase 1) of one record per distinct Sweet Publishing / Jim Padgett
Read 'n Grow picture (about 2,360), saying which Bible passages each picture
illustrates and what is visibly drawn. A standalone MCP server that serves the
dataset is Phase 2 and is planned separately. Research record:
`research/2026-10-07-go-no-go-report.md`; evidence files in `research/data/`.

## Gotchas

- The last number in an RG file name (`41_Mk_02_05_RG.jpg`) is a frame, not a
  verse. The chapter is where a story segment starts, so `41_Mk_02_23` shows Mark 3:1.
- 25 files in the 610px zip are empty (0 bytes). The pCloud host
  (`filedn.com/lD0GfuMvTstXgqaJfpLL87S/sweet_images/`) has good copies, and also
  has `44_Ac_05_17_RG`, which the zip lacks.
- Commons numbers Exodus and Deuteronomy differently from RG, so match Commons
  files to RG files by hash, never by name.
- About a fifth of the files are byte-for-byte duplicates of another file
  (parallel Gospel accounts, Kings/Chronicles). The record is the distinct picture.
- Odd file names: `EX` and `LK` in capitals, `Jb_02_04a1`, `19_Ps_119_01`
  (three-digit chapter), `10_2Sa_31_03` (probably 1 Samuel 31), and two `54_1Ti`
  files in the Romans folder.
- St-Takla.org: we take its verse references only (versification is a fact).
  Never store or republish its caption text, which quotes copyrighted Bible
  translations and FreeBibleimages text.
- A picture may name a person only if that name appears in the verse text of one
  of its passages. Otherwise use a generic label such as "man on a mat".

## Licenses

- Images: CC BY-SA 3.0 (Sweet Publishing). Not redistributed in this repo.
- Tags and references we generate: CC BY-SA 4.0.
- Credit line (default until unfoldingWord answers report Q3): `Illustration by
  Jim Padgett, © Sweet Publishing, from the Read 'n Grow Picture Bible. CC BY-SA
  3.0 https://creativecommons.org/licenses/by-sa/3.0/`

## Open blockers (people, not code)

- Report Q1/Q2: lawyer review of St-Takla references and of the license on AI tags.
- Report Q3: canonical credit line. Q7: who owns the filedn.com account.
- Signal gateway sends the engine API key to any attachment host (report F21);
  belongs to the BT Servant team.
