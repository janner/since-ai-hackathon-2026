# How it works, and how to see it

Everything below was run on 6 Nov 2026 against commit `26187c3`; the output blocks are the real
output, not illustrations. Numbers may move by a second or two between runs, and the timestamps and
`run_at` fields change with the clock.

## 1. One-time setup

```bash
sudo apt install mdbtools
uv sync
cp <path>/Traficom_SinceAI_Frequencies_of_interest_v05112026.xlsx data/
uv run python scripts/fetch_data.py
```

The last command downloads the IFIC package and the M4 table, runs `mdb-export` for the 15 tables,
converts the register xlsx to CSV, and prints a SHA256 per file. It needs a network. The
deterministic pipeline does not: it opens a connection only in the optional LLM prose step, and only
when `LLM_BASE_URL` is set.

## 2. The demo run: the 3.47 to 3.78 GHz slice

```bash
uv run python -m app.pipeline --ific data/itu-ific-3074 \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json --out out/
```

```
196 notices → G1 41 → G2 19 → G3 18 + 1 cannot decide
exceeds 9, near 5, clear 4, 19 in the queue (1 groups, 2 bands, 1.25 s)
wrote out/cases.json, cases.md, queue.md, funnel.json, 3074_results.csv, run.log
```

The first line is the funnel: 196 notices, 41 overlap a protected band, 19 of those can be seen from
Finland, 18 get a number and one cannot be decided. The whole run takes about a second and opens no
connection with no LLM configured.

## 3. What to look at

`out/queue.md` is the decision list, most urgent first:

```
# Queue (19 of 19)

Funnel: 196 → 41 → 19 → 18 + 1

| # | case | class | margin dB | reason |
|---|---|---|---|---|
| 1 | 124545403 | exceeds | 60,44 | exceeds |
| 2 | 125500066 | exceeds | 21,32 | exceeds |
| 3 | 125500277 | exceeds | 16,33 | exceeds |
| 4 | 103500417 | exceeds | 3,24 | exceeds |
| 5 | 303500417 | exceeds | 3,24 | exceeds |
| 6 | 124520183 | exceeds | 2,95 | exceeds |
```

(13 more rows follow; the file lists all 19.)

`out/cases.md` holds one card per computed notice. The one from the plan's test vector:

```
- **Satellite:** COMPASS-80E (GSO, CHN), beam CDN
- **Band:** 3 642-3 678 MHz
- **Victim:** station 983816 (MVV), elevation 4,85°
- **PFD:** -184,78 dB(W/m²/Hz) vs limit -188,02 dB(W/m²/Hz) → margin 3,24 dB
- **Limit:** ITU RR 2024 Art. 21 Table 21-4, 3 400-4 200 MHz, FSS (space-to-Earth), GSO, p. 287
- **M4 in Finland:** MOBILE AND FIXED
- **Missing:** s_beam.bore_long, s_beam.bore_lat, s_beam.maj_axis, s_beam.min_axis
- **Question:** Can China confirm the service area of the COMPASS-80E CDN beam and whether it illuminates Finland in the 3 642-3 678 MHz range?
```

Four things to point at on that card. The PFD, the limit and the margin come from the calculation
block (max PSD −50,0 dBW/Hz, beam gain 28,5 dBi, distance 41 143 km, free-space loss 163,28 dB).
The limit is a citation, not a constant: `rules/rr21_table21_4.csv` holds the row. The `Missing`
line is why the case exists at all: IFIC 3074 does not declare the beam geometry, so the tool cannot
say whether Finland is inside the beam, and the card asks instead of concluding. `Question` is the
draft the administration would receive.

`out/3074_results.csv` has one row per notice in the input, including the 177 the funnel dropped
(155 at G1, 22 at G2), each with its stage and reason. The same notice as a row:

```
103500417,CHN,COMPASS-80E,G,GSO,,,exceeds,3642.0,3678.0,983816,4.85,-184.78,-188.02,3.24,"ITU RR 2024 Art. 21 Table 21-4, 3 400-4 200 MHz, FSS (space-to-Earth), GSO, p. 287",MOBILE AND FIXED,s_beam.bore_long;s_beam.bore_lat;s_beam.maj_axis;s_beam.min_axis
```

`out/run.log` is the audit line:

```
run_at=2026-11-06T22:57:47+02:00
input_sha256=2b7683bb00f0a998e40888b6502d7d229ccd7ec0d88a5b71b9a9e0d64d8497be
rules_version=1.1.0
ific=ific3074
mode=slice
notices=196
freq_rows=95865
stations_on_band=7
bands=2
visible=GEO 16 NGSO 3
g1=41 g2=19 g3=18 cannot_decide=1
elapsed_s=1.29
```

