# Decision log

Every significant choice behind this repository: the technology, the scope, the assumptions, and the
reasons. Each entry states the choice, what else was on the table, why this one won, and what new
information would reopen it.

Part 1 holds the product decisions from the plan (task 0). They were made in the planning role
without asking the user, as the plan's own instruction required, and are repeated here because a
reader of the repository cannot follow the code without them. Part 2 holds the decisions that
appeared while the code was written, each one greppable in the source. Part 3 holds the decisions of
this documentation pass.

## Part 1: product and scope

### D1. Product: a deterministic IFIC triage, not a chatbot and not a map

Choice: read one IFIC package, derive the protected bands, compute the upper-bound PFD, produce a
card per notice and a queue of 20. A human decides.

Alternatives: a retrieval chatbot over the filings, a map layer, a full coordination calculation, a
plain band filter.

Reason: the challenge asks for analysis, an artefact and a human decision. A band filter alone
passes 124 of 196 notices, which is not a filter. A chatbot produces no number to audit. A map earns
nothing in either rubric. A full coordination calculation needs beam geometry that IFIC 3074 does
not carry.

Reopen if: Traficom says they already screen the filings themselves (then the value is comparing
results), or that the input is documents rather than structured tables.

### D2. Demo slice 3.47 to 3.78 GHz, engine runs all seven bands

Choice: the demo locks the 3.47 to 3.78 GHz slice; `--all` runs the seven space allocations into the
accuracy file.

Reason: the slice is the only group where the register also carries the fields the calculation
needs. The full set is 84 rows and 26 bands, and its queue overflows 20, which does not fit a
three-minute demo. Both numbers are in the README.

Reopen if: Traficom supplies calculation parameters for the other bands.

### D3. Direction: downlink

Choice: `emi_rcp = E`, space transmits and Finland receives. Uplink is a configuration, not a demo.

Reason: the challenge's own example is a satellite that disturbs terrestrial use in Finland, and the
register carries the RX frequency and the antenna direction.

Reopen if: Traficom answers that their register is a transmitter register. The engine is the same;
only the filter and the receiver side change.

### D4. Level: ITU RR Article 21 Table 21-4, not `c_pfd`, not I/N

Choice: a 13-row limit table in `rules/rr21_table21_4.csv` covering GSO, non-GSO and HEO, per Hz.

Reason: `c_pfd` covers four frequency ranges and none of the seven space bands. An I/N criterion
needs a receiver noise figure and a bandwidth that the register does not carry. Table 21-4 is public,
citable and a function of elevation.

Reopen if: Traficom names a protection criterion, gives receiver parameters, or shows that the upper
bound produces too many false flags.

### D5. Queue of 20, not padded, everything in the files

Choice: order `exceeds`, `near`, `cannot_decide`, `clear`; cap 20; report `overflow` and the
`coverage gap`; `cases.json` and `3074_results.csv` keep every notice.

Reason: 20 comes from the spoken brief rather than a written one. The cap keeps the queue readable
while the files keep the accuracy record. A short queue is not padded with invented cases.

Reopen if: the Q&A session names another target. The cap is configuration (`QUEUE_CAP`).

### D6. AI writes prose, code decides

Choice: the language model may write the card summary, the letter and a trend sentence. It may not
select rows, compute the PFD, order the queue or state a verdict. A numeric guard checks every
number in the text.

Reason: 40 % of the Traficom rubric rests on determinism and auditability. A generative AI
hackathon expects the model to be used for something, and prose is the honest place. IFIC carries no
free text, so extraction is not the model's job either.

Reopen if: Traficom says the model may decide. That is unlikely.

### D7. Terrestrial side feature: synthetic fixture, no claim about 3076

Choice: two synthetic land-mobile extracts, ITU-R P.1546-6 field strength, a diff and trends, every
output marked `synthetic: true`. A real 3076 extract would be run with the same command.

Reason: the 3076 download was blocked on 6 Nov 2026 and no extract exists. The side feature is 25 %
of the Traficom rubric. A marked synthetic fixture is honest; an unmarked one is not.

Reopen if: Traficom hands over a 3076 extract, in which case the converter has to be written first
(see limitation 8 in the README).

### D8. UI: one page, three panels, no map

Choice: FastAPI plus one static HTML page showing the funnel, the queue and the card. No map, no
login, no database.

