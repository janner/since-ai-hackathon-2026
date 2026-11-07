# Features

What each part of the pipeline does, how it is built, and which test file covers it. Written against
commit `5be8bd5`, verified on 7 Nov 2026 with `make check` (179 passed) and a clean clone
(131 passed, 48 skipped).

For a test count, quote the clean-clone number: it needs no challenge data.

Read a feature row in the tables below as: the module that owns the job, the tests that would fail
if the behaviour changed, and the number the tests lock in.

## F0: repository, lint, CI, test base

`pyproject.toml` pins the dependencies, the ruff rules and the `data` pytest marker. `Makefile`
wraps the commands (`make check` is lint plus tests). `.github/workflows/ci.yml` runs
`make install` and `make check` on Python 3.11, the lowest version `pyproject.toml` promises.
`tests/conftest.py` holds the session fixture and the marker hook: when
`data/itu-ific-3074/ific3074.mdb` is missing, every test marked `data` gets a skip, so a clean clone
stays green.

Tests: `tests/test_smoke.py::test_package_imports`, `tests/test_smoke.py::test_data_present`
(data). CI itself was not executed on GitHub during the hackathon; it is the same command run
locally.

## F1: ingest and normalisation

Reads the 17 IFIC tables straight from the BR IFIC Access database with `mdb-export`, the Finnish
register from the frequencies-of-interest file, and the M4 allocation table, and normalises every
unit. Nothing here computes a gate: a value that is missing stays `None` and the caller decides what
that means.

`app/ingest.py` holds the pieces:

| Piece | Behaviour |
|---|---|
| `TABLES`, `REQUIRED_TABLES` | 17 table names; only `notice` and `freq` are mandatory, the rest may be absent |
| `_export()` | `mdb-export <mdb> <table>` through `subprocess` (no shell); a missing `mdb-export` or a failing table raises `DataError` |
| `mhz()` | `'3 520.500 MHz'` to 3520.5, `'300k'` to 0.3, `'0,1G'` to 100.0, `''` to `None`; understands `GHz`, `kHz`, `Hz` and the single letters, plus the Finnish comma decimal |
| `watts()` | `'145'` + `'W'` to 145.0, `'2'` + `'kW'` to 2000.0, `'mW'` scaled down |
| `deadline()` | `'12/19/26 00:00:00'` (the shape `mdb-export` gives `grp_res35.d_ms_next_deadline`) to `date(2026, 12, 19)`; anything else `None`, never a guess |
| `iter_rows()` | streams a CSV row by row with `csv.DictReader`; an empty file, a missing column or a header-only file raises `DataError` naming the file and the column |
| `rows()` | `list(iter_rows())`, for the callers that want the whole file |
| `load_register()` | `Station` records, streamed from `iter_rows()`; a row without RX and TX is skipped and counted, a row without coordinates likewise; the bandwidth is the smaller of `Channel bandwidth` and `Transmission bandwidth`, with either column as the fallback; an optional `bands` argument keeps only the stations whose channel touches one of the run's bands |
| `load_m4()` | accepts `{"value": [...]}` or a bare array; anything else raises `DataError` |
| `load_ific()` | reads the MDB with `mdb-export` and builds `IficData` (notices, freq rows, beams, emission power per group, GEO, non-GEO, orbits, links, Resolution 35 group deadlines in `res35`, counts); `file` is the MDB name and `input_sha256` its SHA256 |
| `sha256()` | one file's SHA256; `input_digest()` (used by the terrestrial path) one SHA256 over several files |

`Station.centre_mhz` is RX when it exists and TX otherwise, `lo_mhz` and `hi_mhz` are the centre
plus or minus half the channel bandwidth. `Notice.prov` carries the regulatory stage of the filing
and `Station.directivity` the register's `Directivity` code (`D`, `ND` or empty); neither is read by
a gate, and only the card uses them.

Tests (`tests/test_ingest.py`, 27 collected): `test_mhz_normalises_units` (parametrised over nine
unit forms), `test_watts_converts_units`, `test_deadline_reads_the_exported_date` (the
`grp_res35` date shape, and the empty and unparseable forms stay `None`),
`test_load_register_skips_rows_without_frequency`,
`test_station_uses_tx_when_rx_is_missing`,
`test_bandwidth_is_the_smaller_of_channel_and_transmission`,
`test_load_register_keeps_only_the_bands_asked_for` (the band filter, with the skip counters still
counting the dropped rows), `test_register_streams_a_million_rows` (1 M synthetic rows: 1 000 kept,
`tracemalloc` peak under 20 MB),
`test_exported_rows_are_mapped_to_ific_data` (the mapping from exported rows to `IficData`, with
`mdb-export` stubbed), `test_ntc_lnk_maps_a_filing_to_the_notice_it_follows` (the same stub: the
links, and an `ntc_lnk` row without a target), and the seven error paths (`test_empty_file_is_a_clear_error`,
`test_missing_column_names_the_column`, `test_header_only_file_is_a_clear_error`,
`test_missing_mdb_is_a_clear_error`, `test_missing_mdb_export_is_a_clear_error`,
`test_unreadable_table_is_a_clear_error`, `test_m4_without_value_array_is_a_clear_error`).
The data tests `test_real_mdb_row_counts`, `test_real_register_and_mdb_hash` and
`test_real_register_keeps_rows_without_a_licence_class` lock the 196 notices, 95 865 frequency rows,
the 254 `grp_res35` rows, the MDB SHA256, and the 294 register rows that carry no `Class of licence`.

