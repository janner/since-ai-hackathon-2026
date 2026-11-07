# Demo video v2: the Teams hook, the feature pass, and what "yours" means

Draft for Janne's review, 7 Nov 2026. The rendered v2 cut is 1:55.4, 1920x1080, H.264/AAC
(`dist/kaista-demo-v2.mp4`). The table below uses the render's scene times and the corrected
narration; the current MP4 still has six mismatches (section "Corrections for the next render").
A second session is updating the UI from the feedback, so re-record the queue, card and register
scenes after that update; the numbers in this file stay the same.

A second session was editing `docs/demo-video.md`, `docs/features.md` and the other feature docs
during the script pass, so this proposal lives in its own file and touches none of them.

## Why v2

The v1 cut is a good two-minute story about the core funnel, but it leaves out four things the
submission now has: the optional Teams digest, the terrestrial side feature, the complaint
register, and the fact that every input is the customer's own file. It also starts on raw rows,
which is the problem, not the product.

v2 keeps the two-minute limit and changes the shape:

1. **Open on the push, not the pull.** A Teams preview card says a new package arrived and names
   the nine cases that need attention. Clicking it opens the queue. This is the specialist's wish
   from the 6 Nov briefing, and it is built as a preview.
2. **Keep the funnel and the APSTAR card.** They are the proof.
3. **Add a feature pass.** A 12-tile grid names the parts the narration cannot fit: ingest, gates,
   queue, card, letter, register, terrestrial, monitor, Teams, model, OpenShift, tests.
4. **End on personalization.** The last spoken beat lists what the customer controls: band scope,
   M4 table, register, limit table, templates, model endpoint, output directory, complaint log.
   With no model, the template is the floor.
5. **Frame the mission.** Traficom keeps Finnish radio use free of harmful interference. The worst
   case is computed on the border line, where the path is longest, not at a single point in the
   middle of the country. The card shows the point: `land border, Russia`, 63.00771 N, 31.43701 E.

The script is 263 spoken words. At 1.3 speed the voice runs about 2:00, so the next render trims
the path-loss detail (4 s) to stay under the limit. The current v2 render is 1:55.4; the next render
follows the table and the corrections below.

## The 2-minute cut

