# Traficom Q&A, 7 Nov 2026

The challenge's Q&A point ran 9.00–12.00 and 14.30–18.00. The full question list and the answer form
live in `~/hackathon-prep/KYSY-TRAFICOM.md`; this file is the repository's memory of what was asked,
what was answered and what each answer changed. Questions are in English because the brief and the
data are English. The respondent is named where the answer came from a person rather than a source.

## Answered in the Discord thread

### Q1. Register nature and the broadcasting coverage area

> We treat the delivered Excel table (Frequencies of interest, 874 stations) as the list of Finnish
> stations to be protected. So we check satellite downlinks (space-to-Earth) against each station's
> RX frequency and location. Is that correct?
> For broadcasting rows (Class of licence BC and BT), TX and RX frequency are the same. Should we
> protect only the transmitter site, or the whole coverage area around it?

**Answer.** The satellite downlink is the interferer. The protected side is Finnish use: the
register's RX frequencies, and TX frequencies where RX is not separately marked. The general rule is
that every TX is received in Finland. For BC/BT the row is a transmitter, so the whole coverage area
around it is protected.

**What changed.** No code change. `app/ingest.py` already reads RX first and TX as the fallback
(`Station.centre_mhz`). The coverage area is not in the data, so the PFD at the transmitter's site is
its upper bound; the beam is assumed to point at the station. Recorded in `docs/decisions.md` D3 and
`docs/features.md` F5.

### Q2. Protection criterion: Table 21-4, CEPT or national

> As the protection criterion we use the power flux-density (PFD) limits for space stations in RR
> Article 21, Table 21-4. Example: 3 400–4 200 MHz, GSO, −152 dB(W/m²) in 4 kHz at 0–5° elevation.
> You said that exceeding the defined limit is a concern. Is Table 21-4 the defined limit for the
> stations in the table, or is there another one (a national limit, or I/N)? If another, which value
> and source?

**Answer.** Table 21-4 is the internationally agreed limit and the primary source. CEPT may elaborate
the European "concern" thresholds. National limits are not relevant here.

**What changed.** No change to the limit. Table 21-4 stays the PFD limit. The −3 dB `near` class is
a screening convention, not a CEPT threshold. The card now prints the exact Table 21-4 row (A, K,
reference bandwidth, page) and a criterion line that says CEPT/ECC is not applied. Recorded in
`docs/decisions.md` D4 and D19.

### Q3. Beam geometry and the worst-case assumption

> In the free IFIC 3074 database the beam table (`s_beam`) has no boresight coordinates and no beam
> axes, so we cannot tell where a satellite beam points. We therefore assume the worst case: the
> beam's peak gain is aimed at the Finnish station. This gives an upper bound, not a prediction, and
> can over-flag cases. Is this acceptable for screening? Or can you provide the beam data (GIMS
> graphical data) for the relevant notices?

**Answer.** Beams are not relevant to the analysis; the worst case is always assumed. Satellites
move, rotate and can change their pointing, except GSO.

**What changed.** The calculation did not change; the worst case was already the premise. The card
and the letter did: since 7 Nov 2026 the card states the assumption on a `Coverage` line and drops
the beam fields from `Missing`, while the letter states it in its first paragraph; both ask the
administration to confirm the worst-case PFD instead of asking about the service area
(`app/cards.py`, `templates/correspondence_fi_en.md`). GIMS data is not needed.

### Q4. Terrestrial field strength: border line or the register's stations

> For the terrestrial land-mobile side quest we calculate the field strength from each foreign
> station with ITU-R P.1546 and compare it with the ECC T/R 25-08 trigger field strengths. Where
> should we calculate it: at points on the Finnish border or coastline, or at the station locations
> in your Excel table? If at the border, which points matter most?

**Answer.** At points on the border line, not at four cities. Pay attention to the points closest to
the foreign transmitters and to the border sections where the field strength can be highest. Cover
the relevant border sections, not one representative point. Also mark the Finnish stations in the
Excel table whose field strength exceeds the coordination threshold.