## F2: the register's own bands (utility, not in the run path)

`app/bands.py` answers one question: what would the delivered register protect on its own? No channel
frequency is hardcoded: a band is a register row whose channel overlaps one of the seven space
allocations (`derive_bands()` merges touching channels, `select_bands()` narrows to the demo slice,
`stations_on()` returns the rows in register order, `groups()` counts the allocations that protect
something). The run does not call it: the run's bands come from `app/config.py`, and the register is
a reference (D17). The module stays for that question and for its tests. On the real register it
finds 84 rows, 26 bands in 7 groups; in the demo slice, 7 stations and 2 bands, because a 13,1 MHz
hole splits the slice.

Tests (`tests/test_bands.py`, 9): `test_overlaps_rejects_touching_bands`,
`test_derive_bands_merges_touching_channels_but_not_the_hole`,
`test_channels_that_touch_become_one_band`, `test_zero_bandwidth_is_a_point_not_a_crash`,
`test_select_bands_is_the_demo_slice`, `test_stations_on_band_uses_register_order`,
`test_band_stations_are_recorded`, plus the data tests `test_real_band_derivation` and
`test_real_bands_cover_the_register_rows`.

## F3: G1 band overlap and G2 visibility

`app/gates.py::gate1()` keeps a frequency row when `emi_rcp == "E"` (space transmits, Earth
receives) and the row overlaps one of the run's scope bands (the seven space allocations with
`--all`, the demo slice otherwise; `app/config.py`). With `GUARD_MHZ > 0` (`app/config.py`, default
0.0) a row that only comes within that distance of a band also passes, and the notice is returned in
an `adjacent` set: its card is marked `adjacent: true` and its class is capped at `near`. A notice
whose `ntc_type` is `S` (an earth station) is removed again: when such a notice sends "E" it is the
station transmitting, not a downlink. Every notice that does not survive gets a reason,
`earth_station_notice` or `no_band_overlap`, in the `dropped` map as `(stage, reason)`.

`gate2()` asks whether the satellite is visible from Finland at all. For a GEO notice with
`long_nom`, the elevation is computed from every point of the territory edge and the notice is
dropped as `geo_below_horizon` when the best elevation is at or below 0°. For a non-GSO notice,
`ngso_reach()` gives the highest latitude the orbit reaches at zero elevation; the notice is dropped
as `ngso_never_visible` when that is below the southernmost territory latitude. An orbit row without
an apogee or inclination is never dropped here. A notice with neither a `geo` nor an `orbit` row
passes G2 and carries the reason `no_orbit` at G3.

Tests (`tests/test_gates.py`, 14): `test_class_boundaries`, `test_guard_mhz_zero_is_the_plain_overlap`
and `test_guard_mhz_lets_an_adjacent_notice_through` walk the adjacent-channel guard both ways on a
two-row input, `test_a_notice_type_s_sending_E_is_dropped` covers the earth-station reason, and the
data tests `test_demo_slice_funnel`, `test_all_bands_funnel`, `test_missing_perigee_cannot_be_decided`
and `test_case_126590032_cannot_be_decided` lock the real counts (41 from 196 in the slice, 113 in
the full run, 1 earth-station drop in the full run) and the `ngso_never_visible` case 124520197.

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
that cover the band, and the Finnish allocation (`app/allocation.py`). Every candidate is then
evaluated and the largest margin wins:

```
PFD = psd_max + beam_gain_max - fspl(d),   margin = PFD - limit_hz(row, elevation, offset)
```

For a GEO notice the samples are the 552 vertices of the territory edge (`app/territory.py`): the
land borders with Sweden, Norway and Russia plus the territorial sea outer limit. The worst case over
an area sits on its edge, because the slant range grows away from the sub-satellite point and the
limit does not rise faster. A non-GSO notice is sampled over a pass from 0° to 90° in 0,1° steps,
which is a worst case over every latitude and needs no location.

A notice with nothing computable lands in `undecided` with one reason: `no_orbit`, `no_perigee`,
`no_limit_for_band`, `no_power`, `no_gain` or `x_needs_nv`. Classification uses the margin rounded to
two decimals: `exceeds` above 0 dB, `near` between −3 and 0 dB, `not_space` at or below −3 dB when
the band has no space-to-Earth satellite service in Finland, `clear` otherwise. An adjacent-channel
case (see F3) keeps its margin but is capped at `near`: the Table 21-4 limit belongs to the notified
band and does not apply outside it. The register's rows on the band are a reference only: the block
names the one with the highest margin, and the number itself is taken at the territory edge.

