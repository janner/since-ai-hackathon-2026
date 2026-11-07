# Features

What each part of the pipeline does, how it is built, and which test file covers it. Written against
commit `26187c3`, verified on 6 Nov 2026 with `make check` (114 passed) and a clean clone
(102 passed, 12 skipped).

Read a feature row in the tables below as: the module that owns the job, the tests that would fail
if the behaviour changed, and the number the tests lock in.

## F0: repository, lint, CI, test base

`pyproject.toml` pins the dependencies, the ruff rules and the `data` pytest marker. `Makefile`
wraps the commands (`make check` is lint plus tests). `.github/workflows/ci.yml` runs
`make install` and `make check` on Python 3.11, the lowest version `pyproject.toml` promises.
`tests/conftest.py` holds the session fixtures and the marker hook: when `data/itu-ific-3074/csv`
is missing, every test marked `data` gets a skip, so a clean clone stays green.

Tests: `tests/test_smoke.py::test_package_imports`, `tests/test_smoke.py::test_data_present`
(data). CI itself was not executed on GitHub during the hackathon; it is the same command run
locally.

## F1: ingest and normalisation

Reads the 15 IFIC tables from `<ific_dir>/csv`, the Finnish register from the frequencies-of-interest
file, and the M4 allocation table, and normalises every unit. Nothing here computes a gate: a value
that is missing stays `None` and the caller decides what that means.

`app/ingest.py` holds the pieces:

| Piece | Behaviour |
|---|---|
| `TABLES`, `REQUIRED_TABLES` | 15 table names; only `notice` and `freq` are mandatory, the rest may be absent |
| `mhz()` | `'3 520.500 MHz'` to 3520.5, `'300k'` to 0.3, `'0,1G'` to 100.0, `''` to `None`; understands `GHz`, `kHz`, `Hz` and the single letters, plus the Finnish comma decimal |
| `watts()` | `'145'` + `'W'` to 145.0, `'2'` + `'kW'` to 2000.0, `'mW'` scaled down |
| `rows()` | `csv.DictReader`; an empty file, a missing column or a header-only file raises `DataError` naming the file and the column |
| `load_register()` | `Station` records; a row without RX and TX is skipped and counted, a row without coordinates likewise; `Channel bandwidth` is used first and `Transmission bandwidth` as the fallback |
| `load_m4()` | accepts `{"value": [...]}` or a bare array; anything else raises `DataError` |
| `load_ific()` | builds `IficData` (notices, freq rows, beams, emission power per group, GEO, non-GEO, orbits, counts) and the input hash |
| `input_digest()` | one SHA256 over the 15 CSV files (name plus bytes), so a rerun on other data is visible |

`Station.centre_mhz` is RX when it exists and TX otherwise, `lo_mhz` and `hi_mhz` are the centre
plus or minus half the channel bandwidth.

Tests (`tests/test_ingest.py`, 21 collected): `test_mhz_normalises_units` (parametrised over nine
unit forms), `test_watts_converts_units`, `test_load_register_skips_rows_without_frequency`,
`test_station_uses_tx_when_rx_is_missing`, `test_load_ific_mini_counts`, and the six error paths
(`test_empty_file_is_a_clear_error`, `test_missing_column_names_the_column`,
`test_header_only_file_is_a_clear_error`, `test_missing_ific_directory_is_a_clear_error`,
`test_missing_required_table_is_a_clear_error`, `test_m4_without_value_array_is_a_clear_error`).
The two data tests `test_real_package_row_counts` and `test_real_register_and_hash` lock the
196 notices, 95 865 frequency rows, and a stable input hash.

## F2: protected bands derived from the register

No channel frequency is hardcoded. A protected band is a register row whose channel overlaps one of
the seven space allocations in `app/config.py`.

`app/bands.py`: `derive_bands()` keeps the stations that overlap an allocation and merges the
channels that overlap or touch (`MERGE_GAP_MHZ = 0.0`, so nothing is joined across a real hole).
`select_bands()` narrows the list to the demo slice. `stations_on()` returns the register rows in
register order. `groups()` counts how many of the seven allocations actually protect something.

Result on the real register: 84 rows, 26 bands in 7 groups. In the demo slice: 7 stations, 2 bands
in 1 group, with a 13.1 MHz hole between them.