Reason: the rubric rewards a working flow and a readable output. A map earns nothing in either
rubric and costs demo time.

Reopen if: time is left after everything else, which is unlikely.

### D9. Data stays out of the repository

Choice: `data/` is gitignored; `scripts/fetch_data.py` downloads the IFIC package and the M4 table
and converts the register xlsx; the deterministic run itself is offline (only the optional LLM
prose step, when `LLM_BASE_URL` is set, opens a connection).

Reason: the IFIC zip is 60.5 MB and its database 274 MB, against a 100 MB source zip limit, and
redistributing the Traficom register is not allowed. An offline demo is also safer on stage than
ITU's web application firewall.

Reopen if: the data can be published in a smaller form.

### D10. Stack: Python, FastAPI, standard library

Choice: Python 3.11 or newer, FastAPI, uvicorn, openpyxl, pytest, ruff. No pandas, no numpy, no
JavaScript build step.

Reason: 95 865 rows fit in memory, the calculation is a few lines of arithmetic per row, and the
repository was already Python. A large dependency costs installation time and adds risk on demo
morning.

Reopen if: the P.1546 work needs numpy, or the UI needs a chart library. Both would be looked at
separately.

### D11. P.1546: an own table, because the package is not installable

Choice: a committed table (`rules/p1546_land.csv`) with own interpolation, no `py1546` package.

Reason: `py1546` was not on PyPI on 6 Nov 2026 and the ITU site refused command-line downloads. The
table is generated once, outside the runtime, from the ITU reference implementation, and the
interpolation is standard library. The fallback in the plan, a side feature without a numeric field
strength, was not needed.

Reopen if: the table is replaced with a finer grid or a maintained package.

### D12. Name: Kaista

Choice: "Kaista" (band), tagline "From 95,865 frequency rows to 20 cases a human can decide."

Reason: short, Finnish, describes the band and the product, and stands apart from a generic "IFIC
triage".

Reopen if: the owner wants another name. The name is not in the code beyond strings and the page
title.

### D13. What is deliberately not built

Choice: no map, no retrieval chatbot, no AP30 analysis, no real-time monitoring, no cron, no
deployment.

Reason: each one takes time from the core and earns nothing in the rubric. AP30 data rows are zero;
a retrieval chatbot produces no number; real-time monitoring is a different product.

Reopen if: the core is done with more than six hours to spare. Unlikely.

### D14. OpenShift AI and LUMI are P2

Choice: both are optional, with a Saturday 20:00 cutoff. The local run is the primary demo.

Reason: the Red Hat award is 1 000 € and distinctive, but it does not replace a missing core. The
sandbox expires after 30 days, so it cannot be the only demo link.

Reopen if: the core and the side feature are finished before Saturday evening.

### D15. No recall claim

Choice: report the funnel numbers and the share of `cannot_decide`; an evaluation set with own
labels only if there is time, and then labelled as own labels rather than Traficom ground truth.

Reason: without ground truth a recall figure is circular. What Traficom needs is a file they can
compare against their own judgement, not an invented accuracy number.

Reopen if: Traficom gives three to five cases whose outcome they already know.

### D16. `same_network` shows, and does not merge

Choice: list the other notices with the same satellite and administration, or a notified target, and
decide each notice on its own.

Reason: `ntwk_org` is empty on 189 of 196 notices. Merging could hide a notice Traficom expects, and
`103500417` with `303500417` are the same satellite in different `st_cur` states.

Reopen if: Traficom wants results at network level.

## Part 2: decisions taken while writing the code

Each one is visible in the source, and the tests named here would fail if it changed.

### I1. Units: read the `Channel bandwidth` column first, and understand a bare `G`

`app/ingest.py`, `mhz()` and `load_register()`. The register keeps two bandwidth columns. For the
same station `Transmission bandwidth` holds shorthand such as `0,1G`, while `Channel bandwidth`
spells it out as `0.1 GHz`; `mhz()` reads a bare `G` as GHz, so `0,1G` and `0.1 GHz` both come to
100 MHz, and a shorthand such as `8M00` parses to nothing. `load_register()` therefore reads
`Channel bandwidth` first, the raster the station sits in, and falls back to `Transmission
bandwidth` when the channel column is empty. The consequence for the full run is 101 notices
surviving G1, 75 visible and 11 undecidable, one more than the plan's 100/74/10, because the
reference tool behind the plan read the cell `0,1G` as 0.1 MHz. The demo slice matches the plan
exactly.