`gate4()` orders the queue `exceeds`, `near`, `not_space`, `cannot_decide`, and inside a class by
stage rank (advance publication and coordination request before the MIFR notification, then
Resolution 49), then by the notice's earliest upcoming Resolution 35 deadline, then by margin. A
stage another administration can still influence therefore comes before a filing already recorded,
and a filing whose group falls due soonest comes first inside its stage. A notice whose groups carry
no `grp_res35` deadline sorts behind one that has one; a passed deadline behind every upcoming one
(most recent first). The deadline is chosen per notice by `notice_deadlines()`: the earliest
upcoming date over the groups of the notice, else the latest one that has passed. `clear` cases stay
in `cases.json` and the CSV but out of the queue. There is no cap. The stage itself comes from
`notice.prov` through `app/config.py::regulatory_stage()`.

Measured in IFIC 3074: `grp_res35` (`grp_id`, `d_ms_next_deadline`) has 254 rows — 26 groups due
19 Dec 2026, 126 due 19 Jan 2031, 6 due 19 Jul 2031 and 96 already passed (18 Dec 2019). They
belong to three notices, 125500277, 126500053 and 325500168; 125500277 is one of the 20 demo cases,
so the demo queue moves by one row and every other number is unchanged.

Tests (`tests/test_gates.py`, 17 collected): `test_class_boundaries`,
`test_notice_deadlines_pick_the_earliest_upcoming` (a notice with several group deadlines, one
upcoming, one passed, one absent), `test_queue_orders_by_stage_then_deadline_then_margin`,
`test_queue_holds_every_concern_and_no_clear`, `test_queue_puts_coordination_before_notification`,
`test_queue_order`, `test_only_one_demo_case_carries_a_res35_deadline` (125500277, due 19 Dec 2026,
sorts ahead of a larger margin in its stage), `test_an_adjacent_case_is_capped_at_near`,
`test_demo_slice_funnel`, `test_all_bands_funnel`, `test_vector_2_from_the_real_data`,
`test_case_126590032_cannot_be_decided`.

## F6: case cards and the M4 allocation

`app/cards.py::build_card()` turns a `Case` into the card: `case_id`, `same_network`, `source`
(file, IFIC number, SHA256, tables, keys), `parties`, `band`, `direction`, `coverage`, `point`,
`victim`, `calculation`, `m4`, `class`, `adjacent`, `deadline`, `deadline_passed`,
`regulatory_stage`, `filing_action`, `filing_follows`, `threshold_note`, `missing`, `next_action`,
`audit`. The audit block carries `input_sha256`, `rules_version` and `run_at`; the `input_sha256` is
the SHA256 of the BR IFIC MDB the run read.

`regulatory_stage` restates `notice.prov` as `{provision, label, source}`, for example `No. 11.2` /
"notification recorded in the MIFR" / `ITU RR 2024, Vol 1, No. 11.2`. The stage itself carries no
deadline and no window length; `label` is the one sentence of what the stage means (advance
publication and coordination request are stages another administration can still influence, the
notification is a recording in the MIFR). The Resolution 35 deadline has its own field:
`deadline` is the notice's earliest upcoming group deadline from `grp_res35` (see F5) as a Finnish
date, `deadline_passed` says whether it is already behind the run, and `render_card_md()` writes
`- **Resolution 35 deadline:** <date>`, appending `(passed)` for a passed one. No group of the
notice carrying a deadline leaves both fields empty (`null` / `false`) and no line. In the demo
slice only 125500277 carries one: 19.12.2026.

`adjacent` is the guard flag from G1. `threshold_note` is set when the victim is directive
(`victim.directivity` not `ND`) and its gain is at or above 20 dBi: it names a lower possible
trigger level and changes no number and no class. It never compares the station's azimuth with the
satellite direction (see I18 in `docs/decisions.md`).

The `victim` block carries `power_w`, and the card carries a top-level `synthetic_data_warning`
that is set when the victim received power is above 1 GW: the register value is a synthetic
artefact, so it is shown but never used in the PFD. In the `--all` run 14 cards are flagged.
`point` carries the territory edge vertex where the level was taken (`lat`, `lon`, `place`), or
`any point in Finland` for a non-GSO pass; `victim` is the reference row from the register, not the
anchor of the number (D17).

M4 (`app/allocation.py::m4_lookup()`) is a finding, not only context: it lists the sub-band IDs that
overlap the notified band, the merged band range in MHz, the Finnish services from the open data
table, `space_to_earth` and the source URL. `space_to_earth` is true only when an overlapping row
names a satellite service with the space-to-Earth direction (or no direction); an uplink-only or
inter-satellite row does not count. A band with no M4 row gets `rows: []`,
`services_in_finland: "not allocated"` and the same `not_space` finding.