Tests (`tests/test_bands.py`, 9): `test_overlaps_rejects_touching_bands`,
`test_derive_bands_merges_touching_channels_but_not_the_hole`,
`test_channels_that_touch_become_one_band`, `test_zero_bandwidth_is_a_point_not_a_crash`,
`test_select_bands_is_the_demo_slice`, `test_stations_on_band_uses_register_order`,
`test_band_stations_are_recorded`, plus the data tests `test_real_band_derivation` and
`test_real_bands_cover_the_register_rows`.

## F3: G1 band overlap and G2 visibility

`app/gates.py::gate1()` keeps a frequency row when `emi_rcp == "E"` (space transmits, Earth
receives) and the row overlaps a protected band. A notice whose `ntc_type` is `S` (an earth
station) is removed again: when such a notice sends "E" it is the station transmitting, not a
downlink. Every notice that does not survive gets a reason, `earth_station_notice` or
`no_band_overlap`, in the `dropped` map as `(stage, reason)`.

`gate2()` asks whether the satellite is visible from Finland at all. For a GEO notice with
`long_nom`, the elevation is computed from every register station and the notice is dropped as
`geo_below_horizon` when the best elevation is at or below 0°. For a non-GSO notice, `ngso_reach()`
gives the highest latitude the orbit reaches at zero elevation; the notice is dropped as
`ngso_never_visible` when that is below the southernmost station latitude. An orbit row without an
apogee or inclination is never dropped here. A notice with neither a `geo` nor an `orbit` row passes
G2 and carries the reason `no_orbit` at G3.

Tests (`tests/test_gates.py`): `test_mini_funnel_counts_and_reasons` walks the synthetic funnel,
`test_mini_vector_1_is_reproduced` reproduces the GEO vector on the fixture, and the data tests
`test_demo_slice_funnel`, `test_all_bands_funnel` and `test_case_126590032_cannot_be_decided` lock
the real counts (41 from 196 in the slice, 101 in the full run, 1 earth-station drop in the full
run) and the `ngso_never_visible` case 124520197.

## F4: PFD geometry and the Table 21-4 limit

`app/pfd.py` holds the physics and the limit table. Every number is a constant, a formula, or a row
read from `rules/rr21_table21_4.csv` (13 rows, columns `freq_lo_mhz`, `freq_hi_mhz`, `orbit`,
`a_db`, `k_db`, `ref_hz`, `offset`, `service`, `page`, `source`).

| Function | What it computes |
|---|---|
| `look(lat, lon, sat_lon)` | GEO elevation in degrees and slant range in km from a station |
| `slant(h_km, elev_deg)` | slant range from an altitude at an elevation angle |
| `fspl(d_km)` | free-space loss, `10*log10(4*pi*(d*1000)^2)` |
| `limit_row(limits, lo, hi, orbit)` | the row that contains the whole notified band, or `None`; a HEO notice without its own row falls back to the NGSO row |
| `limit_hz(row, elev, offset)` | the limit at an elevation angle: flat below 5°, linear between 5° and 25°, flat again above, minus `10*log10(ref_hz)`. Continuous at 25° |
| `x_fn(n)` | footnote 13 offset; `None` above 999, which forces `cannot_decide` |
| `y_fn(n_max)` | footnote 22 offset, `5*log10(max(NN, NS))`, applied above 2 |
| `ngso_reach(orbit)` | the highest latitude the orbit reaches at zero elevation |
| `is_heo(orbits)` | apogee above 18 000 km with an inclination between 35° and 145° |

Tests (`tests/test_pfd.py`, 12): `test_table_has_thirteen_rows`,
`test_limit_row_needs_a_row_that_contains_the_whole_band`,
`test_heo_uses_the_ngso_row_when_there_is_no_heo_row`, `test_vector_1_arithmetic`,
`test_vector_2_arithmetic`, `test_every_limit_row_is_continuous_at_25_degrees`,
`test_limit_hz_segments`, `test_limit_hz_offset_applies_to_the_low_angles`,
`test_x_and_y_offsets`, `test_ngso_reach`, `test_is_heo_needs_both_apogee_and_inclination`,
`test_look_returns_negative_elevation_below_the_horizon`.

## F5: G3 worst-case PFD and G4 queue

`app/gates.py::gate3()` walks the frequency rows of every notice that survived G1 and G2. For each
row it picks the limit row, the emission power for the group, the strongest beam gain over the beams
that cover the band, and the victim stations the row overlaps. Every candidate is then evaluated at
each elevation sample and the largest margin wins:

```
PFD = psd_max + beam_gain_max - fspl(d),   margin = PFD - limit_hz(row, elevation, offset)
```

A notice with nothing computable lands in `undecided` with one reason: `no_orbit`, `no_perigee`,
`no_limit_for_band`, `no_power`, `no_gain`, `x_needs_nv` or `no_station`. Classification uses the
margin rounded to two decimals: `exceeds` above 0 dB, `near` between −3 and 0 dB, `clear` at or
below −3 dB.

`gate4()` orders the queue `exceeds`, `near`, `cannot_decide`, `clear`, sorts by margin inside a
class, caps the list at `QUEUE_CAP` (20), and reports the overflow per class plus the
`coverage_gap` when the queue has empty seats.

Tests: `test_class_boundaries`, `test_mini_funnel_counts_and_reasons`,
`test_mini_non_gso_case_uses_the_pass_sweep`, `test_queue_order_and_coverage_gap`,
`test_gate4_overflows_in_class_order`, `test_demo_slice_funnel`, `test_all_bands_funnel`,
`test_vector_2_from_the_real_data`, `test_case_126590032_cannot_be_decided`.

## F6: case cards and the M4 allocation

`app/cards.py::build_card()` turns a `Case` into the card: `case_id`, `same_network`, `source`
(file, tables, keys), `parties`, `band`, `direction`, `coverage`, `victim`, `calculation`, `m4`,
`class`, `missing`, `next_action`, `audit`. The audit block carries `input_sha256`,
`rules_version` and `run_at`.

The `victim` block carries `power_w`, and the card carries a top-level `synthetic_data_warning`
that is set when the victim received power is above 1 GW: the register value is a synthetic
artefact, so it is shown but never used in the PFD. In the full run 20 cards are flagged.

M4 (`m4_lookup()`) is context, never a gate: it lists the sub-band IDs that overlap the notified
band, the merged band range in MHz, the Finnish services from the open data table and the source
URL. A band with no M4 row gets `rows: []` and `services_in_finland: "not allocated"`.

`same_network()` lists other notices of the same satellite and administration, or a notified
target. The card shows them; every notice is still decided on its own.

`missing_fields()` names the empty beam geometry (`s_beam.bore_long`, `bore_lat`, `maj_axis`,
`min_axis`) and a register row without gain or power. `render_card_md()` and `render_queue_md()`
write the Markdown, `results_rows()` writes the CSV rows, `render_run_log()` the log. In the CSV,
`results_rows()` leaves `class` empty for a notice dropped at G1 or G2 and writes `cannot_decide`
only for a case that reached G3 and could not be computed; `dropped_at` and `reason` carry the gate
and the cause. `render_run_log()` writes the `ific=` id of the input package alongside the hash and
the counts.

Tests (`tests/test_cards.py`, 7): `test_mini_card_has_the_whole_schema`,
`test_m4_lookup_is_context_not_a_gate`, `test_missing_register_field_is_reported`,
`test_results_rows_cover_every_notice` (asserts one row per notice, the empty `class` for a gate
drop and the `dropped_at` plus `reason`), `test_a_too_large_victim_power_is_flagged`,
`test_a_normal_victim_power_has_no_warning`, and the data test `test_golden_case_103500417`, which
locks every field of the plan's test vector including the band label 3 642–3 678 MHz.

## F7: the six output files and the CLI

`app/pipeline.py` is the entry point.

```bash
python -m app.pipeline --ific data/itu-ific-3074 \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json --out out/ [--all] [--limits rules/rr21_table21_4.csv]
```

It loads the inputs, derives the bands, runs the gates, builds a card per case with its prose
block, and writes `cases.json`, `cases.md`, `queue.md`, `funnel.json`, `3074_results.csv` and
`run.log` into `--out` (created if missing). The last step prints the funnel and the class counts.
A `DataError` such as a missing input file or an unreadable `--limits` CSV prints `error: ...` on
stderr and exits 2.

Tests (`tests/test_pipeline.py`, 12): `test_mini_run_writes_every_output`,
`test_mini_results_csv_has_one_row_per_notice`, `test_mini_funnel_json_mini_out`,
`test_mini_cases_json_and_markdown`, `test_run_log_records_the_hash_and_the_counts`,
`test_out_directory_is_created`, `test_missing_input_is_a_clear_error`,
`test_missing_argument_is_an_argparse_error`, `test_bad_input_returns_exit_code_two`,
`test_missing_limits_is_a_clear_error`, `test_register_without_stations_on_a_band_is_a_clear_error`,
and the data test `test_real_run_writes_the_documented_numbers`.