**What changed.** Code change: the four test points became the border polylines in
`rules/finland_border.csv` (land borders plus the territorial sea outer limit; see the follow-up
answers below), the nearest point to each transmitter and the highest-field-strength border section
are reported, and the register's stations are flagged against the threshold. Recorded in
`docs/decisions.md` T2 and T5 and in `docs/features.md` F6.

### Q5. Output format

> The brief says the processed results for IFIC 3074 and 3076 must be submitted as separate files,
> but does not define the format. Our plan: one CSV per IFIC with one row per notice (notice ID,
> administration, frequency, result class, PFD or field strength, margin, reason), plus the case
> cards as JSON. Is that fine, or do you expect another format, for example the same MDB format as
> the IFIC? Which fields are mandatory?

**Answer.** xls/csv or doc/pdf is the primary format; JSON is preferred over MDB; any
machine-readable open format is fine. The mandatory fields were not answered.

**What changed.** No change: one CSV per IFIC plus `cases.json` stays. The mandatory-field question
is open (Q8 below).

### Q6. Showing data in the demo video

> May we show rows of the delivered Excel table and an unfinished prototype in the demo video?

**Answer.** Yes.

**What changed.** The demo may show the real table rows and the unfinished prototype. Recorded in
`docs/demo.md`.

### Q7. T/R 25-08 above 470 MHz

> T/R 25-08 ends at 470 MHz and 81 % of the 3076 land-mobile rows are above that. What criterion do
> you use there?

**Answer.** For frequencies above 470 MHz, apply the same criteria as T/R 25-08 defines for the range
above 400 MHz.

**What changed.** Code: `rules/tr2508_thresholds.csv` gained the row 470–10 000 MHz at 20 dBµV/m, and
`tr2508_threshold()` now returns a value for the >470 MHz notices instead of `None`. The docs'
"not confirmed" text for the ECC tier was replaced with the confirmed values. Recorded in
`docs/decisions.md` T5.

## Also answered in the Discord thread

**Bandwidth.** If `Channel bandwidth` and `Transmission bandwidth` disagree, use the smaller. Station
440557 has 2 500 kHz against 118 600 kHz, a typo in the data generation. For BC stations, 9 or 10 kHz
is fine. Code: `app/ingest.py` uses `Channel bandwidth` and keeps `Transmission bandwidth` as the
fallback; the fix is `min()`.

**"Concern".** Exceeding the defined limit is always a concern. A near-limit or "semi-high" PFD near
the frequency may also be one; this matches the `near` class (−3 dB) and also means an adjacent band.
The threshold falls if the Finnish station has a high antenna gain pointed at the transmitter's
location, so the register's `Ant gain` and `Radiation direction` fields matter. IFIC 3074 and 3076
contain "several cases which are foundable clearly"; the ground-truth question was dropped because the
cases are the evaluation set.

**AP30 plan positions.** Otto Julkunen pointed to ITU SpaceExplorer (filter Finland, GEO only). The
data is already local: `SPS_ALL_IFIC3083.zip` → 387 MB MDB, four Finnish notices (`100550080`,
`100550081`, `100550722`, `100550723`), two at 22.8°E. The free 3074 zip has empty AP30B tables; the
plan data is separate. SpaceExplorer needs a TIES account or SNS subscription, which we do not have.

## Follow-up answers (second round, 7 Nov 2026)

### F1. Which T/R 25-08 criterion above 470 MHz

> Above 470 MHz you said to apply the same criteria as T/R 25-08 defines for the range above 400 MHz.
> T/R 25-08 has more than one table in that range. Which one should we use for the land-mobile
> records? And should the time percentage be 10 % or 1 % for digital systems?

**Answer.** For this challenge, use the general land-mobile threshold in T/R 25-08 A.1.2.3. The time
percentage is A1.2.3's 10 % (the answer did not restate it, but A1.2.3 is the named criterion).