`same_network()` lists other notices of the same satellite and administration, or a notified
target. The card shows them; every notice is still decided on its own.

`missing_fields()` names every empty input, beam geometry (`s_beam.*`) included. `_blocking()`
keeps the ones that decide a case: since Traficom's Q3 answer the beam geometry is not among them,
because the worst case covers it. `render_card_md()` writes the card (its `filing_follows` links
become a "This filing follows <ntc_id> (<reason>)" line) and `render_queue_md()`
write the Markdown, `results_rows()` writes the CSV rows, `render_run_log()` the log. In the CSV,
`results_rows()` leaves `class` empty for a notice dropped at G1 or G2 and writes `cannot_decide`
only for a case that reached G3 and could not be computed; the `regulatory_stage` column carries the
provision for every notice (dropped included); `dropped_at` and `reason` carry the gate and the
cause. `render_run_log()` writes the IFIC number, the input file name and the hash alongside the
counts.

Tests (`tests/test_cards.py`, 13): `test_card_has_the_whole_schema`,
`test_m4_lookup_names_the_service_and_the_downlink`, `test_missing_register_field_is_reported`,
`test_results_rows_cover_every_notice` (asserts one row per notice, the empty `class` for a gate
drop and the `dropped_at` plus `reason`), `test_a_too_large_victim_power_is_flagged`,
`test_a_normal_victim_power_has_no_warning`, `test_directive_antenna_gets_a_threshold_note`,
`test_deadline_line_marks_a_passed_deadline` and `test_queue_md_carries_a_deadline_column`
(synthetic: the card line and the `deadline` column, a passed deadline marked, a missing one `-`),
and the data tests `test_golden_case_103500417`, which locks every field of the plan's test vector
including the band label 3 442–3 478 MHz and the `source` block,
`test_prov_distribution_and_the_card_stage`, which locks the `prov` distribution (50 / 76 / 65 / 5)
and the card stage block, `test_card_carries_the_filing_chain_and_the_queue_action`, which locks the
`filing_follows` link and the `action` column of `queue.md`, and
`test_the_demo_card_shows_its_res35_deadline`, which locks 125500277's 19.12.2026 line and the
marked passed form.

## F7: the output files and the CLI

`app/pipeline.py` is the entry point.

```bash
python -m app.pipeline --ific data/itu-ific-3074/ific3074.mdb \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json --out out/ [--all] [--limits rules/rr21_table21_4.csv]
```

It loads the inputs, derives the bands, runs the gates, builds a card per case with its prose
block, and writes `cases.json`, `cases.md`, `queue.md`, `funnel.json`, `3074_results.csv` and
`run.log` into `--out` (created if missing), plus `letters/<case_id>.md` for every `exceeds` case.
`3074_results.csv` has one row per notice and 26 columns: `ific`, `case_id`, `ntc_id`, `adm`,
`sat_name`, `ntc_type`, `orbit`, `dropped_at`, `reason`, `class`, `regulatory_stage`,
`freq_min_mhz`, `freq_max_mhz`, `bandwidth_mhz`, `station`, `lat`, `lon`, `victim_rx_mhz`,
`elevation_deg`, `pfd_dbw_m2_hz`, `limit_dbw_m2_hz`, `margin_db`, `limit_source`, `m4_services`,
`m4_space`, `missing`. A dropped notice fills `ific`, `ntc_id`, `dropped_at` and `reason` and leaves
`case_id`, `bandwidth_mhz` and `victim_rx_mhz` empty.
The last step prints the funnel and the class counts.
A `DataError` such as a missing input file or an unreadable `--limits` CSV prints `error: ...` on
stderr and exits 2.

Tests (`tests/test_pipeline.py`, 13): `test_slice_run_writes_every_output`,
`test_slice_run_matches_the_documented_anchors`, `test_slice_cases_json_and_markdown`,
`test_run_log_records_the_source_and_the_counts`,
`test_letters_are_written_for_the_exceeds_cards`, `test_out_directory_is_created`,
`test_missing_input_is_a_clear_error`, `test_missing_argument_is_an_argparse_error`,
`test_bad_input_returns_exit_code_two`, `test_missing_limits_is_a_clear_error`,
`test_register_without_stations_on_a_band_is_a_clear_error`, and the data tests
`test_one_command_writes_both_space_and_terrestrial_outputs` and
`test_without_the_terrestrial_flag_the_space_run_is_unchanged`. Every test that reads a run output
runs the CLI once on the real MDB into a temporary `out/`.

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

The prompt is fixed, asks for English, and says plainly that no number may be invented and no
verdict may be given. The floor templates are `templates/case_en.md` for the card and
`templates/correspondence_fi_en.md` for the letter (the letter carries a Finnish closing line).
A blank or whitespace answer is treated as a failure rather than prose, so it falls back to the
template. A refusal or an answer in the wrong language is not detected: the guard checks numbers,
not intent.