| Time | On screen | Narration (spoken and captioned) | On-screen labels |
|---|---|---|---|
| 0:00 | `docs/assets/teams-preview-3075.html`: a Teams channel card, `Kaista bot · preview`. At 0:05.5 the cursor clicks **Open Kaista** and the app fades in. | Every two weeks a new satellite package arrives. Kaista reads it and can push one message: nine need attention. | `TEAMS · one digest per IFIC` `BR IFIC 3075` `9 need attention` |
| 0:07 | The app queue after the click. | This morning it checked ITU and processed 3075: 129 notices. | `129 notices` `LAST CHECK 7 NOV · NEXT 21 NOV` |
| 0:17 | Raw rows of the 3075 package, slow scroll; the header carries the row count. | BR IFIC 3075: one hundred and twenty-nine notices. A specialist reads them by hand. | `129 notices` `50,645 frequency rows` |
| 0:25 | The app's Funnel panel; each gate lights as it is named. | Traficom keeps Finland's radio use free of harmful interference. Kaista helps: band overlap, visibility, a power flux density upper bound against Table twenty-one, dash four, at Finland's border, and Finland's own M-four allocation. | `TRAFICOM: PROTECT FINNISH RADIO USE` `BAND OVERLAP` `VISIBLE FROM FINLAND` `PFD vs TABLE 21-4` `M4` |
| 0:31 | The funnel numbers. | Nineteen overlap, nine are visible, seven get a number, two cannot be decided. | `129 → 19 → 9 → 7 + 2` |
| 0:42 | The three queue tiers; the no-effect rows stay visible with their reasons. | Every notice keeps a row: attention, checked, no effect. | `ATTENTION` `CHECKED` `NO EFFECT` |
| 0:50 | Queue, attention tier, rows 1–5; open `3075-108501259` (fifth row). Then the card, the `Worst case at … (land border, Russia)` line, and **Show calculation**. | The A-P-star case is fifth: its filing is already in the MIFR, zero point four three decibels over the limit, on a band with no Finnish satellite allocation. The worst case is on Finland's border: forty-one thousand kilometres, one hundred and sixty-three decibels of path loss. | `STAGE FIRST: No. 9.6 → No. 11.2` `0.43 dB over` `M4: no satellite use` `BORDER: 63.00771 N, 31.43701 E` |
| 1:04 | The card's `Coverage` line, the drafted question, then the complaint register below the card. | The package has no beam geometry, so the card states the worst case: the peak gain is aimed at Finland. It lists no missing information. The tool drafts the question and can open an append-only register: what, whose operation, and what was done. | `COVERAGE: WORST CASE ASSUMED` `NO MISSING INFORMATION` `QUESTION TO CHN` `APPEND-ONLY REGISTER` |
| 1:25 | A 12-tile feature grid, then a personalization panel. Tiles highlight as the voice names them. | The same command covers terrestrial land-mobile notices: 32 in reach, six above the ECC T/R 25-08 trigger. Every input is yours: band scope, M-four table, register, limit table, templates, model endpoint, Granite on OpenShift AI in the Red Hat setup, output directory, complaint log. With no model, the template is the floor. | `TERRESTRIAL · 32 IN REACH` `6 ABOVE ECC T/R 25-08` `MONITOR · every 14 days` `YOUR BAND SCOPE` `YOUR M4` `YOUR REGISTER` `YOUR LIMITS` `YOUR TEMPLATES` `YOUR ENDPOINT` `YOUR OUTPUT` `YOUR LEDGER` `TEMPLATE FLOOR` |
| 1:43 | `out/cases.md` and `out/3074_results.csv`; then the end card. | The accuracy package, IFIC 3074: one hundred and ninety-six notices become twenty cards and one undecidable. The specialist decides. Kaista repeats every two weeks. | `196 → 20 CARDS + 1 UNDECIDABLE` `THE SPECIALIST DECIDES` `EVERY TWO WEEKS` |
| 1:50 | End card: **Kaista** — "From 95,865 frequency rows to every case that needs a human decision." | (no voice; the card holds) | The tagline |

Word count: 19 + 10 + 14 + 33 + 13 + 9 + 46 + 43 + 52 + 24 = **263 words**. At 1.3 speed the
voice runs about 2:00, so the next render trims the `41,222 km`/`163.29 dB` path-loss detail (4 s)
to stay under the limit. The `50,645` row count is on screen, not spoken. The first trim candidate
is that path-loss detail, not the personalization beat.

## Corrections for the next render

The current MP4 is the v2 render, but six things in it do not match the current product or this
script:

1. **Queue scene, 0:42.** The MP4 shows `126590034` and `126590035` under "No effect on Finland".
   The current `runs/3075/queue.json` and `queue.md` put both under "Needs attention", rows 8 and 9.
   The page was loaded before the 20:12 queue.json update. Restart the app or refresh the page after
   the UI update and re-record the scene. This is the one visible contradiction with the About:
   `cannot_decide` is attention, not no effect.
2. **Caption, 0:17.** The raw-rows screen carries the feature-grid line "the next package every two
   weeks. Every input is" instead of the raw-rows line. Fix the caption timing. This script puts the
   raw-rows line at 0:17 and the feature-grid line at 1:25.
3. **Beam wording, 1:04.** The card says "No missing information"; the old label "MISSING: beam
   geometry" contradicts it. The script now says "The package has no beam geometry, so the card
   states the worst case. It lists no missing information." Use that.
4. **End, 1:43.** The MP4 says "20 cards"; the run has 20 cards plus one `cannot_decide`
   (`126590032`). The script now names IFIC 3074 and the undecidable.