Test that locks it: `tests/test_gates.py::test_all_bands_funnel`, plus the parametrised
`tests/test_ingest.py::test_mhz_normalises_units`.

### I2. Touching channels form one band, and the gap stays visible

`app/bands.py`, `MERGE_GAP_MHZ = 0.0`. Two channels merge when they overlap or touch, and nothing
is joined across a hole. The plan's "below 100 MHz" tolerance would have merged separate regions
into 17 bands; touching plus the corrected unit parsing yields the plan's 26. In the demo slice the
result is two bands (3 470,5–3 663,7 MHz and 3 676,8–3 776,8 MHz) with a visible 13.1 MHz gap
between them, which the tool shows rather than covers.

Tests: `tests/test_bands.py::test_derive_bands_merges_touching_channels_but_not_the_hole`,
`test_channels_that_touch_become_one_band`.

### I3. The card's band label is the first matching row in file order

`app/gates.py`, `_worst_for_notice()`. The CDN beam repeats an identical 36 MHz channel every
20 MHz, so about ten channels tie for the same worst case with the same power, gain, station and
elevation. The card shows 3 642–3 678 MHz where the plan's vector says 3 662–3 698 MHz. Every number
in the vector matches; only the label differs, and it is whichever channel comes first in the file.

Test: `tests/test_cards.py::test_golden_case_103500417`.

### I4. Non-GSO worst case is a pass sweep, not an orbit

`app/gates.py`, `_worst_for_notice()`, marked `shortcut` in the code. The pass is sampled from
perigee in 0.1° steps up to 90°, and the victim's own position does not change the geometry because
a non-GSO pass sweeps every latitude. Without an ephemeris this is the defensible upper bound; with
one, the sampling should be replaced.

Tests: `tests/test_gates.py::test_mini_non_gso_case_uses_the_pass_sweep`,
`tests/test_pfd.py::test_ngso_reach`.

### I5. `near` is open on the right, and classification uses the rounded margin

`app/gates.py::classify()` with `EXCEEDS_DB = 0.0` and `NEAR_DB = -3.0`: a margin of exactly
0,00 dB is `near`, because `exceeds` needs a margin above zero, and a margin of exactly −3,00 dB is
`clear`. The margin is rounded to two decimals before classification, as in the reference
calculation.

Test: `tests/test_gates.py::test_class_boundaries`.

### I6. HEO without its own table row falls back to the NGSO row

`app/pfd.py::limit_row()`. The table has no separate HEO row for every band, so a HEO notice uses
the non-GSO row when the band has one. The alternative, `cannot_decide`, would lose cases that the
regulation does cover.

Test: `tests/test_pfd.py::test_heo_uses_the_ngso_row_when_there_is_no_heo_row`.

### I7. A limit row must contain the whole notified band

`app/pfd.py::limit_row()` returns `None` unless one row covers the band end to end. A band that
straddles two rows, or sits outside the table, becomes `cannot_decide` with `no_limit_for_band`
rather than borrowing a neighbour's limit. A wrong limit would be worse than no answer.

Tests: `tests/test_pfd.py::test_limit_row_needs_a_row_that_contains_the_whole_band`,
`tests/test_pfd.py::test_every_limit_row_is_continuous_at_25_degrees`.

### I8. Bandwidth comes from the channel, not the emission

`app/ingest.py::load_register()`. `Channel bandwidth` is the raster the station sits in,
`Transmission bandwidth` what it actually emits. The channel is used first, the emission as the
fallback, and 0 when both are empty, which makes the band a point instead of crashing.

Test: `tests/test_bands.py::test_zero_bandwidth_is_a_point_not_a_crash`.

### I9. An earth-station notice is dropped in G1 with its own reason

`app/gates.py::gate1()`. A notice with `ntc_type = S` that sends `emi_rcp = E` is the station
transmitting, not a downlink, so it leaves with reason `earth_station_notice` rather than
`no_band_overlap`. One notice in the full run takes this path. The distinction matters when reading
the drop counts.