`app/guard.py` scans both sides for numbers, normalises the Finnish thousands separator and the
decimal comma, and compares signed values with a 0.01 tolerance. A minus right after a digit is a
range separator (`3 662-3 698`), not a sign; any other sign must match the card.

A pipeline run attaches the card summary to every card and writes the correspondence letter to
`out/letters/<case_id>.md` for each `exceeds` case (see F7); the template is the floor for both.

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

`app/terrestrial.py` is the side path of the same program: `app.pipeline --terrestrial` runs it in
the same pass as the space funnel, into the same `out/`, and its output carries the same `source`
(file, SHA256, tables, keys) / `audit` (input SHA256, rules version, run time) / `missing` contract
as a case card. It shares `app.ingest`'s provenance (`sha256`, `input_digest`) and
`app.config.RULES_VERSION`, imports nothing from `app.gates` or `app.pfd`, and its own calculation
path is ITU-R P.1546-6 field strength, not the PFD gates. It reads the real BR IFIC terrestrial
databases with the same `mdb-export` reader `app/ingest.py` uses.

```bash
uv run python -m app.pipeline --ific data/itu-ific-3074/ific3074.mdb \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json \
  --terrestrial data/itu-terr-ific/brific3076.mdb \
  --terrestrial-prev data/itu-terr-ific/brific3075.mdb --out out/
```

Tables used, one row per `fxm_terra` notice:

- `fxm_terra`: `terrakey`, `adm`, `stn_cls`, `freq_min`/`freq_max` (MHz), `geo_key`, `intent`.
- `fxm_geo`: `geo_key` → `lat_dec`, `long_dec` (a `ZONE` row carries no point and is skipped).
- `fxm_ant`: per `terrakey` and `ant_key` the `pwr_dbw`, `pwr_eiv` (`E` = ERP, `I` = EIRP),
  `hgt_agl` and `tx_rx`. The antenna row is the TX row with the smallest `ant_key`.

`pwr_dbw` is dBW; an EIRP value is converted to ERP by −2.15 dB. A row without frequency, location
or power is counted under the top-level `missing` block, under its reason (`frequency` / `location` /
`power`), and not computed; a missing antenna height leaves the field strength empty rather than
guessed.

| Step | Behaviour |
|---|---|
| Diff | from `fxm_terra.intent`: ADD → `new`, MODIFY → `modified`, SUPPRESS → `withdrawn`, RECORDED → the stock, not a change. The IFIC is not a cumulative database (3075 and 3076 share no `terrakey`), so the change is this field, not a key comparison |
| Filter | keeps `stn_cls` in `{FB, ML, FL}`, within 1 000 km of the nearest point on the Finnish border, and overlapping the register on RX or TX. The border is the land borders with Sweden, Norway and Russia plus the outer limit of the territorial sea (12 nautical miles), not the coastline (Traficom 7.11.2026) |
| Field strength | `field_strength_p1546(freq, dist, h_ant, p_erp_kw)` interpolates the P.1546-6 land table linearly in frequency, height and distance, then adds `10*log10(p)`. Model: land path, 50 % of time, 50 % of locations, no terrain, 10 m receiving antenna |
| Extrapolation | a query outside any of the three table axes (frequency, antenna height, distance) clamps to the nearest node; the notice is flagged `extrapolated: true` when any border sample is outside |
| Trends | grouped by administration, band label, class and bandwidth; new, modified and withdrawn against the same group in the previous number (3075) |
| Anomalies | a group with nothing in the previous number and three or more now |
| Threshold | the ECC T/R 25-08 A1.2.3 coordination values are confirmed (0/6/12/18/20 dBµV/m by band, 25 kHz reference, 10 % time, 10 m receiving antenna) and applied per notice; Traficom 7.11.2026 applies the same 20 dBµV/m above 470 MHz. The national M4 value is not confirmed. The criterion line names the three tiers (ITU RR Art. 21 Table 21-4 PFD → ECC T/R 25-08 trigger field strength → national M4 / Traficomin taajuusjakotaulukko) |

Every finding carries its own source reference: the IFIC number, `terrakey`, `adm_ref_id`, `adm`,
`intent` and the tables it came from, alongside `band`, `distance_to_finland_km`, `p_erp_kw`,
`ant_h_m` and the border field-strength values. The document carries `source` / `prev_source` (file,
SHA256, tables, keys), `audit` (input SHA256, rules version, run time) and `missing`; the readable
report header shows the file name and SHA256 of both MDBs.

The distance to Finland is the nearest point on the border polyline in
`rules/finland_border.csv`, not a single representative point. The polyline is the land borders with
Sweden (SE), Norway (NO) and Russia (RU) plus the outer limit of the territorial sea (TS, the 12
nautical mile line from Marine Regions); the coastline is not a border (Traficom 7.11.2026). Both
register directions count as overlap, because a channel
is a pair: RX 464.04 MHz and TX 454.04 MHz belong to the same licence.

