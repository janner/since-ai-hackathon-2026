# sinceai.app submission draft

Since AI Hackathon 2026. Deadline Sun 8 Nov 10:00 EET, submit by 09:00.
Platform is sinceai.app, not Devpost. Copy each field below into the form.

## Required

**Challenge** (pre-filled by the organiser, only they can change it)

Traficom, "Saving Earth from Space Interferers Using Radio Frequencies"

**Project name** (max 80 characters)

Kaista

**Tagline** (max 140, one sentence; voters read it first)

From 95,865 frequency rows to every case that needs a human decision.

**About the project** (max 5,000 chars; problem, solution, how it was built, what we met on the way, what comes next)

Every two weeks the ITU publishes a BR IFIC: a package of new satellite filings. Traficom has to work out which can touch Finnish radio use, check them against Finland's frequency register, and write to the administration behind the filing. The challenge package, Space IFIC 3074, holds 196 notices and 95,865 frequency rows. Today a specialist reads it by hand.

Kaista is the filter for that first pass. It reads one IFIC package, screens every space-to-Earth notice, keeps the ones a satellite can bring over Finnish territory, and computes an upper-bound power flux density at the edge of that territory against ITU Radio Regulations Article 21, Table 21-4. It also asks whether Finland allocates the band to satellite use at all (Regulation M4); a part of the band that is MOBILE AND FIXED makes a transmitting satellite a case even below the limit. The full run covers every Finnish allocation. Whatever survives becomes a case card: source rows, calculation, Finnish allocation, regulatory stage, missing fields and one question for the other administration. A human decides. The queue is not capped and nothing is hidden: every notice has a row in one of three tiers, and the first tier puts the regulatory stage first because a filing another administration can still influence is worth acting on.

On the demo slice (3 470-3 780 MHz) 196 notices become 41 on band overlap, 21 visible from Finland and 20 cards: 11 exceed, 5 near, 4 below the limit on a part of the band Finland has not allocated to satellite use, none clear, and one cannot be computed. Over every Finnish allocation the run goes 196 to 176 to 138 to 73 cards: 30 exceed, 19 near, 2 not_space, 22 clear and 65 cannot be decided, 63 because Table 21-4 has no row and two because the emission power is missing. Every notice that leaves carries a stage and a reason in 3074_results.csv. The run log carries the input SHA256 and the rules version; every card names the limit's source.

Everything before the card text is deterministic: mdb-export reads the BR IFIC Access database, plus a CSV and a JSON file, and standard-library math does the rest. The pipeline never opens a network connection. The PFD is an upper bound, not a claim of interference. The one optional step is prose: with an endpoint configured a language model writes the card summary, otherwise a template does. A numeric guard rejects any sentence whose number is not on the card. In the Red Hat award setup the drafting model runs on Granite 3.3 2B in an OpenShift AI sandbox; with LLM_BASE_URL unset nothing leaves the machine.

Finding the package is the other half. scripts/monitor.py asks ITU for the next space BR IFIC, and the page shows the last check and the next one. The check pulled IFIC 3075: 129 notices to 19 to 9, seven cards and two undecidable. The first queue row is 125520114, a near case at a coordination request Finland can still influence; the APSTAR-92E exceedance (0,43 dB over) is fifth because its filing is already in the MIFR. IFIC 3074 stays the accuracy material.

After the case, the tool keeps an append-only complaint register: what was complained about, whose operation it was, and what was done. The demo's 2021-2026 history is synthetic and labelled; the real rows come from the pipeline runs. A human records the outcome; no line is rewritten.