## F8: prose from an LLM, template as the floor, numeric guard

`app/prose.py` asks the configured chat endpoint for two sentences (`draft_summary`, `draft_letter`)
and decides what the card gets:

| Condition | Result |
|---|---|
| `LLM_BASE_URL` unset and no `chat` callable | `prose.source = "template"` |
| Endpoint raises | `prose.source = "template"` |
| Endpoint answers blank or whitespace | `prose.source = "template"` |
| Endpoint answers, and the guard rejects a number | `prose.source = "template_guard"` |
| Endpoint answers, guard passes | `prose.source = "llm"` |

The prompt is fixed and says plainly that no number may be invented and no verdict may be given.
A blank or whitespace answer is treated as a failure rather than prose, so it falls back to the
template. A refusal or an answer in the wrong language is not detected: the guard checks numbers,
not intent.

`app/guard.py` scans both sides for numbers, normalises the Finnish thousands separator and the
decimal comma, and compares signed values with a 0.01 tolerance. A minus right after a digit is a
range separator (`3 662-3 698`), not a sign; any other sign must match the card.

A pipeline run attaches the card summary only; `draft_letter` is exercised by tests and by the
correspondence template, and the CLI does not write letters to `out/`.

Tests: `tests/test_prose.py` 8 (`test_without_an_endpoint_the_template_is_used`,
`test_letter_template_asks_the_question`, `test_a_failing_llm_falls_back_to_the_template`,
`test_an_empty_llm_answer_falls_back` (parametrised over an empty and a whitespace answer),
`test_a_number_the_card_does_not_have_falls_back`, `test_a_clean_llm_answer_is_kept`,
`test_a_configured_endpoint_is_called`), `tests/test_guard.py` 6
(`test_scan_normalises_decimals_and_thousands`, `test_card_numbers_are_accepted`,
`test_invented_number_is_rejected`, `test_case_id_is_not_an_invented_number`,
`test_unit_names_are_not_numbers`, `test_empty_text_is_accepted`). Every test stubs the chat call:
no test opens a connection.

## F9: terrestrial side feature

`app/terrestrial.py` is independent of the space pipeline (no import from `app.gates` or
`app.pfd`) and is standard-library only.

```bash
python -m app.terrestrial --prev prev.json --curr curr.json \
  --register data/frequencies_of_interest.csv --out out/
```

Input shape, one issue per file:

```json
{"issue": "SYNTH-3076-B", "synthetic": true,
 "notices": [{"ntc_id": "1090011", "adm": "SVE", "stn_cls": "LM",
              "freq_min_mhz": 800, "freq_max_mhz": 805,
              "lat": 59.3, "lon": 18.1, "p_erp_kw": 30, "ant_h_m": 60, "act_code": "ADD"}]}
```

A row without `ntc_id` or without one of the frequency, position, power and height fields is
skipped and counted in `skipped_invalid`.

| Step | Behaviour |
|---|---|
| Diff | keyed by `ntc_id`; a change in band, position, power, height or class is `modified` |
| Filter | keeps `stn_cls` in `{LM, MVV}`, within 1 000 km of the nearest of the four Finnish test points, and overlapping the register on RX or TX |
| Field strength | `field_strength_p1546(freq, dist, h_ant, p_erp_kw)` interpolates the P.1546-6 land table linearly in frequency, height and distance, then adds `10*log10(p)`. Model: land path, 50 % of time, 50 % of locations, no terrain, 10 m receiving antenna |
| Extrapolation | a query outside any of the three table axes (frequency, antenna height, distance) clamps to the nearest node; the notice is flagged `extrapolated: true` when any of the four test points is outside |
| Trends | grouped by administration, band label, class and bandwidth; counts of new, modified and withdrawn against the previous issue |
| Anomalies | a group with nothing in the previous issue and three or more now |
| Threshold | `protection_threshold_dbuVm` is `null` and the criterion line says it is to be confirmed |

The distance to Finland is the nearest of the four test points (Helsinki, Turku, Lappeenranta,
Maarianhamina), not a polygon border. Both register directions count as overlap, because a channel
is a pair: RX 464.04 MHz and TX 454.04 MHz belong to the same licence.