Tests: `tests/test_gates.py::test_mini_funnel_counts_and_reasons` and the
`earth_station_notice` assertion in `tests/test_cards.py::test_results_rows_cover_every_notice`.

### I10. M4 is context, never a gate

`app/cards.py::m4_lookup()`. The Finnish allocation is looked up and shown on the card; it never
changes a class. A band without an allocation gets `services_in_finland: "not allocated"` and the
card still builds.

Test: `tests/test_cards.py::test_m4_lookup_is_context_not_a_gate`.

### I11. The guard compares signed values

`app/guard.py::check()`. Signs count: a margin written as `-60,44` against a card margin of
`+60,44` says the opposite and is rejected. A minus right after a digit is a range separator
(`3 662-3 698`), not a sign. Comparison is on values within 0.01, and Finnish thousands separators
are joined before scanning, so `3 662` is one number.

This replaced an earlier absolute-value comparison, which let a flipped sign through.

Tests: `tests/test_guard.py` (all seven).

### I12. Only the card summary is attached to a run

`app/pipeline.py` calls `prose.draft_summary()` per card and stores it under `prose`. The
correspondence letter has its own function and template, is covered by tests, and is not written to
`out/`. Writing 18 letters per run would add files nobody asked for.

Tests: `tests/test_prose.py::test_letter_template_asks_the_question`, `test_a_clean_llm_answer_is_kept`.

### I13. The API reads files and computes nothing

`app/main.py`. Every number on the page comes from `out/`, so the UI can never disagree with the
run. A missing or half-written output is answered with 503 and the command to run, because that is
an expected state rather than a bug. `KAISTA_OUT` exists so the tests can point the API at a
temporary directory. The queue endpoint builds its list from `cases.json`, and the code carries a
`shortcut` comment that `cannot_decide` notices therefore have no row there; their count is in the
funnel endpoint.

Tests: `tests/test_api.py` (all nine), in particular
`test_missing_out_is_503_and_the_page_still_loads` and `test_broken_json_is_503_not_500`.

### I14. The page writes text, not HTML

`app/static/index.html`. Values from `out/` go through `textContent` and `replaceChildren`, so a
satellite name or a case id cannot inject markup. No external request, no CDN, no build step.

Test: `tests/test_api.py::test_index_serves_the_finnish_page` covers the page contents; the
injection property rests on the code shape rather than a test.

### I15. A notice that cannot be computed gets no card

`app/pipeline.py` builds a card only for a case that reached G3 with a number. A notice that passes
G1 and G2 but lands in `undecided` keeps its row in `queue.md` and `3074_results.csv` (class
`cannot_decide`) and is counted in `funnel.json`, but has no entry in `cases.json`. In the demo
slice that is notice 126590032 (`no_power`): 18 cards from the 19 notices that reach G3, against the
19 the plan's F7/F10 expects. The row, the reason and the count stay in the files, so the audit
trail is whole, but the notice has no card in the web UI. Stated as README limitation 15; a card for
it would be an owner decision, not a silent gap.

Test: `tests/test_gates.py::test_case_126590032_cannot_be_decided` locks the notice and its reason.

### I16. A blank LLM answer is not prose; the template is the floor

`app/prose.py::_ask()`. An answer that is empty or whitespace is treated as a failure, so the card
gets `prose.source = "template"` instead of an empty sentence. A refusal or an answer in the wrong
language is still not detected: the guard checks numbers, not intent, so the fallback only catches
what the endpoint fails to produce. The gap is stated in README limitation 7 and
`docs/features.md` F8.

Tests: `tests/test_prose.py::test_an_empty_llm_answer_falls_back`.

### T1. The P.1546 table is generated once and committed

`rules/p1546_land.csv`. Generated with the ITU reference implementation (eeveetza/Py1546, commit
e235629) at the nominal distances of the recommendation, for 1 kW e.r.p., at 100, 600 and 2000 MHz
and antenna heights from 10 to 1200 m. The runtime interpolates linearly and adds
`10*log10(p_erp_kw)`; it needs no numpy and no network. The model is the land path at 50 % of time
and 50 % of locations without terrain, receiving antenna 10 m, which is what the side feature
documents in its own output.

Test: `tests/test_terrestrial.py::test_field_strength_matches_p1546_table_node`.

### T2. Distance to Finland is the nearest of four test points

