# Decision log

Every significant choice behind this repository: the technology, the scope, the assumptions, and the
reasons. Each entry states the choice, what else was on the table, why this one won, and what new
information would reopen it.

Part 1 holds the product decisions from the plan (task 0). They were made in the planning role
without asking the user, as the plan's own instruction required, and are repeated here because a
reader of the repository cannot follow the code without them. Part 2 holds the decisions that
appeared while the code was written, each one greppable in the source. Part 3 holds the decisions of
this documentation pass. Part 4 lists the published work the design answers, with a source for every
claim. The last section holds the optional Teams digest, decided on 7 Nov 2026.

## Part 1: product and scope

### D1. Product: a deterministic IFIC triage, not a chatbot and not a map

Choice: read one IFIC package, screen its space-to-Earth notices against the run's bands and the
Finnish allocation, compute the upper-bound PFD at the Finnish territory edge, produce a card per
notice and a queue of the cases that need a human decision. A human decides.

Alternatives: a retrieval chatbot over the filings, a map layer, a full coordination calculation, a
plain band filter.

Reason: the challenge asks for analysis, an artefact and a human decision. A band filter alone
passes every notice that merely touches the run's bands, which is not a filter. A chatbot produces
no number to audit. A map earns nothing in either rubric. A full coordination calculation needs beam
geometry that IFIC 3074 does not carry.

Reopen if: Traficom says they already screen the filings themselves (then the value is comparing
results), or that the input is documents rather than structured tables.

### D2. Demo slice 3.47 to 3.78 GHz, engine runs all seven bands

Choice: the demo locks the 3.47 to 3.78 GHz slice; `--all` runs the seven space allocations into the
accuracy file.

Reason: the slice is the only group where the register also carries the fields the calculation
needs. The full scope is the seven space bands and its queue is 65 rows, which does not fit a
three-minute demo. Both numbers are in the README.

Reopen if: Traficom supplies calculation parameters for the other bands.

### D3. Direction: downlink

Choice: `emi_rcp = E`, space transmits and Finland receives. Uplink is a configuration, not a demo.

Reason: the challenge's own example is a satellite that disturbs terrestrial use in Finland, and the
register carries the RX frequency and the antenna direction. The RX frequency is the receiver's
frequency; TX is the fallback when RX is not separately noted. For BC/BT the row is the
transmitter, so the whole coverage area around it is protected; the PFD at the transmitter's site
is the upper bound for that area, because the beam is assumed to point at Finland. Since D17 the
number is taken at the edge of Finnish territory, not at the station's site.

Reopen if: Traficom answers that their register is a transmitter register. The engine is the same;
only the filter and the receiver side change.

### D4. Level: ITU RR Article 21 Table 21-4, not `c_pfd`, not I/N

Choice: a 13-row limit table in `rules/rr21_table21_4.csv` covering GSO, non-GSO and HEO, per Hz.

Reason: `c_pfd` covers four frequency ranges and none of the seven space bands. An I/N criterion
needs a receiver noise figure and a bandwidth that the register does not carry. Table 21-4 is public,
citable and a function of elevation. Traficom confirmed Table 21-4 as the internationally agreed
limit and the primary source; CEPT may elaborate the European concern thresholds, and the −3 dB
`near` class is a screening convention rather than a CEPT threshold. National limits exist for some
bands but are not relevant to this challenge.

Reopen if: Traficom names a protection criterion, gives receiver parameters, or shows that the upper
bound produces too many false flags.

### D5. Queue without a cap, not padded, everything in the files

Choice: inside a regulatory stage, order `exceeds`, `near`, `not_space`, `cannot_decide`; the stage
orders first (I17); leave `clear` cases out of the queue; keep every notice in `cases.json` and
`3074_results.csv`.

Reason: the written challenge brief names no target number, and the task is to find the problems and
report them rather than shorten the list. The queue holds every case that needs a human decision,
and the files keep the accuracy record. A short queue is not padded with invented cases.

Reopen if: Traficom names a target queue size.

### D6. AI writes prose, code decides

Choice: the language model may write the card summary, the letter and a trend sentence. It may not
select rows, compute the PFD, order the queue or state a verdict. A numeric guard checks every
number in the text.

Reason: 40 % of the Traficom rubric rests on determinism and auditability. A generative AI
hackathon expects the model to be used for something, and prose is the honest place. IFIC carries no
free text, so extraction is not the model's job either.

Reopen if: Traficom says the model may decide. That is unlikely.

### D7. Terrestrial side feature reads the real BR IFIC MDBs

