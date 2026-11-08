# How it works, and how to see it

Everything below was run on 7 Nov 2026; the output blocks are the real
output, not illustrations. Numbers may move by a second or two between runs, and the timestamps and
`run_at` fields change with the clock.

Two runs sit side by side, and the script in section 10 keeps them apart.

- **IFIC 3074 is the accuracy material.** It is the package the challenge ships, and the numbers in
  sections 2 to 4 (196 notices, the slice, the full-allocation run) come from it. `out/` holds that
  run.
- **IFIC 3075 is the automatic-search demo.** The monitor fetched it on 7 Nov 2026 and the funnel
  ran into `runs/3075/`, which `runs/latest` points at, so the web UI shows that run's card text.
  Section 2b is that run.

## 1. One-time setup

```bash
sudo apt install mdbtools
uv sync
cp <path>/Traficom_SinceAI_Frequencies_of_interest_v05112026.xlsx data/
uv run python scripts/fetch_data.py
```

The last command downloads the IFIC package, the two terrestrial BR IFIC packages and the M4 table,
unpacks the `.mdb` database from each zip, converts the register xlsx to CSV, and prints a SHA256 per
file. The database itself is read at run time by `mdb-export` (`apt install mdbtools` above). The
download needs a network. The deterministic pipeline does not: it opens a connection only in the
optional LLM prose step, and only when `LLM_BASE_URL` is set.

## 2. The accuracy run on IFIC 3074: the 3.47 to 3.78 GHz slice

```bash
uv run python -m app.pipeline --ific data/itu-ific-3074/ific3074.mdb \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json --out out/
```

```
196 notices → G1 41 → G2 21 → G3 20 + 1 cannot decide
exceeds 11, near 5, not_space 4, clear 0, 196 in the queue (1 bands, 4.31 s)
wrote out/cases.json, cases.md, queue.md, queue.json, funnel.json, 3074_results.csv, run.log, letters/
```

The first line is the funnel: 196 notices, 41 overlap a band in the run's scope, 21 of those can be
seen from Finland, 20 get a number and one cannot be decided. The pipeline prints these three gates
as `G1` (band overlap), `G2` (visible from Finland) and `G3` (computed); the page shows the same
three in plain language. The whole run takes a few seconds — most of it the `mdb-export` of the 15
tables — and opens no connection with no LLM configured.

## 2b. The automatic check: what the monitor did on IFIC 3075

Nobody downloads the package by hand. `scripts/monitor.py` asks ITU for the next space BR IFIC and
ingests it when it appears; the "Check now" button in the page runs the same thing.

```bash
uv run python scripts/monitor.py --check   # ask ITU now, ingest a new package
uv run python scripts/monitor.py           # print the last known status
```

The check of 7 Nov 2026 wrote `runs/3075/`:

```
run_at=2026-11-07T09:43:56+02:00
input_sha256=5416d9e8a67fc22fb055cb0b6f457e8bb205df90d3e6e0a0dccd9be0ede02a07
rules_version=1.2.0
ific=3075
source_file=ific3075.mdb
mode=slice
notices=129
freq_rows=50645
register_rows=871
territory_points=552
bands=1
visible=GEO 9 NGSO 0
g1=19 g2=9 g3=7 cannot_decide=2
letters=3
elapsed_s=2.05
```

The current code reports `register_rows=7` for the same slice, because it builds only the stations
on the run's bands; the 09:43 run above predates that change.

`runs/3075/funnel.json` carries the counts as `129 → 19 → 9 → 7 + 2`, with the drops
`no_band_overlap` 110 and `geo_below_horizon` 10, and 129 rows in the queue (9 need attention). The
run wrote seven cards to `cases.json` (3 exceeds, 4 near, no clear), 129 rows to
`3075_results.csv`, three letters to `runs/3075/letters/`, and its own `queue.md`, `queue.json`,
`run.log` and `teams_message.*`. The first queue row is
`125520114`, a near case at a coordination request; the APSTAR card `3075-108501259` is fifth, because
its filing is already in the MIFR and the stage orders first. The two notices the tool refuses to
decide are rows 8 and 9 of `queue.md`: `126590034` and `126590035`, Resolution 49, no PSD, each with
the value it would need (`psd ≥` −22,29 and −24,75 dBW/Hz).