5. **Mission line, 0:25.** The MP4 says "defend Finland's borders". Traficom's task is to keep
   Finnish radio use free of harmful interference; the border line is only where the worst case is
   computed. Re-record the narration and the label (`TRAFICOM: PROTECT FINNISH RADIO USE`).
6. **Terrestrial beat, 1:25.** The MP4 says "28 in reach, five above". The current run is 32 in
   reach, six above the ECC T/R 25-08 trigger. Re-record the narration and the two labels
   (`TERRESTRIAL · 32 IN REACH`, `6 ABOVE ECC T/R 25-08`), and change tile 07 to "same command,
   same mdb-export ingest, same source/audit/missing contract".

The MP4's scene times: 0:00 Teams, 0:07 app queue, 0:17 raw rows, 0:25 funnel, 0:31 funnel numbers,
0:42 queue tiers, 0:50 APSTAR card, 1:04 calculation/register, 1:25 feature grid, 1:43 cases, 1:50
end card. The table above uses those times; the TTS may shift them by a second or two.

A second session is updating the UI from the feedback. Re-record the queue, card and register
scenes after that update; check the card's panel labels, the queue tier headings and the register
banner. The numbers in this file do not change.

## Rubric improvements for the next render

The corrections above keep the video truthful. These additions make it score better; the first three
are the highest value.

1. **A/E, 2 seconds of provenance.** Show `out/run.log` or the card's `audit` block:
   `input_sha256=…`, `rules_version=1.1.0`. The card already shows the limit source; the input hash
   is the missing half of "reproducible". The feature-grid tile 01 says "SHA256 and keys", but a
   judge reads a tile, not a proof.
2. **D/E, 2 seconds of `3074_results.csv`.** Show the header and the first rows: one row per notice,
   196 rows, the dropped ones with `dropped_at` and `reason`. The cases.md screen shows 20 cards;
   the CSV proves that no notice is hidden. This is the accuracy artifact the brief asks for.
3. **D/E, the evaluation caveat.** Add "our own labels, not Traficom ground truth" to tile 12 or the
   narration. The tile currently says "a 21-case labelled evaluation set", which can be read as
   ground truth. The About says it; the video should too.
4. **B, the reuse wording.** Tile 07 says "same command, same mdb-export ingest, same
   source/audit/missing contract", next to the 32/6. The About says the same; the tile is the
   video's only B evidence.
5. **A/Red Hat, 2 seconds of the live call.** `dist/redhat-call-2026-11-07.png` shows
   `POST /v1/chat/completions` against Granite 3.3 2B, HTTP 200 in 7,492 ms on 7 Nov 2026, no API
   key. Show it over tile 11. The Red Hat checklist asked for this screenshot; the SUBMISSION draft
   said it was not captured, but the file exists.
6. **C, 2 seconds of the letter.** Show `out/letters/<case_id>.md` for the APSTAR case. The brief
   asks for expert-reviewable draft correspondence; the video shows the card and the question, not
   the letter. Tile 05 says "one draft per exceeds case"; the file is the proof. This is the best
   remaining C addition.

Pick the two or three that fit the 2:00 limit; the first three are the highest value. The current
cut is 1:58, so each addition needs a trim: the `41,222 km`/`163.29 dB` path-loss detail is 4 s, and
the 0:17 raw-rows narration is 5 s (the screen still shows the rows).

Do not add: a live Teams send, an interference claim, an accuracy percentage. The video already says
"can push", "upper bound" and "preview"; keep those.

## The opening mock notification

### What was discussed

At the 6 Nov briefing a second Traficom specialist said, as a wish, that they would like a
notification (perhaps a Teams bot) telling them a new ITU package has arrived and which points in
it need attention. The 7 Nov decision was: no test channel, so no live Teams send. The HTML
preview is enough for the submission; the idea is explained, not claimed as a working Teams
integration. The exact words were "Ei tarvitse mielestäni toimia oikeasti Teamsissa, kunhan väylä
on auki."

