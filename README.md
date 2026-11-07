# Kaista

Seulontatyökalu ITU:n BR IFIC -ilmoituksille: mikä 196 ilmoituksesta voi osua Suomen taajuuksiin.

Kaista hakee uuden BR IFIC -paketin itse ITU:lta kahden viikon välein (`scripts/monitor.py`),
johtaa suojellut kaistat Traficomin taajuusrekisteristä ja laskee jokaiselle osumalle PFD:n ylärajan
ITU RR Art. 21 Table 21-4 -rajaa vasten. Jokainen luku tulee koodista. Kielimalli kirjoittaa
selosteen ja kirjeluonnoksen, ja numerovartija hylkää lauseen, jossa on luku jota kortilla ei ole.
Ihminen päättää.

**Et ole kehittäjä?** [docs/kaytto.md](docs/kaytto.md): viisi askelta, ei komentoriviä.
**Olet kehittäjä?** Asennus ja ajo: [Run it](#run-it). Sanasto: [docs/sanasto.md](docs/sanasto.md).

Since AI Hackathon 2026 · Challenge: Traficom, "Saving Earth from Space Interferers Using Radio
Frequencies" · Team: Greedy Decoding (Janne Rosama, solo)

## The problem

Every two weeks the ITU publishes a BR IFIC with hundreds of new satellite filings. A Traficom
specialist has to find the ones that can touch Finnish radio use, check them against the Finnish
frequency register, and write to the administration behind them. Space IFIC 3074 alone holds 196
notices and 95 865 frequency rows, and the check is done by hand.

## What this does

A deterministic triage pipeline that shows its work. `scripts/monitor.py` fetches the IFIC package
from ITU on the two-week cadence; the run derives the protected bands from Traficom's table of
frequencies of interest, keeps the space-to-Earth notices
that overlap those bands and can be seen from Finland, and computes an upper-bound power flux
density (PFD) against the ITU Radio Regulations Article 21, Table 21-4 limit.

Every notice that survives the gates and gets a number becomes a case card with the source rows,
the calculation, the Finnish allocation from Regulation M4, the regulatory stage of the filing, the
missing data, and one question for the other administration. A notice that passes G1 and G2 but
cannot be computed is not a card: it keeps its row in `queue.md` and `3074_results.csv` under class
`cannot_decide`, and its count is in `funnel.json`. The accuracy slice (IFIC 3074) therefore has 18
cards and one notice without (limitation 15); the auto-fetch demo (IFIC 3075) has 7 cards and two
undecidables. The queue lists every case a human should look at: exceedances
first, then the near-limit cases, then the ones that cannot be decided, and inside a class the
stage another administration can still influence (advance publication, coordination request) comes
before a filing already recorded in the MIFR. It is not capped. A separate accuracy file covers all
196 notices, the dropped ones included. A human decides.

The language model writes the card summary and, for each case above the limit, the correspondence
letter. Every number comes from code, and a numeric guard rejects a sentence that carries a number
the card does not have. Letters land in `out/letters/<case_id>.md`, one per `exceeds` case; the
deterministic template is the floor when no model answers.

A side feature applies the same style to terrestrial land-mobile notices under the same command: it
runs in the same `app.pipeline` pass (`--terrestrial`), writes into the same `out/`, and carries the
same `source` / `audit` / `missing` fields. It reads two real BR IFIC terrestrial databases (3075 and
3076), takes the change from each notice's `intent` field, filters what is within 1 000 km of Finland
and overlaps the register, and computes ITU-R P.1546-6 field strength at points along the Finnish border
(the land borders with Sweden, Norway and Russia plus the outer limit of the territorial sea).

![Kaista UI: funnel, queue and a selected case card](docs/screenshot.png)

The screenshot above is the auto-fetch run: the funnel and the status line for IFIC 3075, the queue
of the seven cards it computed, and a selected case card.

## Verified numbers

Two runs are on record and their numbers are not interchangeable. The auto-fetch demo is IFIC 3075,
the run the page shows (`runs/3075/`): `129 → 19 → 9 → 7 + 2`, 3 exceeds, 4 near, 2 `cannot_decide`,
9 queue rows and the first card `3075-108501259`. The accuracy dataset is the challenge's IFIC 3074
(`out/`): 196 notices, one row per notice in `3074_results.csv`. Measured 7 Nov 2026: `make check`
165 tests (121 passed, 44 skipped without `data/`). The deterministic pipeline is offline; the
optional LLM prose step is the only part of the run that opens a connection, and only when
`LLM_BASE_URL` is set. `scripts/monitor.py` is the one part that reaches the network on its own: it
checks ITU's URL for the next BR IFIC on the two-week cadence and runs it into `runs/<ific>/`.

| | Accuracy slice 3 470–3 780 MHz (IFIC 3074) | All seven space bands (`--all`) |
|---|---|---|
| Notices in | 196 | 196 |
| Register stations on the bands | 7 | 84 |
| Protected bands | 2 (1 group) | 26 (7 groups) |
| G1 band overlap | 41 | 101 |
| G2 visible from Finland | 19 (16 GEO, 3 non-GSO) | 75 |
| G3 computed | 18 | 64 |
| cannot_decide | 1 (`no_power`) | 11 |
| exceeds / near / clear | 9 / 5 / 4 | 26 / 15 / 23 |
| Queue | 15 (9 exceeds, 5 near, 1 cannot decide) | 52 (26 exceeds, 15 near, 11 cannot decide) |

Two test vectors reproduce to the digit:

| Notice | PFD | Table 21-4 limit | Margin | Elevation | Slant range |
|---|---|---|---|---|---|
| 103500417 | −184,78 dB(W/m²/Hz) | −188,02 | +3,24 dB | 4,85° | 41 143 km |
| 124545403 | −137,56 dB(W/m²/Hz) | −198,00 | +60,44 dB | 5,0° | 2 310 km |

The seven-band funnel sits one notice above the plan (101 / 75 / 11 against 100 / 74 / 10). The
reference tool behind the plan read the register cell `0,1G` as 0.1 MHz; this code reads the
`Channel bandwidth` column as 0.1 GHz = 100 MHz. The demo slice is identical in both. The reason
is written up in `docs/decisions.md`, and `tests/test_gates.py::test_all_bands_funnel` locks the
numbers in this repository.

The terrestrial side feature on the real BR IFIC 3076 against 3075 reports 2 905 new, 163 modified,
413 withdrawn and 576 recorded notices, and 28 notices in reach (land mobile, within 1 000 km,
overlapping the register).

## Run it

Prerequisites: [uv](https://docs.astral.sh/uv/), `make`, and `mdbtools` for `mdb-export`.

```bash
sudo apt install mdbtools                 # mdb-export reads the IFIC Access database
uv sync                                   # creates .venv from uv.lock
cp <path>/Traficom_SinceAI_Frequencies_of_interest_v05112026.xlsx data/   # from the Since AI platform
uv run python scripts/fetch_data.py       # downloads the BR IFIC zips and M4; unpacks the .mdb files
```

`fetch_data.py` prints a SHA256 for every file it writes. The source URLs answered on 6 Nov 2026
with the browser-style user agent the script sends; if ITU serves its challenge page instead of the
zip, the script stops with a clear error instead of writing a broken file. The same `PK` check
guards the two terrestrial zips.

```bash
# one command: the 3.47-3.78 GHz space slice and the terrestrial side feature,
# both into the same out/. Drop the two --terrestrial flags for the space run alone.
uv run python -m app.pipeline --ific data/itu-ific-3074/ific3074.mdb \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json \
  --terrestrial data/itu-terr-ific/brific3076.mdb \
  --terrestrial-prev data/itu-terr-ific/brific3075.mdb \
  --out out/

# the whole register: all seven space bands (add the same --terrestrial flags if wanted)
uv run python -m app.pipeline --ific data/itu-ific-3074/ific3074.mdb \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json --out out/ --all

# the web UI over whatever the last run wrote
uv run uvicorn app.main:app --reload      # http://localhost:8000
```

`sh scripts/demo.sh` is that one command. `docs/demo.md` has the three-minute script.

The deterministic pipeline is offline. The LLM is an optional extra step: without `LLM_BASE_URL`
every card falls back to the deterministic template in `templates/`, and the run opens no
connection at all. With `LLM_BASE_URL` set, `app/prose.py` makes one request per card to that
endpoint through `app/llm.py`. Two scripts reach the network: `scripts/monitor.py`, which checks
ITU for the next BR IFIC and runs it into `runs/<ific>/`, and `scripts/fetch_data.py`, the one-time
preparation that downloads the fixed packages by hand.

### Output files

| File | Contents |
|---|---|
| `cases.json` | One card per computed case, full schema, plus the prose block |
| `cases.md` | The same cards as Markdown |
| `queue.md` | The queue in decision order: class first, then stage, then margin |
| `funnel.json` | Counts per gate, drop reasons, queue state, input hash, rules version, mode |
| `3074_results.csv` | Named after the IFIC number. One row per notice in the input, 19 columns, dropped notices with stage and reason, plus the regulatory stage of every notice |
| `run.log` | Timestamp, input SHA256, rules version, the `ific=` id of the package, mode, counts, GEO and non-GSO visibility, the letter count, elapsed time |
| `letters/<case_id>.md` | One correspondence letter per `exceeds` case, drafted by the model or the template |

## Tests

```bash
make install      # uv sync --locked
make check        # lint + tests, exactly what CI runs (.github/workflows/ci.yml)
make lint         # ruff check + ruff format --check
make fmt          # fix lint and formatting
make test         # pytest -q; tests marked @pytest.mark.data skip when data/ is missing
make test-data    # only the tests that need the real challenge data
make run          # uvicorn on http://localhost:8000
make submission-zip   # tracked files at HEAD into dist/kaista-submission.zip
```

`make submission-zip` builds the source archive for the submission form from the files tracked at
HEAD, under a `kaista/` prefix. `data/`, `out/`, `.venv/` and `dist/` never enter it.

| Environment | Result (7 Nov 2026) |
|---|---|
| With `data/` | 165 passed |
| Clean clone, no `data/` | 121 passed, 44 skipped |

There are no committed data fixtures. Every test that needs a real input is marked `data` and reads
the 274 MB BR IFIC MDB, the Traficom register and the M4 table (and the two terrestrial BR IFIC MDBs
for the side feature); `tests/conftest.py` skips all of them when `data/itu-ific-3074/ific3074.mdb`
is missing, so a clean clone and CI run green without the data. To run them locally, fill `data/`
with `scripts/fetch_data.py` (see Run it) and run `make test-data`, or the full `make check`.

## The web UI

`app/main.py` serves one page (`app/static/index.html`) with three panels: the funnel, the queue
and the selected card. It reads the files the pipeline wrote and does no analysis of its own: no LLM
call, no network, no calculation. `KAISTA_OUT` points it at another output directory. Without
`out/`, the page still loads and the API answers 503 with the command to run.

The queue endpoint builds its list from `cases.json`, so notices that could not be computed have no
row; the funnel endpoint carries their count.

## Teams notification (optional)

A wish, not a requirement. `scripts/notify.py` reads `funnel.json` and `cases.json` from the run the
page shows (`runs/latest`, else `out/`) and builds one message per IFIC: the funnel numbers, the three most urgent cases in queue
order, and the link to the UI. One message per run. No bot, no chat, no Graph, no cron, no LLM, and
standard library only: it computes nothing the files do not already carry.

```bash
uv run python scripts/notify.py --dry-run --html   # print, and write out/teams_message.{md,json,html}
TEAMS_WEBHOOK_URL=<url> uv run python scripts/notify.py --send
```

`--dry-run` writes `out/teams_message.md` (the text a human reads in the channel) and
`out/teams_message.json` (the Adaptive Card envelope an incoming webhook accepts); `--html` adds
`out/teams_message.html`, a standalone preview of the same message as a channel card. `--send` POSTs
the card to `TEAMS_WEBHOOK_URL`; when the variable is unset it prints one line on stderr and exits 1.
`KAISTA_OUT` and `KAISTA_URL` (or `--out` and `--url`) point at another output directory and UI
address.

Three limits, stated plainly. No live send has been made: there was no Teams test channel, so the
POST body is covered by a stub in
`tests/test_notify.py::test_send_posts_the_card_to_the_webhook` and the real delivery is untested.
The card's link is `KAISTA_URL`, `http://localhost:8000` by default, so it opens only for someone
already running the UI; a link a real channel could use needs the app on a hosted URL. And there is
no bot and no chat surface, only the one message per run. `--dry-run --html` needs no Teams account
at all: open `out/teams_message.html`.

## Known limitations

1. The PFD is a screening upper bound, not a claim of interference: max PSD plus max beam gain
   minus free-space loss, against Table 21-4. There is no I/N calculation, no receiver noise
   figure and no bandwidth term. `exceeds` means the upper bound is over the limit at some
   elevation angle.
2. Beam geometry is empty in IFIC 3074 (`s_beam.bore_long`, `bore_lat`, `maj_axis`, `min_axis`).
   Following Traficom's Q3 answer the tool does not try to decide coverage from the beam: the worst
   case is always assumed, with the notice's own peak gain aimed at the Finnish station. A card
   states that on a `Coverage` line and asks the administration to confirm the worst-case PFD, so
   the `s_beam` fields no longer appear under `missing` (Q3 in `docs/traficom-qa.md`).
3. Non-GSO geometry is a sweep, not an orbit propagation: the worst case samples a pass from
   perigee in 0.1° steps up to 90° (`app/gates.py`, marked `shortcut`). Station position does not
   change the result for a non-GSO notice, and there is no ephemeris.
4. A Table 21-4 row must contain the whole notified band. A band that straddles two rows, or sits
   outside the tabulated range, becomes `cannot_decide` with reason `no_limit_for_band` rather than
   borrowing a neighbour's limit.
5. Reason codes for one notice can hide each other: inside the per-notice loop the reason is
   overwritten in the order `no_limit_for_band`, `no_power`, `no_gain`, so a notice missing two
   things reports one of them.
6. In `3074_results.csv` the `class` column is empty for every notice dropped at G1 or G2 and reads
   `cannot_decide` only for a notice that reached G3 and could not be computed. `dropped_at` holds
   the gate and `reason` the cause (`app/cards.py`, `results_rows`).
7. The LLM path has been run against one real endpoint (the served Granite, see
   `deploy/openshift/README.md`). The tests cover the template, the exception fallback, the
   blank-answer fallback and the numeric guard with a stubbed chat call. A
   blank or whitespace answer falls back to the template, but a refusal or an answer in the wrong
   language is not detected: the guard checks numbers, not intent. The run behind the numbers above
   had no `LLM_BASE_URL`, so every card carries `prose.source = template`.
8. The terrestrial path runs in the same command as the space funnel (`--terrestrial` on
   `app.pipeline`), writes into the same `out/`, and carries the same `source` / `audit` / `missing`
   fields. It reads the real BR IFIC MDBs (3075 and 3076) with `mdb-export`. The IFIC is
   not a cumulative database, so `new`/`modified`/`withdrawn` come from the `intent` field
   (ADD / MODIFY / SUPPRESS) and 3075 is only the trend baseline. A row without power or location
   (40 of the 4 057 `fxm_terra` rows in 3076: 31 without `pwr_dbw`, 9 whose `geo_type` is `ZONE`)
   is counted under `missing` with its reason and not computed. Mobile stations (`ML`) carry no
   antenna height, so their field strength stays empty rather than guessed.
9. The P.1546 table in `rules/p1546_land.csv` is coarse: three frequencies (100, 600, 2000 MHz),
   eight antenna heights, 70 distances from 1 to 1 000 km, rounded to 0.01 dB. A query outside any
   of those three ranges clamps to the nearest node; the notice is then flagged `extrapolated: true`
   if any border point is outside the table. The model is land path, 50 % of time, 50 %
   of locations, no terrain, 10 m receiving antenna, 1 kW ERP basis.
10. The ECC T/R 25-08 A1.2.3 trigger values are confirmed (0/6/12/18/20 dBµV/m by band on a
    25 kHz reference, and the same 20 dBµV/m above 470 MHz per Traficom 7.11.2026); the national M4
    value is not confirmed. The report names the three tiers in its criterion line (ITU RR Art. 21
    Table 21-4 PFD → ECC T/R 25-08 trigger field strength → national M4) and applies the ECC
    threshold per notice.
11. Not implemented: the labelled evaluation set (plan R16) and the LUMI run (R20). The OpenShift AI
    part (R19) was built and used: Granite 3.3 2B Instruct served by KServe and the vLLM CPU runtime
    in the sandbox, called by the prose step. See `deploy/openshift/README.md`. The demo video, the
    push and the rest of the submission form are the owner's steps; `SUBMISSION.md` lists them under
    the final check.
12. The queue has no cap. The written challenge brief names no target number, and the job is to
    find the problems and report them, not to shorten the list. Everything stays in the files; the
    clear cases keep their row in `cases.json` and `3074_results.csv` and are left out of the queue.
13. The 26 protected bands are an artefact of the register, not a simplification: the demo slice
    has two bands separated by a 13.1 MHz hole, and the hole is shown rather than covered.
14. `main` is pushed: `origin/main` sits at the same commit. Any later commit needs its own push,
    which is Janne's call.
15. A notice that survives G1 and G2 but cannot be computed gets no case card. In the demo slice
    126590032 passes both gates and carries no emission power, so it lands in `queue.md` and
    `3074_results.csv` under class `cannot_decide`, while `cases.json` holds 18 cards, not the 19
    the plan's F7/F10 expects. The row, the reason and the count stay in the files, so nothing drops
    out of the audit trail, but the notice has no card in the web UI. Recorded as I15 in
    `docs/decisions.md`.
16. The adjacent-channel guard is off by default (`GUARD_MHZ = 0.0` in `app/config.py`), so G1 still
    needs a real band overlap and every number above stays comparable with the plan. Raise that one
    constant when Traficom confirms a channel-spacing threshold: a notice that then enters only
    through the guard is marked `adjacent: true` on its card and is capped at class `near`, because
    the Table 21-4 limit is a property of the notified band and does not apply outside it.
17. A card's `threshold_note` (a directive station with gain at or above 20 dBi, `victim.directivity`
    not `ND`) names a lower possible trigger level and changes no number and no class. It does not
    compare the station's azimuth with the direction of the satellite: the register carries an
    azimuth but no beam width, so a direction-to-source claim would be a guess (I18 in
    `docs/decisions.md`).
18. The ingest reads 15 IFIC tables and ten of them reach no gate on IFIC 3074 (`c_pfd`, the
    `s_beam.pwr_max_4k` / `pwr_avg_4k` power columns, `coord_agree_ntw`, `res49_sel`, `hist_notice`,
    `e_stn`, `grp_res35`, `epfd_param`, `ntc_lnk`, `notice.act_code`). Each is a measured negative
    result, written up table by table in `docs/features.md` under "Data we read and did not use".
    `s_beam.gain` is the one column that is used: it gives every PFD the notice's own peak gain
    rather than a worst-case guess.
19. The register has 874 rows (871 stations load; three rows carry no frequency) and only 84 of
    them sit on the seven space bands, so the result does not depend on the full register. The
    sample's own cover note says a real dataset would be "tens of millions of rows", and the code
    reads the whole file into memory,
    so that size needs a band filter before the load; the tool does not claim to handle it as it
    stands (see "Next steps" in `docs/features.md`).
20. What is not built, and what each piece would take, is listed in `docs/features.md` under "Next
    steps": the filings chain (`ntc_lnk`), the filing action (`notice.act_code`), the AP30 plan path,
    RR Art. 22 / EPFD, space-side trends, Resolution 35 deadline ordering, the M15 cross-check
    and the CEPT/ECC DocDB tier.

## Layout

```
app/            one module per feature, each with tests/test_<feature>.py
  config.py     space bands, demo slice, rules version, adjacent guard, stages, formatting
  ingest.py     IFIC tables read from the BR IFIC MDB (mdb-export), register, M4, unit parsing
  bands.py      protected bands derived from the register
  pfd.py        geometry, free-space loss, Table 21-4 limits
  gates.py      G1 to G4, reason codes, classes, queue
  cards.py      card schema, M4 lookup, Markdown, CSV, run log
  pipeline.py   the CLI
  prose.py      prose from the LLM, template as the floor
  guard.py      every number in the prose must exist in the card
  terrestrial.py  BR IFIC 3075/3076 intent diff, filter, P.1546 field strength, trends
  main.py       read-only API and the page
rules/          rr21_table21_4.csv, p1546_land.csv
templates/      the two Finnish templates (card summary, correspondence)
scripts/        fetch_data.py, monitor.py, demo.sh, notify.py
docs/           features.md, architecture.md, decisions.md, demo.md, demo-video.md
tests/          unit, component and data tests; the data tests read data/ and skip when it is missing
data/  out/     local only, ignored by git
```

Configuration lives in `pyproject.toml` (dependencies, ruff, pytest) and `.env` (copy
`.env.example`; never committed). The challenge data is not in the repository: `fetch_data.py`
downloads the public ITU files (space IFIC 3074, terrestrial BR IFIC 3075 and 3076) and Traficom's
table of frequency allocations and prints their hashes, while the frequencies-of-interest table is
Traficom's synthetic dataset from the Since AI platform and has to be copied in by hand.

## Data, privacy and security

- Inputs: ITU Space BR IFIC 3074 (public), ITU terrestrial BR IFIC 3075 and 3076 (public), Traficom
  open data table of frequency allocations (public), the Traficom frequencies-of-interest table
  (synthetic, handed out for the challenge), and ITU Radio Regulations 2024 for the limits.
- No personal data goes through the pipeline.
- No secrets in the repository: configuration comes from `.env` (see `.env.example`), and the only
  credential any code reads is `LLM_API_KEY`, sent to the endpoint the user configured.
- The deterministic run is offline. `scripts/monitor.py` is the only code that downloads on its own:
  it checks ITU for the next BR IFIC and runs it. `scripts/fetch_data.py` downloads the fixed packages
  when called by hand. The optional LLM prose step (`LLM_BASE_URL`) makes one request per card to the
  endpoint the user configured.
- `data/` and `out/` are gitignored. The register and the IFIC package are not redistributed.

## Technology inventory

| Item | Use | Licence |
|---|---|---|
| Python 3.11 or newer | everything | PSF |
| FastAPI and uvicorn | web API and the page | MIT |
| openpyxl | register xlsx to CSV | MIT |
| pytest, ruff | tests, lint, format | MIT |
| mdbtools | `mdb-export` reads the BR IFIC `.mdb` straight from the database: the 15 space tables and the terrestrial tables | GPL / LGPL, system tool, not bundled |
| ITU-R P.1546-6 table | `rules/p1546_land.csv` | generated once from the ITU reference implementation, see `docs/decisions.md` |
| any OpenAI-compatible chat endpoint | card and letter prose, optional | the user's choice |

The runtime needs nothing beyond what the pre-event template already pinned: the numbers are
standard-library math over CSV and JSON.

## Prior art this design answers

Four published sources cover the same ground. None is a dependency; they are the reasons the code is
arranged this way. Part 4 of `docs/decisions.md` records what each one changed, with the same links.

- A spectrum regulator's own paper on LLMs. Ghasemi and Guinand (Communications Research Centre (CRC)
  Canada, Ottawa; the authors' addresses are @ised-isde.gc.ca) list the failure modes in section III of *Accelerating Radio Spectrum Regulation Workflows
  with Large Language Models*: "Inaccuracy" (III-B, output "appearing credible but being factually
  wrong" and able to "misinform policies or public communication") and "Automation Bias" (III-C,
  "automatically generated outputs are preferred even when faced with contradictory evidence").
  https://arxiv.org/html/2403.17819v1 Here the model writes prose only, a numeric guard rejects any
  number the code did not produce, and the decision stays with the specialist.
- Selective classification, the literature name for `cannot_decide`. Heng and Soh define the two
  metrics a selective classifier is judged by, "Coverage" and "Selective Risk", and the trade-off
  between them. https://arxiv.org/html/2505.15008v3 `funnel.json` reports the same pair in its own
  terms: 196 notices in, 15 rows in the queue, and a reason code for every abstention.
- Technology-assisted review. Grossman and Cormack compared review with automated ranking against
  exhaustive manual review "as measured by recall, precision, and F1" (Richmond Journal of Law and
  Technology 17(3), Article 11, 2011). https://grossman.uwaterloo.ca/grossman-publications/jolt-2011/
  Their process is defensible because it reports those three numbers over a sample. The gates here
  read every notice, so their recall is 1 by construction and only the undecidable class carries
  uncertainty. That last sentence is our reading, not theirs.
- The ITU's own test for a compliance tool. EPFD examination under Article 22 rests on Rec. ITU-R
  S.1503-2 and Resolution 85 (Rev. WRC-23), and the Radiocommunication Bureau states that "at least
  two independent implementations" of S.1503 were needed before it would rely on the software.
  https://www.itu.int/epfdsupport/ This repository carries the same kind of evidence for a smaller
  check: the input SHA256, the rules version, and a fixed test vector.

## AI tools used

- Hermes Agent: the work was planned, implemented, documented and reviewed by agent roles on a
  shared kanban board (planner, two coders, writer, reviewer). The human owner chose the challenge,
  set the product framing, and makes the push decision.
- The drafting LLM inside `app/prose.py` is a component of the product rather than a build tool: it
  writes card prose, and the numeric guard rejects anything it invents.
- Keep the GenAI field of the submission form consistent with this section.

## Pre-existing work

This repository template (FastAPI skeleton, OpenAI-compatible client, test setup) was prepared
before the event, commit `6fe98b9`. That commit is the boundary: everything after it was built
during the hackathon, 6 to 8 Nov 2026.

## Documentation

| File | Contents |
|---|---|
| `docs/features.md` | Feature by feature: what it does, how it is built, which test file covers it |
| `docs/architecture.md` | One-page architecture: the pipeline diagram and the module table |
| `docs/decisions.md` | Decision log with reasons, including the choices made without user input |
| `docs/demo.md` | The three-minute demo script and the exact commands, with the expected output |
| `docs/demo-video.md` | The two-minute demo video: timed narration, screen plan, caption lines |
| `deploy/openshift/README.md` | What runs in the cluster and what runs on the laptop, the apply and call commands, and the measured evidence from the served Granite |
| `SUBMISSION.md` | Draft of the sinceai.app submission form and the Red Hat award checklist |