`runs/latest` points at `runs/3075/`, so the web UI shows that run's queue. The monitor does not touch
`out/`: that directory keeps the 3074 outputs. A failed check (a truncated download, a broken zip,
a run that dies) writes `status: error`, exits 1, and leaves `runs/latest` and `out/` as they were.

The top-bar panel reads the last answer from `out/fetch_status.json`:

- `new`: "New IFIC 3075 fetched and processed 7 Nov 2026, 09:43 · 129 notices."
- `no_new`: "No new IFIC has been published yet (latest 3075). Checked <time> · next
  check <time>."
- `error`: "Check failed <time>: <message>."

The cadence is 14 days (`CADENCE` in `scripts/monitor.py`), and `next_check` is written only when a
check finds nothing new.

## 3. What to look at

`out/queue.md` is the decision list, most urgent first:

```
# Queue (19)

Funnel: 196 → 41 → 21 → 20 + 1

| # | case | class | stage | action | deadline | margin dB | reason |
|---|---|---|---|---|---|---|---|
| 1 | 124520183 | exceeds | No. 9.6 | A | - | 3,66 | exceeds |
| 2 | 124520184 | exceeds | No. 9.6 | A | - | 1,74 | exceeds |
| 3 | 124545403 | exceeds | No. 9.1 | M | - | 60,44 | exceeds |
| 4 | 124520214 | near | No. 9.6 | A | - | -0,25 | near |
| 5 | 125500277 | exceeds | No. 11.2 | A | 19.12.2026 | 16,33 | exceeds |
| 6 | 103500417 | exceeds | No. 11.2 | M | - | 3,25 | exceeds |
```

(13 more rows follow; the file lists all 19. The live file carries two more columns, the Finnish
band and the `settles at` value, left out here for width.) The stage comes first, then the class,
then the earliest upcoming Resolution 35 deadline; the margin does not order. The advance publication
and coordination request rows come before the MIFR notifications, so 124545403's +60,44 dB margin is
third and not first, and 125500277 (group due 19.12.2026) moves ahead of a larger margin.

`out/cases.md` holds one card per computed notice. The one from the plan's test vector:

```
- **Satellite:** COMPASS-80E (GSO, CHN), beam CDN
- **Band:** 3 442-3 478 MHz
- **Stage:** No. 11.2 — notification recorded in the MIFR
- **Publication:** notification recorded in the MIFR (BR IFIC Part II-S)
- **Filing action:** modification
- **Point:** 64,3496 N 22,9884 E (territorial sea outer limit), elevation 4,96°
- **PFD:** -184,78 dB(W/m²/Hz) vs limit -188,02 dB(W/m²/Hz) → margin 3,25 dB
- **Limit:** ITU RR 2024 Art. 21 Table 21-4, 3 400-4 200 MHz, FSS (space-to-Earth), GSO, p. 287
- **Limit row:** A -152 dB(W/m²) at 0–5°, K 10 dB, reference bandwidth 4 kHz (p. 287)
- **Criterion:** ITU RR Art. 21 Table 21-4 is the primary PFD limit (Traficom Q2); CEPT/ECC elaborations are not applied in this build.
- **Finland allocation:** MOBILE AND FIXED (no satellite downlink allocation on 3 442-3 478 MHz)
- This filing follows 100543885 (advance publication, No. 9.1)
- **Reference:** station 986805 (MVV), 66,1172 N 28,5729 E, directive, 58 dBi
- **Coverage:** beam name CDN; worst case assumed: peak beam gain toward the Finnish territory
- **Missing:** nothing
- **Threshold:** the station has a directive antenna; the trigger level may be lower if the source is in the main beam direction
- **Question:** Can China confirm the worst-case PFD the COMPASS-80E CDN beam produces on Finnish territory in the 3 442-3 478 MHz range?
```