**What changed.** The A1.2.3 reading is confirmed; `rules/tr2508_thresholds.csv` already carries the
20 dBµV/m row above 470 MHz. The 400 MHz range's NB/WB and LTE/LTE tables (20/55/37 dBµV/m) are not
used. The P.1546 table stays 50 % time, so the note in the output about a flagged station being a
definite exceedance while a low value proves nothing remains true.

### F2. Which border sections count

> You asked us to cover the border sections where the field strength can be highest. Which border
> sections: the land border with Sweden, Norway and Russia, the sea border, or also Åland?

**Answer.** Along the Finnish land borders as well as along the outer limit of Finland's territorial
sea. The Åland question is answered by the territorial sea outer limit, which surrounds Åland.

**What changed.** Code change: `rules/finland_border.csv` now holds the land borders (SE, NO, RU) and
the 12 nautical mile territorial sea outer limit (TS) from Marine Regions. The coastline is dropped.
`border_line()` returns polylines split on section, `border_samples()` samples each, and
`distance_to_border_km()` takes the minimum over all of them. The border maximum for POL 92817506
(801–806 MHz) moved from −51.1 to −46.9 dBµV/m, and its strongest section is now TS. Recorded in
`docs/decisions.md` T2 and `docs/features.md` F6.

### F3. Fixed (FX) records

> The 3076 records above 470 MHz include 2 166 fixed (FX) records as well as 999 FB and 870 ML. Does
> T/R 25-08 apply to the fixed records too, or only to the land-mobile classes? If fixed records are
> outside T/R 25-08, what criterion should we use?

**Answer.** The side quest is limited to land-mobile only.

**What changed.** No code change: `LAND_MOBILE_CLASSES = {FB, ML, FL}` already filters FX out. The
2 166 FX records are dropped by the class filter, not by the threshold.

### F4. Which threshold for the register's stations, and the class of licence

> Which threshold should we compare against: T/R 25-08 land-mobile or national M4? The register's rows
> are Class of licence BC, MVV and empty; T/R 25-08 is for land-mobile stations.

**Answer.** T/R 25-08 threshold. The ITU-R BR IFIC terrestrial preface defines the station classes in
the land mobile service; the register's Class of licence is not needed.

**What changed.** No code change: `flag_stations()` compares against `tr2508_threshold()`, not the
national M4 value. The register's Class of licence is not used to pick the threshold; it only labels
the row.

### F5. What counts as a concern, and how wide the analysis goes

> We screen each notice's space-to-Earth rows against the Finnish register's stations and Table
> 21-4. Is a PFD below the limit enough to clear a filing, and how far beyond the delivered Excel
> list should the analysis reach?

**Answer (Otto Julkunen, 7 Nov 2026, relayed by the team).** A PFD above the limit is not enough on
its own. If a frequency is, in Finland, one that does not relate to satellite use, and some
satellite transmits on it, that is a problem they want to act on. The delivered Excel list is only a
reference, and the analysis must consider more widely than the areas on that list. Not all use is
known, and the authorities do not want to disclose all of it. Exceedance at the level of Finnish
territory is the most important thing. The delivered data is particularly interesting. Location is
secondary; the frequency band is what matters.

**What changed.** The baseline moved from the register to the allocation table and from the
register's stations to Finnish territory: G1 takes its bands from the Finnish allocation (D18),
not from the register, G3 takes the PFD at the edge of the territory
(`rules/finland_border.csv`, `app/territory.py`) and keeps the register's row as a `Reference` line,
and a new M4 finding makes a band with no satellite service a class of its own
(`not_space`, queued even when the margin is clear; `app/allocation.py`). The scope was widened to
every Finnish allocation and every satellite direction on the same day (D18). Recorded in
`docs/decisions.md` D17 and I10. The demo slice 3,47-3,78 GHz is `MOBILE AND FIXED` in Finland, so
every demo case now carries at least the frequency finding.

## Follow-up answers (third round, 7 Nov 2026)