The tool is one module per feature, 196 tests in all, 142 in a clean clone. A slice run takes about 5 seconds; every Finnish allocation about 50. The terrestrial side task reuses the same command, the same mdb-export step and the same source/audit/missing contract. It reads the 3075→3076 change, computes ITU-R P.1546-6 field strength (land, 50/50, no terrain) at points on Finland's land borders and territorial sea outer limit, and compares it with the ECC T/R 25-08 trigger: 28 land-mobile notices in reach, five above the threshold. Two things the build met: beam geometry is empty in IFIC 3074, so following Traficom's Q3 answer the tool assumes the worst case and says so on the card; and the customer's later rule moved the screen off the delivered register, so a part of the band Finland has not allocated to satellite use is a finding of its own. What comes next: a machine-readable Table 21-4, which today is transcribed by hand. The repo also carries a labelled evaluation set (21 cases, docs/eval-3074.md), marked as our own labels, not Traficom ground truth. Every notice is screened, never sampled; an undecidable row names the missing field, and over-flagging is deliberate because Traficom said a false negative is worse.

What was built during the hackathon, 6-8 Nov 2026, starts from a pre-event template (commit 6fe98b9). Everything after is new. The work was planned, implemented, documented and reviewed by Hermes Agent roles on a shared kanban board, with a human owner who chose the challenge, set the framing and makes the push decision. The demo video's narration was generated with ElevenLabs.

**Built with** (comma-separated; the first five become chips on the vote card)

Python, FastAPI, uvicorn, ITU-R P.1546-6, openpyxl, pytest, ruff, mdbtools, ElevenLabs

The first five are the ones a voter sees, so they carry the substance and the evidence of real data
work: Python is the whole implementation, FastAPI and uvicorn serve the read-only page over the files,
ITU-R P.1546-6 is the ITU recommendation the terrestrial path implements (the main pipeline uses Article
21, Table 21-4, which is a table, not a recommendation), and openpyxl is the path from Traficom's real
register workbook into the pipeline. The last three are development tools and a system helper: pytest and
ruff run in CI, mdbtools is the system tool that reads the IFIC Access database.

**Repository** (public or private; if private, judges read the source zip)

TODO (human): the GitHub repository exists and is private
(`github.com/janner/since-ai-hackathon-2026`); paste its URL here. If it stays private, the judges use
the source zip below.

**Demo video** (YouTube, public or unlisted, ideally under 2 min; no file uploads)

TODO (human): upload the rendered cut `dist/kaista-demo-v2.mp4` (1:55) to YouTube and paste the
link. The v2 script is `docs/demo-video-v2.md`; the v1 script is `docs/demo-video.md`; the
three-minute stage script with the exact commands is `docs/demo.md` §10. No link is invented here.

**Source code .zip** (one file, max 100 MB; leave out dependencies and data)

`make submission-zip` writes `dist/kaista-submission.zip`: the tracked files at HEAD under a `kaista/`
prefix, plus the accuracy files the brief asks for as separate files, under `results/`
(`3074_results.csv`, `terrestrial_findings.json`, `terrestrial_trends.csv`, `TERRESTRIAL.md`). The
repository itself holds no `data/`, `out/`, `.venv/`, `.git/` or `dist/`. Run it after the final
commit, with `out/` filled by a pipeline run, and attach the file.

**MLH questions**

- Technology feedback: fast and pleasant where the data is structured (Python, FastAPI, uv, pytest), and
  the friction was on the outside: the IFIC package is an Access database that only `mdbtools` can read,
  and Article 21, Table 21-4 had to be transcribed by hand into `rules/rr21_table21_4.csv`. A machine-
  readable Table 21-4 would save an afternoon for every team that touches PFD limits.
- GenAI tools used: Hermes Agent, as a set of agent roles on a shared kanban board (planner, two coders,
  a writer, a reviewer). It was used to plan, implement, document and review the work. The human owner
  chose the challenge, set the product framing and makes the push decision. The demo narration was
  generated with ElevenLabs (Eleven Multilingual v2).
- Did you implement a generative AI model or API: no trained model. The repository ships a pre-event
  OpenAI-compatible chat client; the product uses it only for optional card prose, and only when
  `LLM_BASE_URL` is set. Without it the run is fully offline and every card falls back to the
  deterministic template. The drafting LLM for the Red Hat award (Granite 3.3 2B Instruct, served by
  KServe and vLLM in OpenShift AI) is deployed in the sandbox and wrote card drafts in the measured
  run.