Four things to point at on that card. The PFD, the limit and the margin come from the calculation
block (max PSD −50,0 dBW/Hz, beam gain 28,5 dBi, distance 41 130 km, free-space loss 163,28 dB).
The limit is a citation, not a constant: `rules/rr21_table21_4.csv` holds the row. The `Coverage`
line is where Traficom's Q3 answer lands: IFIC 3074 does not declare the beam geometry, so the tool
does not try to decide whether the beam reaches Finland. It assumes the worst case, the notice's own
peak gain aimed at the territory edge, and `Missing` is therefore empty: no field is missing for
the computation. `Point` is the border vertex where the level is highest; `Reference` is the
register row on the band, context only. `Finland allocation` is the second screen (Traficom,
7 Nov 2026): 3 442-3 478 MHz is `MOBILE AND FIXED` in Finland, so a downlink there is a finding
whatever the margin. `Question` is the draft the administration would receive, and it asks to
confirm that worst-case PFD. `Stage` names the provision the filing stands under, `Publication`
names the BR IFIC part and session (here Part II-S, a notification), and `Filing action` plus the
`This filing follows` line say what the filing does and what it follows. The web card also lists
the earlier complaints for the same administration or network, with the reply note. `Threshold`
(here the reference station is directive at 58 dBi) restates Traficom's point that a directive
antenna can be protected at a lower level without changing any number.

`out/3074_results.csv` has one row per notice in the input, including the 176 the funnel dropped
(155 at G1, 21 at G2), each with its stage and reason. The same notice as a row:

```
103500417,CHN,COMPASS-80E,G,GSO,,,exceeds,No. 11.2,3442.0,3478.0,986805,64.3496,22.98844,4.96,-184.78,-188.02,3.25,"ITU RR 2024 Art. 21 Table 21-4, 3 400-4 200 MHz, FSS (space-to-Earth), GSO, p. 287",MOBILE AND FIXED,no,s_beam.bore_long;s_beam.bore_lat;s_beam.maj_axis;s_beam.min_axis
```

`out/run.log` is the audit line:

```
run_at=2026-11-07T22:14:44+02:00
input_sha256=a9755213b6cdb7a26a1ca1dcf95ba69a362d3bcc2cb088e91b6b8e01e4790e31
rules_version=1.2.0
ific=3074
source_file=ific3074.mdb
mode=slice
notices=196
freq_rows=95865
register_rows=871
territory_points=552
bands=1
visible=GEO 18 NGSO 3
g1=41 g2=21 g3=20 cannot_decide=1
letters=11
elapsed_s=5.45
```

The hash is the SHA256 of the BR IFIC MDB the run read, and `source_file` names it; a rerun on
another package is visible. `register_rows=7` is the stations the run built for the slice; the
register has 871 in all, and the full allocation scope builds all of them. `territory_points=552`
is the edge it calculated at: the land borders plus the territorial sea outer limit. `bands=1` is the demo slice; the register's 13,1 MHz hole inside it no longer narrows
the screen, because the bands come from the run's scope, not from the register (D17).

`out/funnel.json` carries the same counts as JSON with the drop reasons
(`no_band_overlap` 155, `geo_below_horizon` 19, `ngso_never_visible` 1) for anything that reads
files instead of humans.

## 4. The whole register

```bash
uv run python -m app.pipeline --ific data/itu-ific-3074/ific3074.mdb \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json --out out/ --all
```

```
196 notices → G1 176 → G2 138 → G3 100 + 38 cannot decide
exceeds 55, near 30, not_space 9, clear 6, 196 in the queue (299 bands, 98.49 s)
```

This is the accuracy run: every Finnish allocation, 552 points on the territory edge, and a queue of
196 rows (132 need attention, 6 checked, 58 no effect) that is not capped. The 38 cannot-decide rows
are 22 `no_limit_for_band` (their bands are not in Table 21-4 at all: RNSS 1 164-1 300 MHz, 137 MHz,
400-401 MHz, amateur 435-438 MHz, 1 544 MHz, 2 400-2 425 MHz, 235-400 MHz, 1 427-1 518 MHz), 10
`no_orbit`, 4 `partly_screened` and 2 `no_power`. The register's rows stay on the cards as a
reference; they do not bound the analysis (D17, D18).

