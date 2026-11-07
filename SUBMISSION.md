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

Every two weeks the ITU publishes a BR IFIC: a package of new satellite filings. Traficom has to work out which of them can touch Finnish radio use, check them against the Finnish frequency register, and write to the administration behind the filing. The package the challenge ships, Space IFIC 3074, holds 196 notices and 95,865 frequency rows. Today a specialist reads it by hand.

Kaista is a triage tool for that first pass. It reads one IFIC package, derives the protected bands from Traficom's table of frequencies of interest, keeps the space-to-Earth notices that overlap those bands and can be seen from Finland, and computes an upper-bound power flux density against the ITU Radio Regulations Article 21, Table 21-4 limit. Whatever survives and can be computed becomes a case card: the source rows, the calculation, the Finnish allocation from Regulation M4, the regulatory stage of the filing, the fields that are missing, and one question for the other administration. A human decides what to do with each card.

The funnel is the whole point, so the tool shows it. On the demo slice of the challenge package (3 470 to 3 780 MHz) 196 notices become 41 on band overlap, 19 visible from Finland and 18 computed cards: nine exceed the limit, five come near it, four are clear, and one notice passes both gates but cannot be computed, so it keeps a row as cannot_decide instead of becoming a card. Over all seven space bands the run goes 196 to 101 to 75 to 64 cards. The queue is not capped, and inside a class it puts the stage another administration can still influence (advance publication, coordination request) before a filing already recorded in the MIFR. Nothing is dropped silently: every notice that leaves carries a stage and a reason in 3074_results.csv.

Everything before the card text is deterministic: `mdb-export` reads the BR IFIC Access database, plus a CSV and a JSON file, and standard-library math does the rest. The pipeline never opens a network connection. The PFD is an upper bound, not a claim of interference: max PSD plus max beam gain minus free-space loss, against Table 21-4. The one optional step is prose. With an endpoint configured a language model writes the card summary, otherwise a template does. The model never supplies a number: a numeric guard rejects any sentence whose number is not already on the card, and the template takes over. In the Red Hat award setup the drafting model runs in an OpenShift AI sandbox and the pipeline runs on the laptop; with `LLM_BASE_URL` unset nothing leaves the machine.

Finding the package is the other half, so the tool does it too. `scripts/monitor.py` asks ITU for the next space BR IFIC, and the page shows the last package checked, when it was checked and, when nothing new is out yet, when the next check falls. "Check now" asks ITU again and ingests what it finds; a clean run writes its own `runs/<ific>/` and moves the `runs/latest` pointer. The check pulled IFIC 3075, the automatic path's demo: 129 notices to 19 to 9, seven cards and two undecidable notices, first card 3075-108501259 (APSTAR-92E, 0,38 dB over the limit). IFIC 3074 stays the accuracy material.

The tool is one module per feature, each with its own test file, 165 tests in all, 121 of them in a clean clone. A slice run takes about 3.5 seconds. A side feature applies the same style to terrestrial land-mobile notices: `python -m app.pipeline --terrestrial` runs it in the same pass and into the same output directory, with the same `source` and `audit` blocks on every file it writes, and only the calculation path differs, ITU-R P.1546-6 field strength instead of the PFD gates.

Two things the build met on the way. Beam geometry is empty in IFIC 3074 (`s_beam.bore_long`, `bore_lat`, `maj_axis`, `min_axis`), and following Traficom's Q3 answer the tool does not try to decide coverage from the beam: the worst case is always assumed, with the notice's own peak gain aimed at the Finnish station. A card states that on a `Coverage` line and asks the administration to confirm the worst-case PFD, so the `s_beam` fields no longer appear under `missing`. And the reference tool behind the plan read the register cell `0,1G` as 0.1 MHz, while this code reads the `Channel bandwidth` column as 0.1 GHz = 100 MHz; that is why the seven-band funnel sits one notice above the plan (101 against 100). The demo slice is identical either way, and the difference is written up in docs/decisions.md.

What comes next: a labelled evaluation set, so the screening can be measured against a human decision; and a machine-readable Article 21, Table 21-4, which today has to be transcribed by hand.

What was built during the hackathon, 6 to 8 Nov 2026, starts from a pre-event repository template (commit `6fe98b9`): a FastAPI skeleton, an OpenAI-compatible client and a test setup. Everything after that commit is new. The work was planned, implemented, documented and reviewed by Hermes Agent roles on a shared kanban board (planner, coder, writer, reviewer), with a human owner who chose the challenge, set the framing and makes the push decision.

**Built with** (comma-separated; the first five become chips on the vote card)

Python, FastAPI, uvicorn, ITU-R P.1546-6, openpyxl, pytest, ruff, mdbtools

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

TODO (human): Janne records it. The two-minute video script — timed narration, screen plan and
caption lines — is `docs/demo-video.md`; the three-minute stage script with the exact commands is
`docs/demo.md` §10. No link is invented here.

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
  chose the challenge, set the product framing and makes the push decision.