Measured on the real pair: 3076 has 4 057 `fxm_terra` rows, `intent` ADD 2 905 / MODIFY 163 /
SUPPRESS 413 / RECORDED 576, 313 Russian notices (FX 188, ML 68, FB 57); the filter leaves 28
notices in reach of the register. 40 rows are skipped for a missing field (31 power, 9 location).

Outputs: `terrestrial_findings.json`, `terrestrial_trends.csv`, `TERRESTRIAL.md`.

Tests (`tests/test_terrestrial.py`, 21): `test_diff_intents_reads_the_intent_field`,
`test_filter_keeps_land_mobile_in_reach`, `test_trends_group_by_adm_band_class_width`,
`test_findings_leaves_threshold_open_and_cites_the_source`,
`test_params_say_what_the_field_strength_is_computed_for`,
`test_field_strength_matches_p1546_table_node`,
`test_field_strength_falls_with_distance_and_follows_power`,
`test_field_strength_rejects_unusable_input`, `test_extrapolated_flags_clamped_query`,
`test_findings_flags_extrapolated_per_point`, `test_a_notice_without_antenna_height_gets_no_value`,
`test_run_writes_three_outputs`, `test_load_issue_mdb_rejects_a_missing_file`,
`test_cli_fails_cleanly_on_missing_input`, `test_register_counts_both_rx_and_tx_directions`,
`test_register_without_frequency_columns_is_rejected`, and the four data tests
`test_real_3076_intent_distribution_and_source`, `test_real_3076_russian_federation_notices`,
`test_real_mdb_prints_the_example_finding` and `test_cli_runs_on_the_real_mdb`, which read the real
MDBs and skip when `data/itu-terr-ific` is missing.

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
| `GET /api/queue` | `cases.json` in queue order |

`KAISTA_OUT` (default `out`) points the API at another output directory. A missing file or broken
JSON answers 503 with the message from `app.pipeline`, not 500: a half-finished run is an expected
state. The page keeps working when the API fails and shows the error in a status line.

The page is English, three panels wide (Funnel, Queue, Card), styled with plain CSS and no
external request. Every value from `out/` is written with `textContent`, so a case id or a
satellite name cannot inject markup. The queue row and the card show the regulatory stage with
the ITU short name (`No. 9.1` advance publication, API; `No. 9.6` coordination request, CRC;
`No. 11.2` MIFR), the queue row spells out the filing action it reads from `filing_action`
(`A` New filing, `M` Modification, `S` Suppression), and the card names the protected station and
its coordinates: that is where the worst case is calculated. The queue endpoint reads `cases.json`,
which holds cards only, so a
`cannot_decide` notice has no row there; the funnel panel lists each one from
`funnel.json::undecided_detail` with the missing field and the value it would need to reach the
limit. The fetch line names the document series (`space`), so an IFIC number alone cannot be
mistaken for the terrestrial series. The "Show calculation" block carries the formula, the limit
source and the input keys, so a reader can recompute the number.

Tests (`tests/test_api.py`, 16): the page, the fetch status and its lock, the `runs/latest` pointer,
the funnel numbers, every card, one card and its 404, the queue order, and the 503/504 error paths.
The tests that read content take it from one real pipeline run into a temporary `out/` (a private
copy per test, so one may corrupt its files); the index, health and error paths need no challenge
data.

## F11: the optional Teams digest

`scripts/notify.py` turns the files of the last run into one Teams message per IFIC. It reads
`out/funnel.json` and `out/cases.json`, imports nothing from `app/` (its stage rank table is a copy
of `app/config.REGULATORY_STAGES`, marked `shortcut` in the code), and computes nothing: the counts
are the ones in `funnel.json` and the three lines are the first three decidable rows of `queue.md`,
ordered by class, then stage, then margin, then case id. `--dry-run` writes `out/teams_message.md`
and `out/teams_message.json` (the Adaptive Card envelope) and, with `--html`,
`out/teams_message.html`; `--send` POSTs the card to `TEAMS_WEBHOOK_URL` and returns 1 with one line
on stderr when the variable is unset. A run whose queue is empty gets the single line `Käsitelty, ei
uusia huomioitavia tapauksia.`

This is a wish, not a requirement: no bot, no chat surface, no cron, and no live Teams send (there
was no test channel). The README section "Teams notification (optional)" carries the commands and
the limits.

Tests (`tests/test_notify.py`, 6): `test_message_carries_numbers_and_link` (the funnel numbers, the
queue size, the link, the Finnish decimal comma), `test_top_three_is_queue_order_not_margin`,
`test_zero_cases_gets_the_short_message` (the empty message in both the text and the card),
`test_dry_run_writes_markdown_json_and_html`, `test_send_without_webhook_fails_cleanly` (exit 1, no
traceback) and `test_send_posts_the_card_to_the_webhook` (a stubbed `urlopen`: the URL, the content
type, the card type). No test opens a connection.