## 5. The web UI

```bash
make run          # uv run uvicorn app.main:app --reload
```

Open `http://localhost:8000`. The page has three panels: the funnel with the drop reasons and the
run metadata, the queue as buttons, and the selected card. Clicking a queue row loads the card from
`/api/cases/{case_id}`. The page computes nothing; it renders the files the pipeline wrote.

Show the error path by pointing it at an empty directory, or by running the UI in a clean clone
where the pipeline has not been run yet:

```bash
KAISTA_OUT=/tmp/nothing uv run uvicorn app.main:app
# GET /api/cases -> 503 {"detail": "...run `python -m app.pipeline` first"}
# GET / still returns the page, with the error in the status line
```

The API endpoints for a scripted demo: `/api/funnel`, `/api/cases`, `/api/cases/{case_id}`,
`/api/queue`, `/api/queue/full`, `/health`. `/api/queue` lists computed cards only; `/api/queue/full`
is the page's queue: every notice in the run with its tier, so the one `cannot_decide` notice in
the 3074 slice has a row there (the 3075 run the page shows has two).

## 5b. The complaint register and the statistics

Traficom's specialist asked what has to be answerable five years from now: what was complained about,
whose operation it was, and what was done (`docs/traficom-qa.md` S6). The page's last section is the
answer, and everything in it is folded from `ledger/complaints.jsonl` on read.

```bash
env -u PYTHONPATH -u PYTHONHOME uv run python scripts/seed_history.py --seed 2026
# 206 complaints, 695 events -> ledger/complaints.synthetic.jsonl
```

The command is deterministic: the same seed writes the same file, byte for byte
(`sha256 d1c80655e620668474eabbf59ad75e948e6044cabb2feb138267ac27e1a658b1`). Those rows are demo
history and every one carries `synthetic: true`; the banner above the tables says so, and
`?synthetic=false` hides them.

The register as this tree shows it, measured 7 Nov 2026:

```
224 complaints · 88 still open · median 28 days from letter to reply
206 of them are seeded demo history (2021-2026); the rest come from the pipeline runs
```

The five blocks are the three questions. Who: China 43 complaints and 23 still open, Russia 32, the
United States 32. What: 3 400-4 200 MHz 97 complaints, PFD over the limit 83, near the limit 66, band
without a satellite downlink allocation 33. What was done: a comment sent 191 times, coordination requested
26, BR assistance requested 16, no action decided 21, with the outcomes beside each. Per year: 2021
35, 2022 38, 2023 36, 2024 35, 2025 33, 2026 47.

Three things to do on screen, in this order:

1. **Start at the card, not at the table.** Open `3075-108501259` and read the new line: "In the
   register China: 43 complaints, 23 open." That is the moment the register earns its place; a
   dashboard nobody asked a question of does not.
2. **One band, one answer.** Set the Year selector to 2023 and the banner and the tables follow. Click
   `Download CSV` and say the file is for their own tools, not ours.
3. **Say what it is not.** Seeded history is labelled; the real rows are the pipeline runs; the log is
   a file, and a production deployment moves the same event model to a database with a retention
   period (`docs/decisions.md` R1). The specialist who hears the limit from us does not have to find
   it.

If the recording is short on time, drop step 2: steps 1 and 3 carry the point alone.

## 6. The terrestrial side feature

The side feature runs in the same command as the space funnel, one MDB per number:

```bash
uv run python -m app.pipeline --ific data/itu-ific-3074/ific3074.mdb \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json \
  --terrestrial data/itu-terr-ific/brific3076.mdb \
  --terrestrial-prev data/itu-terr-ific/brific3075.mdb --out out/
```

```
terrestrial 3075→3076: 2905 new, 163 modified, 413 withdrawn, 32 notices in reach
```

`out/TERRESTRIAL.md` is the readable report: the intent table, the field strength at the border
samples, the trends and the anomalies.