Five scope questions were put to the specialists at the stand after the usability test. The
respondent is not recorded. The answers are quoted as given, in Finnish.

### S1. What to prioritise after filtering

**Answer.** "Tekniikka ratkaisee. Marginaali ei ole niin merkityksellinen, jos se ylittyy. Nykyisin
he käyvät läpi kaikki. Filteröinnin jälkeinen priorisointi ei ole enää tärkeä. Eli tämän palvelun
tuotokset eivät ole enää niin tärkeitä. Vaiheen priorisointi on tärkein filteröinnin jälkeen."

**What changed.** The product is a filter, not a ranking. Once a notice passes the filter, the
expert reviews all of them; the size of the margin does not change the action. The one ordering
that matters is the regulatory stage: a filing another administration can still influence comes
before one already recorded in the MIFR. Applied 7 Nov 2026 (D18): the queue orders by stage, then
class, then the Resolution 35 deadline, and the margin does not order.

### S2. False positive or false negative

**Answer.** A false negative is worse.

**What changed.** The worst-case upper bound and the broad `near` class stay. This is now a
recorded design decision: over-flagging is the accepted cost of not missing a concern.

### S3. Automatic retrieval scope

**Answer.** Both are acceptable: automatic retrieval for both series, or the space monitor plus a
terrestrial batch run.

**What changed.** No code change. The current split (space monitored, terrestrial run from two
consecutive issues) is an accepted scope, not a gap.

### S4. AP30 or space-side trends

**Answer.** Space-side trends.

**What changed.** Space-side trends are the next step; AP30 stays deliberately out of scope. This
belongs in the submission's next steps, not in the code before the freeze.

### S5. Required fields on an output row

**Answer.** An IFIC reference and a reference to our own data (a single unique entity), a unique
identity pointing to the source material, the combination that identifies the problem being
solved: frequency, bandwidth, the interferer's frequency and bandwidth, the calculation result,
and the justification.

**What changed.** Done. Each row of `<ific>_results.csv` now opens with the IFIC tag, the
`case_id` (our own data, `<ific>-<ntc_id>`) and the notice id, and carries the interferer's band
(`freq_min_mhz`, `freq_max_mhz`) and its `bandwidth_mhz`, the protected station and its
`victim_rx_mhz`, the PFD, the limit, the margin, the limit source and the BR IFIC publication part
(`publication`). A dropped notice keeps its IFIC tag and notice id with the stage, the publication
part and the reason, and leaves `case_id` empty because it has no card.

## Open

- No open questions from the Q&A. The mandatory-field question is answered in S5. The `Class of
  licence` question is not needed: the side quest reads the station class from the BR IFIC
  terrestrial preface.

## Follow-up answers (fourth round, 7 Nov 2026)

### S6. Tracking what was complained about, and how it ended

**Answer.** "Tilastointi olisi tärkeää. Pitäisi saada tietää, mistä asioista on valitettu ja kenen
toiminnasta on valitettu, vaikka viiden vuoden kuluttua: mitä on tehty ja mihin on puututtu."

**What changed.** New: an append-only complaint register (`app/ledger.py`) and a statistics view
(`app/stats.py`, section "Complaint register" in the UI). A complaint is opened by the pipeline for
every case it would write a letter for, and a human records the rest: the letter, the reply, the
action, the closing outcome. The three questions are answered from those events: what (band, Finnish
allocation, issue type), whose operation (administration, network, operator) and what was done
(action, outcome, days from letter to reply). The card lists the earlier complaints for that
administration and network, with the reply note the register holds. Nothing is deleted or rewritten,
so the answer for 2021 is the same in 2031.

The history from 2021 to 2026 in the demo is synthetic and labelled: it is seeded from
`scripts/seed_history.py --seed 2026`, every line carries `synthetic: true`, the network names are
invented, and the UI says so in its banner. The real rows come from the pipeline runs. Decision R1 in
`docs/decisions.md` has the reasons and the limits (a file, not a database; a production deployment
would move the same event model to SQLite or Postgres with a retention period).