**Challenge terms**: accepted by submitting. The challenge transfers no ownership (Traficom is not
confidential), so no personal ticks are needed.

**Public summary**: confidential challenges only. Traficom is not confidential.

## Optional

- Demo URL (judges see it, voters do not): TODO (human), only if a public instance is kept up. The local
  run is the primary demo, and the sandbox expires after 30 days.
- Pitch deck (one PDF or PowerPoint): not produced.
- Supporting documents (max two): `docs/features.md` and `docs/decisions.md` are the two candidates.
  Part 4 of `docs/decisions.md` records the prior art this design answers: the Canadian spectrum
  regulator's own paper on LLM failure modes in spectrum work (arXiv:2403.17819), the abstention
  metric behind `cannot_decide`, the e-discovery screening result that explains why the gates read
  every notice instead of a sample, and the reason reproducibility is the acceptance test the ITU
  itself applies: EPFD examination rests on Rec. ITU-R S.1503-2 and Resolution 85 (Rev. WRC-23), and
  the Bureau required at least two independent implementations before relying on the software
  (https://www.itu.int/epfdsupport/). All sources are listed in README and in part 4 of
  `docs/decisions.md`.
- Partner technologies: Red Hat OpenShift AI. Two parts: the drafting model on KServe with vLLM, and the triage funnel itself as an OpenShift AI Data Science Pipeline. See below.
- Teams digest: no field of its own. The optional `scripts/notify.py` builds one message per IFIC for
  an incoming Teams webhook (dry-run output `out/teams_message.md`, preview `out/teams_message.html`).
  The webhook path is implemented and unit-tested; no live send was made, because there was no test
  channel.

The write-up of what the tool reads and does not use, and what would come next, is in
`docs/features.md` ("Data we read and did not use", "Next steps"). Seven of the 17 IFIC tables reach
no gate on IFIC 3074: the notifier's own PFD limit (`c_pfd`) and the beam power columns
(`s_beam.pwr_max_4k`, `pwr_avg_4k`) carry no value on any Finnish allocation, the coordination
tables (`coord_agree_ntw`, `res49_sel`, `hist_notice`) are empty in this issue, the earth-station
table (`e_stn`) lists 12 stations in five countries and none in Finland, and the Article 22 EPFD data
(`epfd_param`) has no computation path. The filings chain (`ntc_lnk`) and the filing action
(`notice.act_code`) do: the card carries the notice it follows and the queue says whether the filing
is new, modified or suppressed. So do the Resolution 35 deadlines (`grp_res35`): the card shows the
notice's earliest upcoming group deadline, a passed one marked, and the queue sorts inside a stage by
it (one of the 20 demo cases, 125500277, falls due on 19 Dec 2026).
`s_beam.gain` is the exception: it is used, and it is why the beam gain in every PFD is the notice's
own peak gain rather than a worst-case guess.

## Terrestrial side task

The tool answers a second, smaller question Traficom asked: the terrestrial land-mobile notices in
the BR IFIC packages. `python -m app.pipeline --terrestrial` runs it in the same pass and into the
same output directory as the space funnel, and `out/TERRESTRIAL.md` is the readable report. The field
strength from each foreign station is computed with ITU-R P.1546-6 (land, 50/50, no terrain) and
compared with the ECC T/R 25-08 trigger level. Four answers of 7 Nov 2026 fixed the screen:

- The field strength is computed at points on the border line, not at four cities (Q4). The border
  line is the land borders with Sweden, Norway and Russia plus the 12 nautical mile territorial sea
  outer limit, which also surrounds Åland (F2). The tool reports the nearest point to each
  transmitter and the border section where the level is highest, and it flags the register's own
  stations whose field strength passes the threshold.
- The comparison uses the general land-mobile threshold in T/R 25-08 A.1.2.3, and above 470 MHz the
  same 20 dBµV/m (F1). Most of the 3076 land-mobile rows sit above 470 MHz, past the recommendation's
  own tables.
- The side task covers the land-mobile classes only: FB, ML and FL (F3). Fixed (FX) records drop out
  at the class filter, not at the threshold.
- The margin is measured against the T/R 25-08 threshold, not against a national M4 value (F4). The
  register rows' Class of licence labels the row; it does not pick the threshold.

The national M4 value is the one tier that is not confirmed, so the report states the margin against
the ECC threshold and claims no exceedance against the national one.

## Optional award: Red Hat OpenShift AI (1 000 €)

**Claimed: the drafting model is served by OpenShift AI and the app called it.** Granite 3.3 2B
Instruct (Red Hat modelcar) runs on KServe with the vLLM CPU runtime in the sandbox project
`janner-1-dev`, and the prose step drafted cards through its OpenAI-compatible endpoint.

**Also on OpenShift AI: the triage funnel itself as a Data Science Pipeline.** `deploy/openshift/pipeline/`
holds a `DataSciencePipelinesApplication` (`kaista-pipelines`) with managed MinIO and MariaDB, a task
image built in-cluster from this repository, and a three-stage KFP v2 pipeline sharing one workspace
PVC: `ingest -> triage -> metrics`. Caching is off on all three, so each IFIC package is a comparable
run. The measured run on 7 Nov 2026, workflow `kaista-ific-triage-zszqk` (`Succeeded`, 49 min, run id
`febefa66-4181-43c4-92b5-78235f1f1c23`), reproduced the laptop funnel of the same commit exactly, notice for notice and class for class,
and wrote the funnel numbers and the guard's rejection share as the run's own metrics. The prose
step kept two cards in the cluster: a CPU-throughput limit there, not a correctness one.
`deploy/openshift/pipeline/README.md` has the run and the four limitations.

- [x] The drafting LLM (Granite 3.3 2B Instruct modelcar) served by KServe + vLLM CPU runtime in
  OpenShift AI. `oc get isvc granite` reads READY True, the pod is 3/3 Running, and the route
  answers over HTTPS.
- [x] The app calls it through the OpenAI-compatible endpoint, and the numeric guard ran on its output:
  in that slice run the guard rejected 12 of the 17 drafts it saw (the `prose.source` line
  below). That run predates the guard's list-marker fix (`docs/decisions.md` I11). The guard's own
  unit tests (`tests/test_guard.py`) run against a fixed card fixture, not model text, so they pin
  the guard logic, not the served model's output.
- [x] `deploy/openshift/` in repo: the InferenceService YAML, the ServingRuntime YAML, and the apply
  and call commands for the sandbox project `janner-1-dev` (the project already exists; no Namespace
  manifest is shipped).
- [x] Screenshot captured: `dist/redhat-call-2026-11-07.png`. It shows `POST /v1/chat/completions`
  against the Granite 3.3 2B route, HTTP 200 in 7,492 ms on 7 Nov 2026, with no API key or token in
  the frame. The file is in `dist/` (gitignored); attach it to the award form if a file is asked for.
  The route is live and unauthenticated until about 6 Dec 2026. On 7 Nov the node also ran the
  data-science pipeline of the sibling task and one card prompt took 239.5 s, past the app's 120 s
  client timeout, so a live call now needs a longer timeout than the app ships.
- [x] "How did you use it?" field, 40+ characters. The text below.
- [x] One About-text line: what runs in the cluster, what runs locally.

**How did you use it?** (259 characters)

> The case-drafting model (Granite 3.3 2B Instruct) is served by KServe with the vLLM CPU runtime in
> OpenShift AI; the IFIC triage app calls it through an OpenAI-compatible endpoint, and a numeric
> guard rejects drafts whose numbers are not in the computed case.

Measured evidence, 7 Nov 2026, sandbox `janner-1-dev`. The raw output is in
`deploy/openshift/README.md`.

- `curl $U/v1/models`: HTTP 200 in 0.52 s. One short chat completion: HTTP 200 in 9.03 s. One full
  card prompt (1002 prompt tokens, 155 completion tokens): HTTP 200 in 41.84 s. Before the route
  timeout was raised, the same prompt returned HTTP 504 at 30.31 s.
- The cluster slice run: the same gates and the same counts as the local run at that commit. `prose.source`: llm 5, template_guard 12, template 1, so the guard rejected 12 of
  the 17 drafts it saw. One call per card, 36.6 s to 120.3 s, median 86.9 s, whole run 25.6 min. The
  deterministic part of the same run took 1.19 s.
- `make check` green: 137 tests passed in that run; 196 at the final commit. The tests never need
  the network.
- One card fell back to the template. The slowest call measured 120.3 s, right at the 120 s
  client timeout in `app/llm.py`, but the log does not tell a timeout from a blank answer. After the
  list-marker fix a re-run on the loaded node did not get through that timeout at all:
  `deploy/openshift/README.md` has the three attempts.

The local run stays the primary demo. The sandbox expires about 6 Dec 2026, so the route is never
the only demo link. The route is unauthenticated, and that is why no token sits in the repository
or in any screenshot.

Sandbox facts (verified 6 and 7 Nov 2026, namespace `janner-1-dev`):

- KServe is available: `oc auth can-i create inferenceservices` = yes. Runtime template
  `vllm-cpu-x86-runtime-template` in `redhat-ods-applications`. No GPU quota, 3 CPU request quota.
- No build step for the model: KServe pulls the modelcar
  `quay.io/redhat-ai-services/modelcar-catalog:granite-3.3-2b-instruct` as an OCI artifact and mounts
  it at `/mnt/models`. The first start took about 8 minutes (the pull, then the vLLM load of 4.72 GiB).
- The router default timeout of 30 s returns 504 on any real card. The annotation
  `haproxy.router.openshift.io/timeout: 300s` on the InferenceService fixes it. It has to sit on the
  isvc, because the KServe controller owns the route and resets annotations set on the route itself.
- Sandbox expires 30 days after activation (~6 Dec 2026).

## Final check before 10:00

Automated, done in the repository

- [x] `make check` green: ruff check, ruff format --check, 196 tests passed
- [x] README run steps work in a clean clone (142 passed, 54 skipped without `data/`)
- [x] Pre-existing work and outside assets stated in README and About (template commit `6fe98b9`)
- [x] No secrets or challenge data committed; `data/` and `out/` are gitignored
- [x] `make submission-zip` builds `dist/kaista-submission.zip`, tracked files at HEAD only, no data
- [x] `docs/architecture.md` present and linked from the README documentation table
- [x] Submission-form field text lengths, re-measured 7 Nov 2026: name 6 and tagline 69 are inside
      their limits; the About text is 4,939 characters, inside the form's 5,000 limit.

Human steps, before submitting

- [ ] Push: `origin/main` already carries the deadline commits; push the final commit before submitting
- [ ] Demo video on YouTube, public or unlisted, under 2 minutes; opens on the automatic check (the
      automatic-check panel and the "Check now" click) in the first 30 seconds
- [ ] Source zip rebuilt after the final commit and attached to the form (under 100 MB)
- [ ] Repository URL pasted into the form (and the repo made readable to judges)
- [ ] Demo URL opens logged out, if a demo URL is given at all
- [ ] Every field of the form copied over and the form submitted by 09:00
- [ ] Red Hat award: the boxes are ticked in this draft. Janne ticks the form and pastes the
      "How did you use it?" text. The https link to `deploy/openshift/` does not open for a reviewer
      while the repository is private, so publish it or grant access first.
- [ ] `SUBMISSION.md` is a draft of the form, TODOs and all: decide whether it stays in a public
      repository as-is or is moved out once the fields are submitted