```
| terrakey | adm | class | intent | band | TX lat, lon | distance to border km | max at border | section | distance to maximum km | bw kHz (source) | threshold | margin | coordination | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 92817506 | POL | FB | ADD | 801-806 MHz | 53.8644, 20.9550 | 626 | -38.1 | TS | 625 | 5000 (fxm_terra.bdwdth) | 43.0 | -81.1 | no | - |
| 93005609 | RUS | FB | ADD | 791.14-798.34 MHz | 54.4511, 22.5817 | 563 | -66.0 | TS | 562 | 7200 (fxm_terra.bdwdth) | 44.6 | -110.6 | no | - |
| 93075637 | RUS | FB | ADD | 152.892-152.908 MHz | 61.7606, 30.9894 | 42 | 20.9 | RU | 42 | 16.8 (fxm_terra.bdwdth) | 12.0 | +8.9 | yes | - |
| 93075638 | RUS | ML | ADD | 152.892-152.908 MHz | 61.7606, 30.9894 | 42 | 5.9 | RU | 42 | 16.8 (fxm_terra.bdwdth) | 12.0 | -6.1 | no | fxm_ant.hgt_agl missing: h1 assumed 10 m (lowest P.1546 table height, above a vehicle antenna, so the field strength is overestimated) |

## Anomalies

- RUS FB 791-796 MHz (5 MHz): no notices in this group in the previous issue, 9 new now
- RUS FB 791.14-798.34 MHz (7.2 MHz): no notices in this group in the previous issue, 10 new now
```

(Four of the 32 rows are shown; the same table covers all of them. A mobile station carries no
antenna height, so its row uses the stated 10 m assumption.)

The header of the same file states the source and the criterion: both MDB file names with their
SHA256, model `P.1546-6 land, 10 % time, 50 % locations, no terrain`, and the three-tier framework
(ITU RR Article 11 terrestrial notification and the notice's own coordination provision → ECC T/R
25-08 A1.2.3 → national M4). The ECC values are confirmed and applied per notice; the national value
is not confirmed. The tool reports the margin against the ECC threshold and claims no exceedance
against the national one.

## 7. Proving the deterministic path

```bash
# no LLM configured: every card gets the template and says so
uv run python -c "import json;print({c['prose']['source'] for c in json.load(open('out/cases.json'))})"
# {'template'}

# the guard rejects an invented number (no endpoint needed)
uv run pytest -q tests/test_guard.py tests/test_prose.py
```

The prose block in `cases.json` carries `source` and the text. With an endpoint configured
(`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`), the source becomes `llm` when the guard accepts the
text and `template_guard` when it does not. The pipeline run itself produced `template` for all 18
cards, because no endpoint was set.

## 8. The full test suite

```bash
make check        # ruff check, ruff format --check, pytest: 196 passed with data/
```

In a clean clone without `data/`, the data tests skip themselves: 152 passed, 56 skipped. The number
to quote for "does it work on my machine" is that one, since it needs no challenge data.

## 9. The optional Teams digest (15 seconds)

A side wish, not part of the product, and it needs no Teams account to show. `scripts/notify.py`
turns the files of the run into one message per IFIC:

```bash
uv run python scripts/notify.py --dry-run --html
# reads runs/latest (the run the page shows); writes teams_message.{md,json,html} into that run
```

The message of the auto-fetch run in section 2b:

```
# BR IFIC 3075 — 9 cases to note

Funnel: 129 → 19 → 9 → 7 + 2
Classes: 3 exceeds · 4 near

## Most urgent
1. 125520114 — near, No. 9.6, -0,26 dB
2. 125520132 — near, No. 9.6, -0,25 dB
3. 125520135 — near, No. 9.6, -0,86 dB

Kaista: http://localhost:8000
```

Open `runs/3075/teams_message.html` for the same text as a channel card. The script follows
`runs/latest`, so it builds the digest of the run the page shows; pointed at `out/` with `KAISTA_OUT`
it builds the 3074 accuracy slice instead. The three lines are `queue.md` rows 1 to 3 and the counts
are the ones in `funnel.json`: the script reads those two files and computes nothing. One message per
run, no bot, no chat, no schedule.