### What is built

`scripts/notify.py` turns the files of the last run into **one message per IFIC**:

- the funnel numbers;
- the three most urgent cases in queue order, not margin order;
- a link to the UI (`KAISTA_URL`);
- `--dry-run` writes `teams_message.md` and `teams_message.json` (the Adaptive Card envelope);
- `--html` adds `teams_message.html`, the standalone preview used in the video;
- `--send` POSTs to `TEAMS_WEBHOOK_URL`; it exits 1 with one line when the variable is unset.

There is no bot, no Graph, no chat surface, no cron and no LLM in the message. The live send has
not been tested because there was no test channel; the payload is covered by a stub in
`tests/test_notify.py::test_send_posts_the_card_to_the_webhook`. The video labels the card
**preview** and the narration says "can push", not "sends".

### The card for 3075

The exact card, in the same order as the built preview:

```
Kaista bot · preview
New BR IFIC 3075 — 9 cases need attention
129 notices → 19 in scope → 9 need attention
3 exceed · 4 near · 2 cannot decide

Top 3, in queue order
1. 125520114 — near, No. 9.6, −0.26 dB
2. 125520132 — near, No. 9.6, −0.25 dB
3. 125520135 — near, No. 9.6, −0.86 dB

[ Open Kaista ]   http://127.0.0.1:8020/
Preview of scripts/notify.py --html. No live Teams send; the webhook path is implemented and the
payload is covered by a stub.
```

The top three are `near` cases, not the three `exceeds` cases. That is the queue order: the four
No. 9.6 coordination cases come before the No. 11.2 MIFR cases, so APSTAR-92E is fifth. The video
explains that on the card, which turns a potential confusion into the stage-first argument.

The English mockup is `docs/assets/teams-preview-3075.html`. The built Finnish preview is
`runs/3075/teams_message.html`; the numbers and structure are the same. The English file is only
for the judges; it changes no product code. If you prefer the actual built artifact on screen,
use the Finnish file and accept that the card's labels are in Finnish while the narration is in
English; the English mockup is the cleaner choice for an international jury.

## Feature inventory: every feature and where it lands