The hash covers the 15 input CSVs, so a rerun on another package is visible. `stations_on_band=7`
and `bands=2` are the demo slice; the 13.1 MHz hole between the two bands is real and the tool does
not cover it.

`out/funnel.json` carries the same counts as JSON with the drop reasons
(`no_band_overlap` 155, `geo_below_horizon` 21, `ngso_never_visible` 1) for anything that reads
files instead of humans.

## 4. The whole register

```bash
uv run python -m app.pipeline --ific data/itu-ific-3074 \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json --out out/ --all
```

```
196 notices → G1 101 → G2 75 → G3 64 + 11 cannot decide
exceeds 26, near 15, clear 23, 20 in the queue (7 groups, 26 bands, 5.51 s)
```

This is the accuracy run: all seven space bands, 84 register stations on the bands, 26 protected
bands in 7 groups, and a queue that overflows its cap of 20 (`overflow: exceeds 6, near 15,
cannot_decide 11, clear 23` in `funnel.json`). The counts are one notice above the plan
(101/75/11 against 100/74/10) for the reason in `docs/decisions.md` (I1).

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
`/api/queue`, `/health`. The queue endpoint lists computed cards only, so the one `cannot_decide`
notice in the slice has no row there; its count is in the funnel panel.

## 6. The terrestrial side feature

The fixture holds both issues in one file, and the CLI takes one issue per file:

```bash
uv run python - <<'PY'
import json
prev, curr = json.load(open("tests/fixtures/terrestrial_fixture.json"))["issues"]
json.dump(prev, open("prev.json", "w"))
json.dump(curr, open("curr.json", "w"))
PY

uv run python -m app.terrestrial --prev prev.json --curr curr.json \
  --register data/frequencies_of_interest.csv --out out/
```

```
3 new, 1 modified, 1 withdrawn; 12 notices in reach; -> out/
```

`out/TERRESTRIAL.md` is the readable report: the diff table, the field strength at the four Finnish
test points, the trends and the anomalies.

```
| muutos | ntc_id | hallinto | kaista | kentät |
|---|---|---|---|---|
| modified | 1090006 | RUS | 453.9-454.1 MHz | p_erp_kw |
| withdrawn | 1090010 | RUS | 800-805 MHz | - |
| new | 1090011 | SVE | 800-805 MHz | - |
| new | 1090012 | SVE | 800-805 MHz | - |
| new | 1090013 | SVE | 800-805 MHz | - |

Uudet 3, muutetut 1, poistetut 1.

| ntc_id | hallinto | kaista | Helsinki | Turku | Lappeenranta | Maarianhamina |
|---|---|---|---|---|---|---|
| 1090001 | EST | 453.9-454.1 MHz | 26.5 | 9.4 | -1.1 | -3.0 |
| 1090004 | SVE | 796-796.5 MHz | -14.8 | -0.6 | -32.6 | 17.7 |
| 1090007 | RUS | 900-905 MHz | -0.7 | -16.7 | 34.1 | -29.6 |

## Poikkeamat

- SVE 800-805 MHz: ei ilmoituksia edellisessä issuessa, nyt 3.
```

(Three of the twelve rows are shown; the same tables cover all of them.)

The header of the same file states the model and the open question: source `synthetic_fixture`
(marked as synthetic, no real 3076 data), model `P.1546-6 land, 50/50, no terrain`, and protection
threshold `None` with the criterion to be confirmed. The tool reports a calculated estimate and
claims no exceedance, because no threshold was given.

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
make check        # ruff check, ruff format --check, pytest: 114 passed with data/
```

In a clean clone without `data/`, the data tests skip themselves: 102 passed, 12 skipped. The number
to quote for "does it work on my machine" is that one, since it needs no challenge data.

## 9. Three-minute demo script

| Time | On screen | What to say |
|---|---|---|
| 0:00 | terminal, `wc -l` on the freq CSV | 196 notices, 95 865 frequency rows, published every two weeks, checked by hand today |
| 0:20 | run the slice command, funnel line appears | 196 to 41 to 19 to 18 plus one that cannot be decided |
| 0:50 | `out/cases.md`, card 3074-103500417 | the number, the citation for the limit, the missing beam geometry, the question we would send |
| 1:40 | `queue.md`, row 15, case 126590032 | the case the tool refuses to decide, with the reason `no_power`, and why that is a feature |
| 2:20 | terrestrial split and run, `TERRESTRIAL.md` | the same style for terrestrial notices: diff, field strength, trends, threshold open |
| 2:50 | the UI, or `run.log` | every number is reproducible from the hash and the rules version; the human decides |

If the UI is not running, the demo works from `cases.md` and `queue.md` alone. The deterministic run
needs no network, and nothing breaks when the language model is absent.