## Data we read and did not use

`app/ingest.py` reads 17 IFIC tables. Each was checked against the seven space bands and the
Finnish side, and the ones that reach no gate are recorded here as measured negative results rather
than left as gaps nobody noticed. Every count below was read from IFIC 3074 on 7 Nov 2026. The
Resolution 35 table `grp_res35` used to be one of them; it now feeds the queue order and the card
(see F5 and F6).

`c_pfd` (119 rows; `ntc_id, seq_no, freq_min, freq_max, pfd, bdwdth, ra_stn_type`) is the
notifier's own PFD limit. Measured on IFIC 3074, the four frequency ranges it covers are
1 164–1 215, 4 990–5 000, 5 030–5 150 and 42 500–43 500 MHz, and zero rows cover 3 000–4 400 MHz, so
not one of the seven space bands has a notifier PFD limit to compare against. The limit therefore
stays ITU RR Art. 21 Table 21-4 (decision D4).

`srv_area` (930 rows; `grp_id, ctry, f_excl_api`) is the service area a group claims. The
`f_excl_api` flag is `Y` once, `N` 125 times and empty on the other 804 rows, and `FIN` appears
twice, both with an empty flag. A flag that is blank on almost every row, and on both Finnish ones,
cannot decide whether Finland sits inside a beam, so it is not used as a relevance filter. Beam
geometry is carried by `s_beam`, and the Finnish victim side comes from the register.

`srv_cls` (60 529 rows; `grp_id, seq_no, stn_cls, nat_srv`) holds the class of station and the
nature of service per group. `stn_cls` is dominated by `EC` 25 871, `EK` 12 391, `ER` 8 199,
`EI` 4 852 and `ED` 4 428, over roughly 30 codes in total. Checked against the ITU BR IFIC Preface
(WRS-22, reference Table 3): the `stn_cls` code is the class of station (data item C4a), and the
legend pairs each space-station class with an earth-station class (`T*`/`U*`) — a code-to-code
table, not a service name. `nat_srv` is a separate code set (nature of service, data item C4b).
M4's `Services_in_Finland` is not drawn from either: it names the services in the Finnish
allocation table (`FIXED`, `MOBILE AND FIXED`). No key and no shared vocabulary connects the two,
so a join would be a guess rather than a mapping. Not implemented; the M4 lookup answers only the
downlink question of D17 and nothing else.
(decision I10).

`s_beam.pwr_max_4k` and `s_beam.pwr_avg_4k` carry a beam's peak and average power. The database has
321 beams in all, but none of the 128 beams on the 3 400–4 200 MHz band holds a value, so the same
limit as `c_pfd` applies: there is no reference power on our band and a cross-check is not possible.

`coord_agree_ntw` has 0 rows. There are no coordination agreements in this issue. When there are,
they say whether an agreement already exists for a network, which a specialist would want.

`res49_sel` has 0 rows: the Resolution 49 selections are missing from this issue.

`hist_notice` has 0 rows: there is no notice history in this issue.

`e_stn` with `es_ctry` lists 12 earth stations: RUS 6, KAZ 2, GRC 2, USA 1, KOR 1. None is in
Finland. A network with a station in Finland would be decisive relevance information; in this issue
the answer is negative, and that is worth stating.

`epfd_param` (35 rows) is the RR Art. 22 data for protecting Finnish satellites. No computation path
is implemented, so the rows are read and dropped.

`ntc_lnk` (43 rows, 12 of which concern one of our 20 case notices) links a filing to the notice it
follows. `load_ific()` reads it into `IficData.links` (a row without a target is skipped; its
`ntf_rsn` only repeats the filing's own `notice.ntf_rsn`, so the link carries `lnkntf_rsn`), and
`build_card()` carries it as `filing_follows`, one entry per link. `render_card_md()` writes "This
filing follows <ntc_id> (<reason>)"; the reason is the linked notice's nature (`N` notification,
`C` coordination request, `A` advance publication, `U` Resolution 49 -- in IFIC 3074 each code pairs
one-to-one with `notice.prov`, so `app/config.py::NTF_REASONS` uses the stage labels).

`notice.act_code` is the action the filing takes on the record: A new, M modified, S suppressed
(117 / 77 / 2 in IFIC 3074). It is carried to the card as `filing_action` and to `queue.md` as its
own `action` column; the web UI spells the three codes out on the queue row.

`s_beam.gain` is the one column here that is used. `app/gates.py::_beam_gain()` takes the peak gain
of the beams that cover the notified band, so the beam gain in every PFD is the notice's own peak
gain and not a worst-case assumption. The column is filled on 2 299 of 2 304 rows and `pattern_id`
on 721 beams; a beam without a gain value puts its notice in `missing` as `no_gain` instead of
computing from a guess.

### AP30 plan data is not in the biweekly IFIC