Choice: `app/terrestrial.py` reads two real BR IFIC terrestrial databases (3075 and 3076) with
`mdb-export`, takes each notice's change from `fxm_terra.intent` (ADD → new, MODIFY → modified,
SUPPRESS → withdrawn, RECORDED → the stock), keeps land-mobile notices within 1 000 km of Finland
that overlap the register, and computes ITU-R P.1546-6 field strength. 3075 is the trend baseline.
No synthetic extract is used anywhere.

Reason: the IFIC is not a cumulative database (3075 and 3076 share no `terrakey`), so the change is
the `intent` field, not a key comparison. The 3076 package is a public ITU download
(`brific3076.zip`), so the tool reads the real file directly; the repository holds no synthetic
extract. The side feature is 25 % of the Traficom rubric.

Reopen if: a newer IFIC changes the `fxm_terra` schema, in which case `load_issue_mdb` needs the new
columns.

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

Choice: "Kaista" (band), tagline "From 95,865 frequency rows to every case that needs a human decision."

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

Reopened: that condition was met. The core was finished and green on Friday 6 Nov 2026 at 23.42, so
the OpenShift AI part was built. Granite 3.3 2B Instruct is served by KServe and the vLLM CPU
runtime in the sandbox project `janner-1-dev`, and the prose step ran against it: the guard kept five
drafts and rejected twelve. That measurement predates the list-marker fix in
I11, and a re-measurement after the fix did not get through the app's 120 s client timeout while the
sandbox node also ran the data-science pipeline. LUMI stays out, because an archive run needs data
we do not have. The measured evidence is in `deploy/openshift/README.md`, and the plan behind the
part is D17 in the prep repository.

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

### D17. Baseline: the Finnish allocation and the territory edge, not the register's stations (7 Nov 2026)

Choice: the run's bands come from the space scope in `app/config.py`, the PFD is taken at the edge
of Finnish territory, and a band with no space-to-Earth satellite service in Finland is a class of
its own (`not_space`).

Reason: Traficom's answer of 7 Nov 2026 (`docs/traficom-qa.md` F5) moved the criterion. A PFD
above Table 21-4 is not enough on its own: if a frequency is, in Finland, one that does not relate
to satellite use and a satellite transmits on it, that is a problem they want to act on. The
delivered Excel list is only a reference, and the analysis has to reach beyond the areas it lists,
because not all use is known or disclosed. Exceedance at the level of Finnish territory is the most
important thing; the frequency band is what matters and the location is secondary.

What it changed:

- G1 (`app/gates.py::gate1`) matches a notice against the run's scope bands, not against the bands
  the register happens to declare. A notice whose band nobody listed is now screened: 113 notices
  pass G1 in `--all` mode where 101 did before, and 41 in the demo slice where 41 did (two more of
  those reach G2, both inside the register's 13,1 MHz hole).
- G3 takes the worst case at the edge of Finnish territory (`rules/finland_border.csv`: the land
  borders with Sweden, Norway and Russia plus the territorial sea outer limit,
  `app/territory.py`). The worst case over an area lies on its edge: the slant range grows away from
  the sub-satellite point and the Table 21-4 limit does not rise faster, so the vertices are enough
  and no polygon or grid is needed. The register's rows stay on the card as a `Reference` line.
- `app/allocation.py` reads the Finnish allocation table (M4) and answers one question: does the
  band carry a satellite service with the space-to-Earth direction? An uplink-only or an
  inter-satellite row does not. A band that fails is class `not_space`, queued even when its margin
  is clear. `clear` now means that both the margin and the allocation are unremarkable. The demo
  slice is 3,47-3,78 GHz, which in Finland is `MOBILE AND FIXED`: every demo case carries at least
  the frequency finding.

Alternatives: keep the register as the gate and add a separate "possible use" report (rejected: the
queue would still hide the filings the customer wants to act on); sample a territorial grid or a
polygon (rejected: the edge is exact for a monotone worst case and needs no new data); treat any
allocation row as satellite use regardless of direction (rejected: an Earth-to-space allocation
does not license a downlink).

Cost: `--all` takes about 20 s instead of 4 s, because every GSO notice is evaluated at 552 edge
points instead of a handful of stations. The demo slice stays at about 4 s.

Test: `tests/test_gates.py::test_a_clear_margin_on_a_non_satellite_band_is_still_a_finding`,
`tests/test_cards.py::test_m4_lookup_names_the_service_and_the_downlink`,
`tests/test_pipeline.py::test_the_register_is_only_a_reference`.

Reopen if: Traficom says the register's station set should bound the analysis again, or supplies the
declared service areas; then the territory edge can be replaced by the real footprint.

## Part 2: decisions taken while writing the code

Each one is visible in the source, and the tests named here would fail if it changed.

### I1. Units: understand a bare `G`, and take the smaller of the two bandwidth columns

`app/ingest.py`, `mhz()` and `load_register()`. The register keeps two bandwidth columns. For the
same station `Transmission bandwidth` holds shorthand such as `0,1G`, while `Channel bandwidth`
spells it out as `0.1 GHz`; `mhz()` reads a bare `G` as GHz, so `0,1G` and `0.1 GHz` both come to
100 MHz, and a shorthand such as `8M00` parses to nothing. When the two columns disagree, Traficom
answers that the smaller one is what the register means, the larger being a data-entry artefact
(their example: station 440557, `Channel bandwidth` 2 500 kHz against `Transmission bandwidth`
118 600 kHz), so `load_register()` takes `min(Channel bandwidth, Transmission bandwidth)` and falls
back to whichever column carries a value. No row of the challenge register disagrees, so no number
moves. The consequence of the unit reading for the full run is 101 notices surviving G1, 75 visible
and 11 undecidable, one more than the plan's 100/74/10, because the reference tool behind the plan
read the cell `0,1G` as 0.1 MHz. The demo slice matches the plan exactly.

Test that locks it: `tests/test_ingest.py::test_bandwidth_is_the_smaller_of_channel_and_transmission`,
plus `test_mhz_normalises_units` and `tests/test_gates.py::test_all_bands_funnel`.

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
20 MHz, so about ten channels tie for the same worst case with the same power, gain and geometry.
The card shows 3 442–3 478 MHz where the plan's vector says 3 662–3 698 MHz. Every number in the
vector matches; only the label differs, and it is whichever channel comes first in the file.

Test: `tests/test_cards.py::test_golden_case_103500417`.

### I4. Non-GSO worst case is a pass sweep, not an orbit

`app/gates.py`, `_worst_for_notice()`, marked `shortcut` in the code. The pass is sampled from
perigee in 0.1° steps up to 90°, and the victim's own position does not change the geometry because
a non-GSO pass sweeps every latitude. Without an ephemeris this is the defensible upper bound; with
one, the sampling should be replaced.

Tests: `tests/test_gates.py::test_vector_2_from_the_real_data`,
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

### I8. Bandwidth is the smaller of the two register columns

`app/ingest.py::load_register()`. `Channel bandwidth` is the raster the station sits in,
`Transmission bandwidth` what it actually emits. Where they disagree the smaller one wins (Traficom,
7 Nov 2026); a missing one falls back to the other, and both empty gives 0, which makes the band a
point instead of crashing.

Tests: `tests/test_ingest.py::test_bandwidth_is_the_smaller_of_channel_and_transmission`,
`tests/test_bands.py::test_zero_bandwidth_is_a_point_not_a_crash`.

### I9. An earth-station notice is dropped in G1 with its own reason

`app/gates.py::gate1()`. A notice with `ntc_type = S` that sends `emi_rcp = E` is the station
transmitting, not a downlink, so it leaves with reason `earth_station_notice` rather than
`no_band_overlap`. One notice in the full run takes this path. The distinction matters when reading
the drop counts.

Tests: `tests/test_gates.py::test_a_notice_type_s_sending_E_is_dropped` and the
`earth_station_notice` assertion in `tests/test_gates.py::test_all_bands_funnel`.

### I10. M4 is a finding, not only context

`app/allocation.py::m4_lookup()`. The Finnish allocation is looked up per notified band, shown on
the card, and it decides one class: a band with no space-to-Earth satellite service is `not_space`,
queued even when the PFD is clear (D17). A band without an allocation row gets
`services_in_finland: "not allocated"` and the same finding.

Test: `tests/test_cards.py::test_m4_lookup_names_the_service_and_the_downlink`.

### I11. The guard compares signed values

`app/guard.py::check()`. Signs count: a margin written as `-60,44` against a card margin of
`+60,44` says the opposite and is rejected. A minus right after a digit is a range separator
(`3 662-3 698`), not a sign. Comparison is on values within 0.01, and Finnish thousands separators
are joined before scanning, so `3 662` is one number.

This replaced an earlier absolute-value comparison, which let a flipped sign through.

A list marker is not a number. Digits that open a list, `1. Vastaus` at a line start or a `2.` after
a space, are removed before scanning, so a numbered answer is not rejected for its own numbering. A
period and a space are what make the marker: a date (`3.1.2026`), a decimal (`3,24 dB`) and an id
(`3074-103500417`) keep their digits. A number that ends a sentence before a line break reads as a
marker too; the guard is a floor, not a proof.

Tests: `tests/test_guard.py` (all nine).

### I12. The card summary, and a letter for every case above the limit

`app/pipeline.py` calls `prose.draft_summary()` per card and stores it under `prose`.
`app/cards.py::write_outputs()` then writes `out/letters/<case_id>.md` for every `exceeds` case,
through `prose.draft_letter()`, and records the count in `run.log`. Earlier the letters were not
written at all: "Writing 18 letters per run would add files nobody asked for." The written brief's
workflow ends with "drafting relevant correspondence template for expert review", so the letter is
part of the deliverable; it is kept to the cases above the limit rather than all cards, so `near`,
`clear` and `cannot_decide` cases get no letter. The directory is regenerated each run, so a letter
from an earlier mode cannot outlive the cases of this run.

Tests: `tests/test_prose.py::test_letter_template_asks_the_question`, `test_a_clean_llm_answer_is_kept`;
`tests/test_pipeline.py::test_letters_are_written_for_the_exceeds_cards` (mini) and the data test
`test_real_run_writes_a_letter_for_every_exceeds_case` (9 letters, none for the 4 clear cases).

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
slice that is notice 126590032 (`no_power`): 20 cards from the 21 notices that reach G3. The row,
the reason and the count stay in the files, so the audit
trail is whole, but the notice has no card in the web UI. Stated as README limitation 14; a card for
it would be an owner decision, not a silent gap.

Test: `tests/test_gates.py::test_case_126590032_cannot_be_decided` locks the notice and its reason.

### I16. A blank LLM answer is not prose; the template is the floor

`app/prose.py::_ask()`. An answer that is empty or whitespace is treated as a failure, so the card
gets `prose.source = "template"` instead of an empty sentence. A refusal or an answer in the wrong
language is still not detected: the guard checks numbers, not intent, so the fallback only catches
what the endpoint fails to produce. The gap is stated in README limitation 7 and
`docs/features.md` F8.

Tests: `tests/test_prose.py::test_an_empty_llm_answer_falls_back`.

### I17. The queue reads the regulatory stage from `notice.prov`

`app/config.py::REGULATORY_STAGES` and `app/gates.py::gate4()`. The BR IFIC carries the stage of a
filing in `notice.prov`: `9.1/IA` (advance publication, ITU RR 2024 No. 9.1), `9.6` (coordination
request, No. 9.6), `11.2` (notification, No. 11.2) and `RS49` (Resolution 49). In IFIC 3074 the
counts are 50 / 76 / 65 / 5. The card shows the stage as `{provision, label, source}`. The stage is a
property of the notice, not a deadline: no window length is computed or guessed, and `label` is one
sentence of what the stage means.

The queue order (revised 7 Nov 2026 after Traficom's S1 answer): `queue_key()` sorts the whole queue
by stage rank, then class, then the Resolution 35 deadline (I21), then the notice id. The margin is
not in the key. An advance publication or coordination request, where another administration can
still influence the filing, comes before a filing already recorded in the MIFR, whatever the class
or margin of either. The specialists review every case the filter passes; the size of the margin
does not change their action, the stage does.

Alternatives: class first, then stage, then margin (the earlier order, rejected by S1: it put an
11.2 exceedance at +21 dB ahead of a 9.6 `near` case the administration can still act on); keep the
margin as the last tie-break (rejected: S1 says it does not order, and the notice id is a stable
tie-break that implies no priority).

Tests: `tests/test_cards.py::test_prov_distribution_and_the_card_stage` (data) locks the 50 / 76 / 65
/ 5 distribution and the card block;
`tests/test_gates.py::test_queue_puts_coordination_before_notification` (every 9.1/9.6 row before
the first 11.2 row), `test_stage_beats_a_bigger_margin` (a `near` 9.x case ahead of an 11.2
exceedance at +99 dB), `tests/test_api.py::test_queue_is_ordered_by_stage_first` and
`tests/test_notify.py::test_top_three_is_stage_first_not_margin` lock the same order in the API and
the digest.

### I18. The adjacent-channel guard is one constant, off by default

`app/gates.py::gate1()` with `app/config.py::GUARD_MHZ = 0.0`. Traficom's Discord answer (7 Nov
2026) says a close-by exceedance or a semi-high PFD near the frequency can also be a concern, but
the current G1 needs a real band overlap, so such a notice never reaches a card. Rather than widen
the gate now, the spacing is one constant: `0.0` leaves G1 exactly as it was and keeps the run
comparable with the plan and the vectors, and raising it is a one-line change once Traficom confirms
a threshold. A notice that then enters only through the guard is marked `adjacent: true` and its
class is capped at `near`, because the Table 21-4 limit is a property of the notified band and does
not apply outside it. The deliberate default is 0.0; the number stays unset until it is confirmed.

Tests: `tests/test_gates.py::test_guard_mhz_zero_is_the_plain_overlap` (the default changes nothing),
`test_guard_mhz_lets_an_adjacent_notice_through` (a 5 MHz guard brings the in-hole notice in),
`test_an_adjacent_case_is_capped_at_near` (the cap, with the margin unchanged).

### I19. The directive-antenna note states a possibility, not a number

`app/cards.py::_threshold_note()` with `app/config.py::DIRECTIVE_GAIN_DB = 20.0`. Traficom says the
trigger level can fall when a Finnish station has a large antenna gain aimed at the transmitter. The
register carries a per-station gain and a directivity code, so the card adds one sentence when the
victim is directive (`victim.directivity` not `ND`) and its gain is at or above 20 dBi. It changes
no number and no class, and it does not compare the registration's azimuth with the direction of the
satellite: the register has an azimuth but no beam width, so a direction-to-source claim would be a
guess rather than a measurement (README limitation 16).

Test: `tests/test_cards.py::test_directive_antenna_gets_a_threshold_note`.

### I20. The space funnel reads the BR IFIC MDB directly

`app/ingest.py::load_ific()`. The 17 tables are read straight from the Access database with
`mdb-export <mdb> <table>` (subprocess, no shell), so there is no intermediate CSV directory and no
synthetic extract anywhere in the repository. `--ific` takes the `.mdb` path
(`data/itu-ific-3074/ific3074.mdb`); `scripts/fetch_data.py` only downloads and unpacks the zip. A
missing `mdb-export`, an unreadable table or a missing file raises `DataError` naming the input.
Provenance is the database itself: every card's `source` carries the file name, the IFIC number and
the file's SHA256, and `run.log` carries the same plus `source_file`. The exported bytes are
identical to the CSV files the earlier version read, so every number is unchanged; the demo slice
run goes from about 1.3 s to about 3.5 s, which is under the point where a cache would earn its
keep.

Tests that lock it: `tests/test_ingest.py::test_real_mdb_row_counts` and
`test_real_register_and_mdb_hash` (data), plus the unit mapping test
`test_exported_rows_are_mapped_to_ific_data` and the error paths
`test_missing_mdb_is_a_clear_error`, `test_missing_mdb_export_is_a_clear_error` and
`test_unreadable_table_is_a_clear_error`.

### I21. The queue's Res 35 deadline is the notice's earliest upcoming group deadline

`app/ingest.py::deadline()` with `IficData.res35`, `app/gates.py::notice_deadlines()` and
`queue_key()`, `app/cards.py::deadline_lines()`. `grp_res35` carries a Resolution 35 deadline per
group (`grp_id` -> `d_ms_next_deadline`), and a notice has many groups: the 254 rows of IFIC 3074
belong to three notices only, 125500277, 126500053 and 325500168. The chain `freq.ntc_id` ->
`freq.grp_id` -> `grp_res35.grp_id` was read and thrown away, so a filing with a bring-into-use
deadline read like any other in the queue (the gap was listed in `docs/features.md`).

Choice: a notice's deadline is the earliest date still upcoming over all of its groups, else the
latest date that has already passed; the queue orders by stage rank, then class, then that
deadline (soonest upcoming first, a passed one behind every upcoming one, a notice with no deadline
last), then the notice id (I17; the margin left the key on 7 Nov 2026). The card carries `deadline` (Finnish `d.m.yyyy`) and `deadline_passed`, and
`render_card_md()` writes `- **Resolution 35 deadline:** <date>`, appending `(passed)` for one
already gone. The classes, the margins and every other number do not change: in the demo slice one
row (125500277, due 19 Dec 2026) moves ahead of a larger margin in its stage, and its card gains one
line.

Alternatives: the case's own `grp_id` only (rejected: the worst-case group of a notice is not
necessarily the group that falls due, so the deadline of 125500277 would be missed, since its case
picked a group without one); sorting by the raw date even when it is past (rejected: a 2019
deadline would outrank a 2026 one); hiding a passed deadline (rejected: a missed deadline is a
finding, not noise). The reference date is the run's own instant (`gates.run(today=...)`, the same
moment as `run_at`), so the run stays deterministic and the data tests pass a fixed date.