`app/terrestrial.py::distance_to_finland_km()`. The same four points serve as the field strength
sample locations, so the filter and the report use one definition. A polygon border would be more
accurate and is not worth the geometry for a screening filter at 1 000 km.

Test: `tests/test_terrestrial.py::test_filter_drops_far_and_non_land_mobile`.

### T3. Register overlap counts RX and TX

`app/terrestrial.py::register_frequencies()`. A channel is a pair, RX 464.04 MHz with TX
454.04 MHz on the same licence, so a notice band that touches either side counts as overlapping.
The register columns are read as strings with their own unit suffix (`454.040 MHz`), unlike the
space path, because the frequencies-of-interest file uses that form.

Test: `tests/test_terrestrial.py::test_fixture_bands_overlap_the_real_register` (data).

### T4. Field strength is evaluated at the band centre

`app/terrestrial.py::findings()`. One value per notice per test point, at the centre frequency of
the notified band. Sweeping the band would multiply the output without changing the screening
question.

Test: covered by `tests/test_terrestrial.py::test_run_writes_three_outputs` and the fixture output.

### T5. The protection threshold stays `null`

`app/terrestrial.py`, `THRESHOLD_DBUV_M = None` with `CRITERION = "criterion to be confirmed (e.g.
ECC T/R 25-08)"`. No threshold was given for the challenge, so the tool reports field strength and
says nothing about pass or fail. A guessed threshold would turn a report into a false verdict.

Test: `tests/test_terrestrial.py::test_findings_mark_synthetic_and_leave_threshold_open`.

### T6. The terrestrial filter keeps `LM` and `MVV`

`app/terrestrial.py`, `LAND_MOBILE_CLASSES = frozenset({"LM", "MVV"})`. Land mobile and mobile,
the two classes that describe the 3076-style notices the side feature is about. Everything else is
counted under `class` in the drop tally so the filtering is auditable.

Test: `tests/test_terrestrial.py::test_filter_drops_far_and_non_land_mobile`.

### T7. An anomaly means a group with nothing before and at least three now

`app/terrestrial.py::anomalies()`. A new group of one or two notices is normal churn; three at once
in a group that was empty is worth a look. The limit is a parameter and the output lists the rows
rather than a count.

Test: the fixture run reports the SVE 800-805 MHz group, visible in `docs/demo.md`.

## Part 3: decisions of this documentation pass

### W1. Repository documentation in English, the kanban handoff in Finnish

The repository is what the competition jury reads, and the existing README and submission form are
English. The board handoff for the review card (a Finnish reader) stays Finnish. The split is
deliberate, so a later editor does not "fix" one into the other.

Reopen if: the owner wants Finnish README content for a Finnish audience.

### W2. Documentation lives in `docs/`, the README stays the entry point

`docs/features.md`, `docs/decisions.md` and `docs/demo.md`, all linked from the README. Three files
rather than one long one, because the three questions are different: what exists, why it is like
this, and how to see it working. The plan's `docs/checklist.md` became the Final check section of
`SUBMISSION.md`; a separate checklist file would duplicate both the limits section of the README and
the form's own list.

Reopened 6 Nov 2026 (F11, card `t_24772576`). Review `t_ffe3dcd3` finding R17 (P1) noted that the
repository had no architecture diagram, and the plan lists `docs/architecture.md` in F11. The file
is added after all: one page with the pipeline as a Mermaid flowchart and a table of the twelve
modules, linked from the README documentation table. The checklist stays in `SUBMISSION.md`, as
decided above.

Reopen if: the repository grows other documentation that needs an index of its own.

### W3. The known defect is documented, then fixed in the code card

`3074_results.csv` originally labelled every notice dropped at G1 or G2 as `cannot_decide` in the
`class` column. This documentation pass wrote it up as README limitation 6 rather than editing code,
because the fix belonged to a code card, not to a prose pass. That card (`t_caa3d691`) then changed
`app/cards.py::results_rows()`: a gate drop now has an empty `class`, and `cannot_decide` is kept
for a case that reached G3. The README limitation and `docs/features.md` F6 were corrected with it.

### W4. Documentation is verified by running, not by reading

Every command and number in these files was executed on 6 Nov 2026 against commit `26187c3`, with
the outputs recorded in the handoff. A number that appears in the documentation comes from a run,
not from the plan.