Outputs: `terrestrial_findings.json`, `terrestrial_trends.csv`, `TERRESTRIAL.md`.

Tests (`tests/test_terrestrial.py`, 16): `test_diff_finds_new_modified_withdrawn` (3 new, 1
modified, 1 withdrawn), `test_diff_detects_moved_station`,
`test_filter_drops_far_and_non_land_mobile`, `test_findings_mark_synthetic_and_leave_threshold_open`,
`test_field_strength_matches_p1546_table_node`,
`test_field_strength_falls_with_distance_and_follows_power`,
`test_field_strength_rejects_unusable_input`, `test_extrapolated_flags_clamped_query`,
`test_findings_flags_extrapolated_per_point`, `test_run_writes_three_outputs`,
`test_load_issue_skips_rows_without_required_fields`, `test_load_issue_rejects_wrong_shape`,
`test_empty_extract_still_produces_outputs`, `test_register_without_frequency_columns_is_rejected`,
`test_cli_runs_and_fails_cleanly_on_missing_input`, and the data test
`test_fixture_bands_overlap_the_real_register`.

The P.1546 table in `rules/p1546_land.csv` was generated once, outside the runtime, with the ITU
reference implementation; see `docs/decisions.md`.

## F10: web UI and read-only API

`app/main.py` serves what the last pipeline run wrote. It does no analysis of its own: it reads
files, and every number on the page comes from them.

| Route | Returns |
|---|---|
| `GET /` | the single page, `app/static/index.html` |
| `GET /health` | `{"ok": true}` |
| `GET /api/funnel` | `out/funnel.json` |
| `GET /api/cases` | `out/cases.json` |
| `GET /api/cases/{case_id}` | one card, 404 when the id is unknown |
| `GET /api/queue` | `cases.json` in queue order, capped at 20 |

`KAISTA_OUT` (default `out`) points the API at another output directory. A missing file or broken
JSON answers 503 with the message from `app.pipeline`, not 500: a half-finished run is an expected
state. The page keeps working when the API fails and shows the error in a status line.

The page is Finnish, three panels wide (Suppilo, Jono, Kortti), styled with plain CSS and no
external request. Every value from `out/` is written with `textContent`, so a case id or a
satellite name cannot inject markup. The queue endpoint reads `cases.json`, which holds cards only,
so a `cannot_decide` notice has no row there; its count appears in the funnel panel.

Tests (`tests/test_api.py`, 9): `test_index_serves_the_finnish_page`, `test_health`,
`test_funnel_numbers`, `test_cases_returns_every_card`, `test_case_by_id`,
`test_unknown_case_id_is_404`, `test_queue_is_ordered_by_class_and_capped`,
`test_missing_out_is_503_and_the_page_still_loads` and `test_broken_json_is_503_not_500`. The
fixtures write their own synthetic `out/` into `tmp_path`, so the API tests need no challenge data.

## Tooling: fetching and converting the data

`scripts/fetch_data.py` downloads the IFIC 3074 zip and the M4 table, calls `mdb-export` for the 15
tables, and converts the frequencies-of-interest xlsx to CSV by finding the `Station number` header
row and skipping the Finnish header row behind it. It prints a SHA256 for every file and refuses a
response that is not a zip (`check_zip`), which is how a WAF challenge page gets caught.

Tests (`tests/test_fetch_data.py`, 2): `test_html_instead_of_zip_is_rejected`,
`test_xlsx_rows_skips_preamble_and_finnish_header`.

## Test fixtures

| Fixture | Contents |
|---|---|
| `tests/fixtures/ific_mini/csv/` | nine synthetic notices with frequency, group, emission, beam, GEO, non-GEO and orbit rows, including both plan test vectors and a case that cannot be decided |
| `tests/fixtures/register_mini.csv` | nine rows, eight of which load as stations (one has no frequency); five rows lack the antenna gain, two the power, two the RX frequency |
| `tests/fixtures/m4_mini.json` | four allocation rows, two of them inside the demo slice |
| `tests/fixtures/terrestrial_fixture.json` | two synthetic land-mobile issues in one file, `synthetic: true`, split into `prev` and `curr` for the CLI |
| `tests/fixtures/register_terrestrial_mini.csv` | a small register for the terrestrial filter |