Reopen if: the ITU says the deadline attaches to a frequency assignment rather than to the network's
bring-into-use round, or Traficom wants the group's own deadline on the card rather than the
notice's earliest.

Tests: `tests/test_ingest.py::test_deadline_reads_the_exported_date`;
`tests/test_gates.py::test_notice_deadlines_pick_the_earliest_upcoming` (synthetic: earliest
upcoming, latest passed, a group with no deadline),
`test_queue_orders_by_stage_then_deadline` (synthetic: upcoming ascending, then passed,
then none) and `test_only_one_demo_case_carries_a_res35_deadline` (data: 125500277 ahead of a larger
margin in its stage); `tests/test_cards.py::test_deadline_line_marks_a_passed_deadline` and
`test_queue_md_carries_a_deadline_column` (synthetic) and
`test_the_demo_card_shows_its_res35_deadline` (data).

Known limit: the order lives in four places (`gate4`, `app/main.py::queue`,
`scripts/notify.py::top_cases` and `app/static/index.html`'s `queueKey`). All four carry the same
stage, class, deadline key since 7 Nov 2026; the copies exist because `notify.py` stays stdlib-only
and the page sorts what the API sends. `out/queue.md` is the queue of record. A new key changes
four files, and the committed screenshot shows the old order until it is retaken.

### T1. The P.1546 table is generated once and committed

`rules/p1546_land.csv`. Generated with the ITU reference implementation (eeveetza/Py1546, commit
e235629) at the nominal distances of the recommendation, for a 1 kW ERP reference, at 100, 600 and
2000 MHz and antenna heights from 10 to 1200 m. The runtime interpolates linearly and adds
`10*log10(p_erp_kw)`; it needs no numpy and no network. The model is the land path at 50 % of time
and 50 % of locations without terrain, receiving antenna 10 m, which is what the side feature
documents in its own output.

Test: `tests/test_terrestrial.py::test_field_strength_matches_p1546_table_node`.

### T2. Distance to Finland is the nearest point on the border line

`app/terrestrial.py::distance_to_border_km()`. The border polylines in `rules/finland_border.csv`
serve as the field strength sample locations, so the filter and the report use one definition.
The border is the land borders with Sweden (SE), Norway (NO) and Russia (RU) plus the outer limit of
the territorial sea (TS, the 12 nautical mile line from Marine Regions); the coastline is not a
border. Traficom asked for the nearest points to the foreign transmitters and the border sections
with the highest field strength, so the border line is not optional.

Test: `tests/test_terrestrial.py::test_filter_keeps_land_mobile_in_reach`.

### T3. Register overlap counts RX and TX

`app/terrestrial.py::register_frequencies()`. A channel is a pair, RX 464.04 MHz with TX
454.04 MHz on the same licence, so a notice band that touches either side counts as overlapping.
The register columns are read as strings with their own unit suffix (`454.040 MHz`), unlike the
space path, because the frequencies-of-interest file uses that form.

Test: `tests/test_terrestrial.py::test_register_counts_both_rx_and_tx_directions`.

### T4. Field strength is evaluated at the band centre

`app/terrestrial.py::findings()`. One value per notice per test point, at the centre frequency of
the notified band. Sweeping the band would multiply the output without changing the screening
question.

Test: covered by `tests/test_terrestrial.py::test_run_writes_three_outputs` and the fixture output.

### T5. The protection threshold follows T/R 25-08 A1.2.3

`app/terrestrial.py`, `tr2508_threshold()` reads `rules/tr2508_thresholds.csv`: 0/6/12/18/20
dBµV/m by band on a 25 kHz reference, and the same 20 dBµV/m above 470 MHz per Traficom 7.11.2026.
The threshold is applied per notice and the margin is reported. `CRITERION` still names the three
tiers a field-strength limit would come from: ITU RR Art. 21 Table 21-4 (PFD, the level the space
path already applies) → CEPT/ECC T/R 25-08 (the field strength that triggers protection) → the
national M4 / Traficomin taajuusjakotaulukko (the Finnish protection threshold). The ECC values are
confirmed; the national value is not. A guessed threshold would turn a report into a false verdict,
so the national tier stays named and unused.

Test: `tests/test_terrestrial.py::test_findings_applies_the_tr2508_threshold` (the criterion names
the confirmed values), `test_tr2508_threshold_is_frequency_dependent_and_bandwidth_corrected` (the
>470 MHz row), `test_run_writes_three_outputs` (the framework line lands in `TERRESTRIAL.md`).

### T6. The terrestrial filter keeps the land-mobile station classes

`app/terrestrial.py`, `LAND_MOBILE_CLASSES = frozenset({"FB", "ML", "FL"})`. In the BR IFIC station
class code, `FB` is a base station, `ML` a land mobile station and `FL` a land mobile station
(fixed); the 3076 file uses exactly these three. Everything else, `FX` included, is counted under
`class` in the drop tally so the filtering is auditable.

Test: `tests/test_terrestrial.py::test_filter_keeps_land_mobile_in_reach`.

### T7. An anomaly means a group with nothing before and at least three now

`app/terrestrial.py::anomalies()`. A new group of one or two notices is normal churn; three at once
in a group that was empty is worth a look. The limit is a parameter and the output lists the rows
rather than a count.

Test: the 3076 run reports the SVN 1770-1775 MHz group (49 new), visible in `docs/demo.md`.

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

## Part 4: prior art

This part exists because the design was not invented from nothing. Four published sources cover the
same ground, and each one either confirmed a choice or changed one. None is a dependency, none is
cited in code, and the repository does not need any of them to run.

### P1. A spectrum regulator's own paper names the two blockers, and both are answered

Choice: the model writes prose only. Code computes every number, a guard rejects any sentence that
carries a number the card does not hold, and the class and the letter are the specialist's call.

Alternatives: let the model select which notices matter; let it summarise a row into a number; skip
the model entirely and ship templates.

Reason: the closest published work comes from the Canadian spectrum regulator's own research arm.
Ghasemi and Guinand are at the Communications Research Centre (CRC) Canada in Ottawa, and the paper's
contact addresses are @ised-isde.gc.ca, the department that runs spectrum regulation there. They put
LLMs through spectrum regulation workflows. Section
III-B, "Inaccuracy", says the output can appear "credible but being factually wrong (so-called
hallucination)" and that this "could misinform policies or public communication". Section III-C,
"Automation Bias", says that when it is relied on too much, "automatically generated outputs are
preferred even when faced with contradictory evidence suggesting other manually-derived outputs might
be better". Section II-D3 argues for human oversight on the same grounds. Source: *Accelerating Radio
Spectrum Regulation Workflows with Large Language Models*, arXiv:2403.17819, full text at
https://arxiv.org/html/2403.17819v1 (abstract: https://arxiv.org/abs/2403.17819). A tool that let a
model decide would import both problems into a decision with legal consequences. Skipping the model
would have left the letter and the card text to a template, which is what happens anyway when
`LLM_BASE_URL` is unset: the template is the floor, not the fallback nobody tested.