| Feature | What it does (evidence) | In the v2 cut |
|---|---|---|
| **F0** repository, lint, CI, test base | `make check`; 192 tests collected at the current HEAD (7 Nov 2026); the data tests skip in a clean clone | Feature-grid tile `192 tests`; not spoken |
| **F1** ingest and normalisation | `app/ingest.py` reads 17 IFIC tables with `mdb-export`, keeps the source file, SHA256 and keys | Raw-row scene; spoken "reads the package" |
| **F2** the register's own bands | `app/bands.py`; the register defines the scope; `--all` screens all 299 Finnish allocations (132 need attention) | "your band scope"; feature-grid tile |
| **F3** G1 band overlap and G2 visibility | GEO sampled over the 552-point territory edge; non-GSO over a 0–90° pass; a satellite below the horizon is dropped with a reason | Funnel scene; feature-grid tile |
| **F4** PFD geometry and Table 21-4 | `PFD = psd_max + beam_gain_max − fspl(d)`; limit row by frequency, elevation and offset; the number is an upper bound, not interference | Funnel and APSTAR scenes; feature-grid tile |
| **F5** G3 worst-case PFD and G4 queue | Three tiers: `attention`, `checked`, `no_effect`; attention ordered by regulatory stage, then class, then the earliest Resolution 35 deadline; no cap; an adjacent-channel case is capped at `near` | Numbers and APSTAR scenes; feature-grid tile `STAGE → CLASS → RES 35` |
| **F6** case cards and M4 | Full card schema: source, parties, band, coverage, point, victim, calculation, M4, class, stage, filing action, deadline, missing, question, audit; `same_network`; `not_space` is a finding | APSTAR and missing-data scenes; feature-grid tile |
| **F7** output files and CLI | `cases.json/md`, `queue.md/json`, `funnel.json`, one CSV row per notice (26 columns), a letter per `exceeds`, `run.log`; `--all`, `--limits`, `--terrestrial`, `--ledger` | Personalization beat; feature-grid tile `CSV · JSON · MD` |
| **F8** prose from an LLM, template floor, numeric guard | Optional OpenAI-compatible endpoint; template when unset, on error, on blank, or when the guard rejects a number not on the card; Granite 3.3 2B on OpenShift AI is the Red Hat path | Personalization beat; feature-grid tiles `MODEL` and `OPENSHIFT` |
| **F9** terrestrial side feature | Same command with `--terrestrial`: P.1546-6 field strength at 10 % time, 1,000 km border filter plus every notice whose coordination record names Finland, new/modified/withdrawn from `intent`, neighbour trends and anomalies, ECC T/R 25-08 threshold; on the real pair 32 notices in reach, six above the trigger | Spoken "terrestrial land-mobile notices" with the 32/6; feature-grid tile 07 `same command, same mdb-export ingest, same source/audit/missing contract` |
| **F10** web UI and read-only API | Three panels, every number from `out/`; funnel rows are filters; queue groups by network, administration, band, stage or victim; `Show calculation`, `Show raw data (JSON)`, `Copy question`; 503 when a run is missing | Whole demo; personalization panel `YOUR VIEW` |
| **F11** optional Teams digest | One message per IFIC; funnel, top 3 in queue order, link; `--dry-run`, `--html`, `--send`; no live send tested | Opening hook; feature-grid tile `TEAMS` |
| **F12** complaint register and statistics | Append-only JSONL; closed lists for issue/action/outcome; 206 synthetic complaints and 695 events from `--seed 2026`; stats answer what, whose operation, what was done; CSV export | Missing-data scene; feature-grid tile `REGISTER · STATS` |
| **Monitor and run history** | Hermes cron every 14 days (first run 21 Nov 2026); `runs/<ific>/` plus `runs/latest`; a failed check writes `status: error` and leaves the pointer | Spoken "This morning it checked ITU and processed 3075"; feature-grid tile |
| **OpenShift AI / Red Hat** | Granite 3.3 2B Instruct served by KServe + vLLM in the `janner-1-dev` sandbox; DSPA pipeline manifests in `deploy/openshift/`; live call HTTP 200 on 7 Nov | Spoken "Granite on OpenShift AI in the Red Hat setup"; feature-grid tile |
| **Evaluation set** | 21 labelled cases in `docs/eval-3074.md`; our own labels, not Traficom ground truth; the tile says so | Feature-grid tile `21-case eval · own labels`; not spoken |
| **Deploy and submission** | `deploy/openshift/`, `dist/kaista-submission.zip`; docs, tests, ledger, results | Not a video feature; covered by the submission |

What is deliberately **not** in the two-minute cut: the 552-point territory walk, the 0.1° non-GSO
pass, the 26 CSV columns, the `same_network` union-find, the synthetic-history seed, the exact
`--all` numbers (196 → 176 → 138 → 100 + 38; 55 / 30 / 9 / 6), the `KAISTA_CHECK_LOCKED` demo
lock, and the `c_pfd`/`srv_area` negative results. They are in `docs/features.md` and
`docs/decisions.md`; the video only has two minutes.

## What "yours" means

The personalization beat is not a settings screen. It is the fact that the tool's inputs are the
customer's own files and the customer's own rule, not a hidden model.