`--send` POSTs the same card to `TEAMS_WEBHOOK_URL`. That path has never run against a real Teams
channel, because there was no test channel, so show the dry-run output and say so. The link in the
card is `KAISTA_URL` (`http://localhost:8000` by default), so it opens only for someone already
running the UI; a link a real channel could use needs the app on a hosted URL.

## 10. Three-minute demo script

Two data sets on the screen: IFIC 3074 is the accuracy material, IFIC 3075 is what the automatic
search fetched. The first 30 seconds are the automatic check; the rest is one card of the run it
produced. The two-minute video version, with narration and captions, is `docs/demo-video.md`.
Traficom confirmed on 7 Nov 2026 (Q6) that the video may show the delivered table's rows and the
unfinished prototype.

| Time | On screen | What to say |
|---|---|---|
| 0:00 | browser, the top-bar panel and "Check now" | the panel shows the last check: the newest package and when it was checked. On this tree it reads "New IFIC 3075 fetched and processed 7 Nov 2026, 09:43 · 129 notices."; when a check finds nothing new it reads "No new IFIC has been published yet (latest 3075). Checked <time> · next check <time>." Nobody downloads anything; the tool asks ITU itself, every two weeks. |
| 0:10 | the top-bar status line with its funnel count, and the "Check now" button; do not click | the status line reads the last check, that of 7 Nov 2026: "New IFIC 3075 fetched and processed 7 Nov 2026, 09:43 · 129 notices." The button would ask ITU right away and, on this tree, fetch 3076, so the demo does not click it; see "Why not to click". |
| 0:25 | the funnel panel | 129 notices: 110 with no band overlap and 10 below the horizon dropped, 19 overlap a band in the scope, 9 of those can be seen from Finland, 7 get a number and 2 cannot be decided. |
| 0:35 | the queue, rows 1 and 5 | the stage orders first, not the margin. Row 1 is `125520114`, a near case at a coordination request Finland can still influence; the APSTAR exceedance `3075-108501259` is row 5, because its filing is already in the MIFR. |
| 0:50 | open card `3075-108501259` (row 5) and its `Coverage` and `Missing` lines | APSTAR-92E, 3 440-3 480 MHz, No. 11.2: PFD −187,59 against the −188,02 dB(W/m²/Hz) limit, margin +0,43 dB. The beam geometry is empty in IFIC 3075, so the worst case is assumed: peak beam gain aimed at the territory edge. `Missing` says nothing, because nothing blocks the case, and the question asks China to confirm that worst-case PFD. |
| 1:05 | `runs/3075/letters/3075-108501259.md` | the draft letter: the number, the worst-case assumption, the question. The tool drafts; a human sends it from their own mailbox. |
| 1:20 | "Show calculation" on the card | the calculation behind the number: max PSD −50,3 dBW/Hz, beam gain 26,0 dBi, slant range 41 222 km, free-space loss 163,29 dB, and the limit with its Article 21 Table 21-4 row. |
| 1:35 | `out/TERRESTRIAL.md` | the same style for terrestrial notices: 2 905 new, 163 modified, 413 withdrawn and 32 notices in reach against BR IFIC 3076, six above the ECC T/R 25-08 trigger. That file comes from the offline run into `out/`; the monitor run is space-only. |
| 1:50 | `runs/3075/queue.md`, rows 8 and 9 (`126590034`, `126590035`) | "Needs attention": the two notices the tool refuses to decide, with the level each would need (psd ≥ −22,29 and −24,75 dBW/Hz). Listing them instead of guessing is the point; the decision is left to a human. |

**Why not to click.** The check fetches the number after `runs/latest`. On 7 Nov 2026 that was 3075
and ITU had already published 3076; `https://www.itu.int/sns/ific10/ific3076.zip` answers 200 with
22 079 898 bytes. A live click on this tree would fetch 3076 and move the page on to it, so the demo
reads the status line the 3075 run left and leaves the button alone. Do not run the check on the
tree you are about to submit.

If the UI is not running, the demo works from `cases.md` and `queue.md` alone; the run the page shows is
in `runs/3075/`. Everything except the "Check now" click is offline, and nothing breaks when
the language model is absent: every card of the 3075 run carries the deterministic template.