What it changed: it is the reason the guard exists as a rejection rule rather than a warning, and the
reason the guard's rejections are counted in the run instead of logged quietly.

Reopen if: Traficom states that a model may rank or decide. That is unlikely, and it would still need
the guard.

### P2. The abstention class comes from selective prediction, not from convenience

Choice: `cannot_decide` is a first-class outcome. It keeps a row in the queue, it keeps a row in
`3074_results.csv`, and it carries the reason the calculation stopped (`no_power`, `no_gain`,
`no_limit_for_band`, `x_needs_nv`, `no_perigee`).

Alternatives: drop what cannot be computed; assume a default beam gain; let the model guess a value
from the notice text.

Reason: a classifier that refuses to answer is measured in the selective classification literature by
two numbers, and both are defined there: "Coverage" (the share of inputs it answered) and "Selective
Risk" (the error rate on the part it did answer), with the trade-off between them as the objective
(Heng and Soh, *Know When to Abstain: Optimal Selective Classification with Likelihood Ratios*,
arXiv:2505.15008, section III, https://arxiv.org/html/2505.15008v3). That pair fits
this tool better than a single accuracy figure, because the tool has no labelled ground truth and
will not have one before the submission. `funnel.json` therefore reports the coverage and the
abstention reason codes instead of an accuracy number, and the queue ordering puts the abstentions
where a specialist sees them rather than at the bottom. Assuming a default gain would have moved a
number into a card that no source supports, and a model guessing a PSD from prose would have been
the exact failure mode the numeric guard exists to stop.

What it changed: nothing in the code. It gave the class its name and its metric, and it is the reason
the abstention count is reported next to the class counts rather than hidden in a log line.

Reopen if: Traficom supplies a labelled set of decisions. Then coverage can be replaced by real
recall on the two classes that matter.

### P3. The gates read everything, so recall is structural, not estimated

Choice: every notice passes all gates, and every drop is recorded with a stage and a reason in
`3074_results.csv`. The queue is not a sample and has no cap.

Alternatives: score and rank notices, review the top N, and estimate the recall of that sample.

Reason: the neighbouring field solved this problem first. Technology-assisted review in e-discovery
screens a large document set down to a small relevant subset. Grossman and Cormack compared a process
that combined human judgment with automated ranking against exhaustive manual review, and report the
result "as measured by recall, precision, and F1" (*Technology-Assisted Review in E-Discovery Can Be
More Effective and More Efficient Than Exhaustive Manual Review*, Richmond Journal of Law and
Technology 17(3), Article 11, 2011,
https://grossman.uwaterloo.ca/grossman-publications/jolt-2011/). The next sentence is our reading,
not theirs: a process judged on those three numbers over a sample is defensible by its statistics,
whereas a full read is defensible by its construction. A sample-based method would have been cheaper to
build and impossible to defend here: 196 notices take 3.4 seconds to read in full, so there is no
reason to sample, and a ranked top N would have hidden the `cannot_decide` notices, which are the
ones a specialist most needs to see. Reading everything makes the recall of the gates 1 by
construction and leaves uncertainty only in the class that declares it.

What it changed: the queue keeps every exceeds, near, not_space and cannot_decide row, and the CSV
keeps the rest, so no number in this repository is an estimate of what the filter might have missed.

Reopen if: an IFIC grows past the point where a full read fits the run budget, or Traficom names a
target size for the queue.

### P4. Reproducibility is the acceptance test the ITU already uses

Choice: each run writes the input SHA256, the rules version and the run timestamp, and the
calculation is pinned by a fixed test vector (`docs/features.md`, the COMPASS-80E case).

Alternatives: state the method and trust the reader; ship a UI screenshot as the evidence.

Reason: EPFD examination under Article 22 of the Radio Regulations is done by software, not by hand.
Rec. ITU-R S.1503 describes that software, and the Radiocommunication Bureau required at least two
independent implementations of it before relying on the result. The Bureau's page states it directly:
"in order to increase the confidence in any software tool, the Bureau felt that at least two
independent implementations of Recommendation ITU-R S.1503 would be necessary", and names the two
commercial tools, EPFD-A and EPFD-T (https://www.itu.int/epfdsupport/, Resolution 85 (Rev. WRC-23),
Rec. ITU-R S.1503-2). The same standard, applied to a much smaller calculation, is a hash of the
input, a version of the rules, and one case whose numbers are written out by hand and checked in the
tests. Two implementations, the same answer, without asking anyone to trust the program.

What it changed: `run.log` carries `input_sha256` and `rules_version`, and the limits live in
`rules/rr21_table21_4.csv` rather than in code, so a second reader can recompute a card by hand.

Reopen if: a second implementation of this funnel appears, which would let the two be compared the way
the Bureau compares EPFD tools.

### Sources for part 4

Every claim above is checkable at one of these four places. Accessed 7 Nov 2026.

1. A. Ghasemi and P. Guinand, *Accelerating Radio Spectrum Regulation Workflows with Large Language
   Models (LLMs)*, arXiv:2403.17819, sections II-D3, III-B, III-C. Full text
   https://arxiv.org/html/2403.17819v1, abstract https://arxiv.org/abs/2403.17819
2. A. Heng and H. Soh, *Know When to Abstain: Optimal Selective Classification with Likelihood
   Ratios*, arXiv:2505.15008, section III (Coverage and Selective Risk). Full text
   https://arxiv.org/html/2505.15008v3, abstract https://arxiv.org/abs/2505.15008
3. M. R. Grossman and G. V. Cormack, *Technology-Assisted Review in E-Discovery Can Be More Effective
   and More Efficient Than Exhaustive Manual Review*, Richmond Journal of Law and Technology 17(3),
   Article 11, 2011. https://grossman.uwaterloo.ca/grossman-publications/jolt-2011/
4. International Telecommunication Union, EPFD examination support, Resolution 85 (Rev. WRC-23) and
   Rec. ITU-R S.1503-2, including the statement about two independent implementations.
   https://www.itu.int/epfdsupport/

## The optional Teams digest

### N1. One webhook message per IFIC, not a bot (7 Nov 2026)

Choice: `scripts/notify.py` builds one deterministic message per run from `out/funnel.json` and
`out/cases.json`, and either writes it (`--dry-run`) or POSTs it to a Teams incoming webhook
(`--send`, `TEAMS_WEBHOOK_URL`). No bot, no chat, no Graph, no app registration, no cron.

Alternatives: a Teams bot that answers questions in a channel, a scheduled digest, an email, or
nothing at all.

Reason: the product is a deterministic triage whose output is a file, and the digest is a delivery
convenience on top of it rather than a second surface. A bot needs an app registration, a tenant
decision, a hosted endpoint and an auth story, and it would answer in prose, which is the one place
where a number could be invented; a webhook needs one URL and holds no state. The message is built
from the files of the run, so it cannot disagree with the UI. The digest is a wish, not a
requirement: the rubric scores the triage, not the delivery, and the demo does not depend on it. The
live send stays untested because there was no test channel, and the documentation says so instead of
claiming an integration (README "Teams notification (optional)", `docs/features.md` F11).

Reopen if: a Teams test channel exists, or Traficom asks for the digest inside Teams. Verify the
live send first; a bot is worth discussing only after that.