| What you control | How | What it changes |
|---|---|---|
| **Band scope** | `--all`, or your `--register` CSV | The demo slice, or every Finnish allocation (299 bands; 132 cases need attention in 3074) |
| **Frequency register** | `--register data/frequencies_of_interest.csv` | Which victim stations and channels define the Finnish side |
| **M4 table** | `--m4 data/taajuusjakotaulukko.json` | The M4 finding (satellite use or not) and the services named on the card |
| **Table 21-4 limits** | `--limits rules/rr21_table21_4.csv` | The limit row the margin is measured against |
| **Card and letter text** | `templates/case_en.md`, `templates/correspondence_fi_en.md` | The wording the specialist sends; the numbers are separate |
| **Model** | `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | Optional prose; no model means the template is the floor |
| **Output directory** | `--out`, `KAISTA_OUT` | Where the run writes and which run the page shows |
| **Complaint log** | `KAISTA_LEDGER` | Where the append-only register lives |
| **UI link** | `KAISTA_URL` | The link in the Teams card |
| **Teams channel** | `TEAMS_WEBHOOK_URL` | Where the digest is posted; the path is implemented, no live send tested |
| **View** | Funnel filters; queue **Group by** network / administration / band / stage / victim | The specialist's own reading order, without changing a number |
| **Deployment** | Laptop or your own OpenShift | The pipeline is offline by default; the monitor's IFIC fetch is the only network step; with `LLM_BASE_URL` unset no model call is made |
| **Decision** | The card, the question, the register events | The tool never guesses and never closes a complaint; the specialist does |

Two things are **fixed and visible**, not configurable: the `near` band is −3 to 0 dB, and the
queue order is stage → class → Resolution 35 deadline. They are in `app/config.py` and
`app/gates.py`; a customer who wants another rule changes code, not a hidden preference. That is
the honest version of "personal": the files are yours, the rule is readable, the model is optional.

## TTS pronunciation

The v1 voice is ElevenLabs Rachel (Eleven Multilingual v2) at 1.2 speed. The v2 script has more
abbreviations, so the TTS text and the caption text should differ where needed: the caption keeps
the written form, the voice gets the spoken form.

| Written | Spoken |
|---|---|
| Kaista | **Kye-sta** in the TTS text, `Kaista` in the caption. "KAI-sta" is read as letters ("K A I sta"); "Kye-sta" gives the Finnish "kai" sound. |
| BR IFIC | B-R I-F-I-C |
| ITU | I-T-U |
| PFD | P-F-D |
| Table 21-4 | Table twenty-one, dash four |
| M4 | M-four |
| MIFR | M-I-F-R |
| APSTAR | A-P-star |
| GSO / non-GSO | G-S-O / non-G-S-O |
| dB | decibels |
| 0.43 | zero point four three |
| 41,222 | forty-one thousand, two hundred and twenty-two |
| 50,645 | fifty thousand, six hundred and forty-five |
| 95,865 | ninety-five thousand, eight hundred and sixty-five |
| Res 35 | Resolution thirty-five |
| P.1546-6 | P one five four six, part six |
| KServe | K-serve |
| OpenShift AI | Open Shift A-I |
| T/R 25-08 | T-R twenty-five, dash zero eight |
| CEPT / ECC | C-E-P-T / E-C-C (not in the cut) |

The current pipeline has one narration string per segment; the captions are split from that same
string. If we want the split, add a `say` field per line and feed `say` to the TTS while the ASS
caption keeps the text. That is a small change to the video tooling, not to the product.

## Recording notes

- Start the app on port 8020 with `KAISTA_CHECK_LOCKED=1` after the other session's UI update, as in
  v1. Refresh the page before recording. **Do not click Check now** on the submission tree: it would
  fetch 3076 and move `runs/latest`. The status line already says 3075, 09:43, 129 notices. Check
  that `126590034` and `126590035` sit under "Needs attention", rows 8–9; if they sit under "No
  effect", the page is stale.
- Open `docs/assets/teams-preview-3075.html` for the hook. The button is a real link to
  `http://127.0.0.1:8020/`, so the recording can click it and cut to the app.