- Did you implement a generative AI model or API: no trained model. The repository ships a pre-event
  OpenAI-compatible chat client; the product uses it only for optional card prose, and only when
  `LLM_BASE_URL` is set. Without it the run is fully offline and every card falls back to the
  deterministic template. The drafting LLM for the Red Hat award (Granite 3.3 2B Instruct, served by
  KServe and vLLM in OpenShift AI) is deployed in the sandbox and wrote 5 of the 18 card drafts in
  the measured run.

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
`docs/features.md` ("Data we read and did not use", "Next steps"). Ten of the 15 IFIC tables reach
no gate on IFIC 3074: the notifier's own PFD limit (`c_pfd`) and the beam power columns
(`s_beam.pwr_max_4k`, `pwr_avg_4k`) carry no value on any of the seven space bands, the coordination
tables (`coord_agree_ntw`, `res49_sel`, `hist_notice`) are empty in this issue, the earth-station
table (`e_stn`) lists 12 stations in five countries and none in Finland, the Resolution 35 deadlines
(`grp_res35`) touch one of the 18 demo cases, and the Article 22 EPFD data (`epfd_param`), the
filings chain (`ntc_lnk`) and the filing action (`notice.act_code`) have no computation path.
`s_beam.gain` is the exception: it is used, and it is why the beam gain in every PFD is the notice's
own peak gain rather than a worst-case guess.

## Optional award: Red Hat OpenShift AI (1 000 €)

**Claimed: the drafting model is served by OpenShift AI and the app called it.** Granite 3.3 2B
Instruct (Red Hat modelcar) runs on KServe with the vLLM CPU runtime in the sandbox project
`janner-1-dev`, and the prose step drafted cards through its OpenAI-compatible endpoint.

**Also on OpenShift AI: the triage funnel itself as a Data Science Pipeline.** `deploy/openshift/pipeline/`
holds a `DataSciencePipelinesApplication` (`kaista-pipelines`) with managed MinIO and MariaDB, a task
image built in-cluster from this repository, and a three-stage KFP v2 pipeline sharing one workspace
PVC: `ingest -> triage -> metrics`. Caching is off on all three, so each IFIC package is a comparable
run. The measured run on 7 Nov 2026, workflow `kaista-ific-triage-zszqk` (`Succeeded`, 49 min, run id
`febefa66-4181-43c4-92b5-78235f1f1c23`), reproduced the laptop funnel exactly (196 notices to G1 41,
G2 19, G3 18 + 1 `cannot_decide`, exceeds 9 / near 5 / clear 4, queue 15) and wrote the funnel
numbers and the guard's rejection share as the run's own metrics. The prose step kept 2 of 18 cards
in the cluster: a CPU-throughput limit there, not a correctness one.
`deploy/openshift/pipeline/README.md` has the run and the four limitations.

- [x] The drafting LLM (Granite 3.3 2B Instruct modelcar) served by KServe + vLLM CPU runtime in
  OpenShift AI. `oc get isvc granite` reads READY True, the pod is 3/3 Running, and the route
  answers over HTTPS.
- [x] The app calls it through the OpenAI-compatible endpoint, and the numeric guard ran on its output:
  in the 18-card slice run the guard rejected 12 of the 17 drafts it saw (the `prose.source` line
  below). That run predates the guard's list-marker fix (`docs/decisions.md` I11). The guard's own
  unit tests (`tests/test_guard.py`) run against a fixed card fixture, not model text, so they pin
  the guard logic, not the served model's output.
- [x] `deploy/openshift/` in repo: the InferenceService YAML, the ServingRuntime YAML, and the apply
  and call commands for the sandbox project `janner-1-dev` (the project already exists; no Namespace
  manifest is shipped).
- [ ] Screenshot or short recording of a successful call; no keys or tokens in it. Not captured yet.
  The route is live and unauthenticated until about 6 Dec 2026, so it can still be taken. On 7 Nov
  the node also ran the data-science pipeline of the sibling task and one card prompt took 239.5 s,
  past the app's 120 s client timeout, so a live call now needs a longer timeout than the app ships.
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
- The 18-card slice run: 196 notices to 41 to 19 to 18 cards plus 1 `cannot_decide`, identical to
  the local run. `prose.source`: llm 5, template_guard 12, template 1, so the guard rejected 12 of
  the 17 drafts it saw. One call per card, 36.6 s to 120.3 s, median 86.9 s, whole run 25.6 min. The
  deterministic part of the same run took 1.19 s.
- `make check` green: 137 tests passed in that run; 165 at the final commit. The tests never need
  the network.
- One card of 18 fell back to the template. The slowest call measured 120.3 s, right at the 120 s
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

- [x] `make check` green: ruff check, ruff format --check, 165 tests passed
- [x] README run steps work in a clean clone (121 passed, 44 skipped without `data/`)
- [x] Pre-existing work and outside assets stated in README and About (template commit `6fe98b9`)
- [x] No secrets or challenge data committed; `data/` and `out/` are gitignored
- [x] `make submission-zip` builds `dist/kaista-submission.zip`, tracked files at HEAD only, no data
- [x] `docs/architecture.md` present and linked from the README documentation table
- [x] Submission-form field text lengths, re-measured 7 Nov 2026: name 6 and tagline 69 are inside
      their limits; the About text is 4,867 characters, inside the form's 5,000 limit.

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