The ITU distributes the AP30 plan data apart from the biweekly BR IFIC: `SPS_ALL_IFIC3083.zip` is
72 MB and unpacks to a 387 MB Access database that `mdb-export` reads. Measured on that database:
1 770 notices, 4 of them Finnish (`adm = FIN`), 100550080, 100550081, 100550722 and 100550723.
100550080 is FIN10300 and 100550081 is FIN10400, both at 22.8°E (±0.1°), plan types `00DN`
(downlink, AP30B) and `00UP` (uplink): downlink 12 116.76–12 489 MHz and 12 385.28–12 489 MHz
(27 MHz), uplink 17 716.76–18 089 MHz and 17 985.28–18 089 MHz, beam `E001`, circular polarisation,
4 `beam_tr` rows. `30B_3083.zip` (22 MB) was not opened.

Traficom pointed to ITU SpaceExplorer (filter: notifying administration Finland, GEO only), which
needs a TIES account we do not have; the same data was already on disk. IFIC 3074 has no notifier
within ±1.0° of 22.8°E on 10.7–18.2 GHz, so the Finnish plan positions change nothing in this run.
SpaceExplorer would also show Finland's Art. 11 notices and MIFR entries, not only plan allocations;
we protect terrestrial stations, so those are not needed here, and protecting Finnish satellites
would be RR Art. 22 (EPFD), a separate calculation.

## Next steps

Not built, in rough order of value. The estimate is effort, not a schedule.

| Step | What it would take | Estimate |
|---|---|---|
| Scheduled cadence | The monitor is built (`scripts/monitor.py`) and the issue number is no longer given by hand, but nothing is installed: the cadence needs one line in whatever scheduler the operator already runs | Small |
| Stage-first queue order | Sort the whole queue by regulatory stage before class; the customer said stage is the only priority that matters after filtering. The card keeps the margin as information | Small |
| Space-side trends | The customer's first next step. Needs a second space IFIC issue; the terrestrial side already has trends | Medium, blocked on data |
| M15 cross-check | The brief lists it; the tool does not use it | Medium |
| CEPT/ECC DocDB | The third tier of the protection framework; not used | Medium |
| AP30 / AP30A / AP30B | The customer ranked this below space-side trends. Open `SPS_ALL_IFIC3083.zip` (72 MB) and `30B_3083.zip` (22 MB) with `mdb-export` and build a plan path | Large |
| RR Art. 22 / EPFD | A calculation and a criterion for protecting Finnish satellites; `epfd_param` is already read | Large |

Register scale, measured 7 Nov 2026 with `load_register()` alone on a synthetic register (1 M rows,
65 MB on disk, every 1000th row on the demo slice):

| Register rows | Time | Peak memory |
|---|---|---|
| 1 000 000 | 3.2 s | 19 MB |

The same file through the old whole-file read took 8.0 s and 1 154 MB, because `rows()` built a
list of every row before the first `Station`. `load_register()` now streams the file with
`iter_rows()` and keeps only the stations whose channel touches one of the run's bands, so the
memory is the kept stations, not the file. The register has 874 rows covering 872 station numbers;
three rows carry no frequency, so 871 stations load, and only 84 of them sit on the seven space
bands (7 on the demo slice). The run passes its bands to `load_register()`, so the other rows are
never built: the funnel is unchanged (196 → 41 → 21 → 20 + 1) and `run.log` reports
`register_rows=7` for the slice. A real dataset of "tens of millions of rows" by the sample's own
cover note now costs time, not memory.

## Tooling: fetching and converting the data

`scripts/fetch_data.py` downloads the IFIC 3074 zip, the terrestrial BR IFIC 3075 and 3076 zips and
the M4 table, unpacks the `.mdb` database from each zip, and converts the frequencies-of-interest
xlsx to CSV by finding the `Station number` header row and skipping the Finnish header row behind it.
The reading of the databases happens at run time in `app/ingest.py` and `app/terrestrial.py` through
`mdb-export`. The script prints a SHA256 for every file and refuses a response that is not a zip
(`check_zip`), which is how a WAF challenge page gets caught.

Tests (`tests/test_fetch_data.py`, 2): `test_html_instead_of_zip_is_rejected`,
`test_xlsx_rows_skips_preamble_and_finnish_header`.

## Test data

There are no committed data fixtures. The tests that need a real input are marked `data` and read
`data/itu-ific-3074/ific3074.mdb`, `data/frequencies_of_interest.csv`, `data/taajuusjakotaulukko.json`
and the two terrestrial BR IFIC MDBs; `tests/conftest.py` skips every one of them when
`data/itu-ific-3074/ific3074.mdb` is missing, so a clean clone runs green (131 passed, 48 skipped).
The pure tests carry their own inputs in the test: the unit forms in `tests/test_ingest.py`, the band
merging in `tests/test_bands.py`, the guard rows in `tests/test_gates.py`, the PFD vectors and the
limit table in `tests/test_pfd.py`.