- The feature grid is a new scene. Build it as an HTML overlay with 12 tiles in the Carbon style
  (white, `#161616`, `#525252`, one `#0f62fe` accent, no shadows). Highlight in this order:
  `TERRESTRIAL` → `MONITOR` → the personalization panel → `OPENSHIFT` → `MODEL` / `FLOOR`.
  The other tiles stay visible; the viewer can pause.
- The terrestrial report is `out/TERRESTRIAL.md` from the 3076/3075 pair, not a panel in the 3075
  space app. Show the file, not the app, and say "the same command", not "the same run". Put the
  result on screen or in the tile: 32 notices in reach, six above the ECC T/R 25-08 trigger.
- The complaint register panel shows the synthetic demo history plus the real ledger rows (224
  complaints in the demo, 206 of them synthetic) with its banner. The 3075 run is not in the ledger
  unless `--ledger` was used; the narration says "can open", not "has opened". Do not hide the
  synthetic banner.
- Show `out/run.log` or the card's `audit` line for two seconds: `input_sha256`, `rules_version`.
  Show `out/3074_results.csv` for two seconds at the end: the header, one row per notice, the
  dropped rows with `dropped_at` and `reason`. These are the A/E and D/E proofs the tiles only name.
- The evaluation tile 12 must say "own labels, not Traficom ground truth"; the terrestrial tile 07
  must say "same command, same mdb-export ingest, same source/audit/missing contract". The
  additions are in "Rubric improvements for the next render".
- For tile 11, overlay `dist/redhat-call-2026-11-07.png` for two seconds: `POST /v1/chat/completions`,
  HTTP 200 in 7,492 ms, 7 Nov 2026, no API key. It is the Red Hat checklist's successful call.
- Lock these numbers before the render: `129 → 19 → 9 → 7 + 2`; `3 exceed · 4 near · 2 cannot
  decide`; `0.43 dB`; `41,222 km`, `163.29 dB`; `196 → 20 cards + 1 undecidable`; `32 in reach,
  6 above`.
- The video says "upper bound", never "interference". It says "can push", never "sends to Teams".
  The card says `preview`.
- The `50,645` row count is on screen, not spoken. If the cut runs over 2:00, drop the `41,222
  km`/`163.29 dB` path-loss detail (4 s). Do not drop the terrestrial 32/6 or the personalization
  beat.
- The end card holds the v1 tagline. The voice does not read it; the card needs the last 5 seconds
  (1:50–1:55.4).

## Decisions for Janne

1. **Teams card or phone notification?** Recommendation: the Teams card, because it is the built
   feature and the preview exists; a phone mockup would be a new, unbuilt surface.
2. **How should "Kaista" be pronounced?** The render uses `Kye-sta` in the TTS text and `Kaista` in the caption; `KAI-sta` was read as letters. Keep `Kye-sta` unless a Finnish voice for the name is worth the splice.
3. **Is the 12-tile feature grid the right way to show the breadth?** Recommendation: yes. It gives
   every feature a place without spending narration time; the personalization panel is the
   emphasis.
4. **Should the video say `preview` on the Teams card?** Recommendation: yes. It keeps the claim
   honest and still shows the push; the submission text explains the webhook path and the missing
   test channel.
5. **Wait for the UI update before the final render?** Recommendation: yes. The queue, card and
   register scenes change; the numbers do not. Re-record those scenes after the update and check
   that `126590034` and `126590035` sit under "Needs attention".
6. **Add the provenance and CSV shots?** Recommendation: yes, two seconds each. They are the A/E and
   D/E proof; the feature grid only names them.

## What this does not change

- No product code, no numbers, no run outputs, no `docs/features.md` or `docs/demo-video.md`.
- The v2 MP4 exists (`dist/kaista-demo-v2.mp4`, 1:55.4). The next render applies the corrections in
  this file; the UI scenes wait for the other session's UI update.
- The other session's documentation and UI passes are untouched; this file is new.
