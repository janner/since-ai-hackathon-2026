# sinceai.app submission draft

Since AI Hackathon 2026. Deadline Sun 8 Nov 10:00 EET, submit by 09:00.
Platform is sinceai.app, not Devpost. Copy each field below into the form.

## Required

**Challenge** (pre-filled by the organiser, only they can change it)

Traficom, "Saving Earth from Space Interferers Using Radio Frequencies"

**Project name** (max 80 characters)

Kaista

**Tagline** (max 140, one sentence; voters read it first)

From 95,865 frequency rows to 20 cases a human can decide.

**About the project** (max 5,000 chars; problem, solution, how it was built, what we met on the way, what comes next)

Every two weeks the ITU publishes a BR IFIC: a package of new satellite filings. Traficom has to work out which of them can touch Finnish radio use, check them against the Finnish frequency register, and write to the administration behind the filing. The package the challenge ships, Space IFIC 3074, holds 196 notices and 95,865 frequency rows. Today a specialist reads it by hand.

Kaista is a triage tool for that first pass. It reads one IFIC package, derives the protected bands from Traficom's table of frequencies of interest, keeps the space-to-Earth notices that overlap those bands and can be seen from Finland, and computes an upper-bound power flux density against the ITU Radio Regulations Article 21, Table 21-4 limit. Whatever survives and can be computed becomes a case card: the source rows, the calculation, the Finnish allocation from Regulation M4, the fields that are missing, and one question for the other administration. A human decides what to do with each card.

The funnel is the whole point, so the tool shows it. On the demo slice (3,470 to 3,780 MHz) 196 notices become 41 on band overlap, 19 visible from Finland, and 18 computed cards. Nine cards exceed the limit, five come near it and four are clear. One notice passes the first two gates and cannot be computed, so it keeps its row in the queue and the CSV as cannot_decide instead of becoming a card. Over all seven space bands the run goes 196 to 101 to 75 to 64 computed cards, with 26 exceeding, 15 near and 23 clear, and a queue of 20. Nothing is dropped silently: every notice that leaves carries a stage and a reason in 3074_results.csv, and the counts are in funnel.json.

Everything before the card text is deterministic. The pipeline reads CSV and JSON, uses standard-library math, and never opens a network connection. The PFD is an upper bound, not a claim of interference: max PSD plus max beam gain minus free-space loss, against Table 21-4. The one optional step is prose. If LLM_BASE_URL is set, a language model writes the card summary; if it is not, a template does. The model never supplies a number. A numeric guard reads every sentence and rejects it if it carries a number that is not already in the card, and the template takes over. The letter to the other administration has its own template and its own function.

The tool is built as one module per feature, each with its own test file, 114 tests in all. A slice run takes about 1.3 seconds and the seven-band run about 5.5 seconds on the hackathon machine. The repository also carries a side feature for terrestrial land-mobile notices: it diffs two 3076-style extracts, keeps what is within 1,000 km of Finland and overlaps the register, and computes ITU-R P.1546-6 field strength at four Finnish test points.

Two things the build met on the way. Beam geometry is empty in IFIC 3074, so the tool cannot decide whether a beam actually illuminates Finland; instead of guessing, every card carries that as a question and lists the missing fields. And the reference tool behind the plan read the register cell `0,1G` as 0.1 MHz, while this code reads the `Channel bandwidth` column as 0.1 GHz = 100 MHz; that is why the seven-band funnel sits one notice above the plan (101 against 100). The demo slice is identical either way, and the difference is written up in docs/decisions.md.

What comes next: a labelled evaluation set, so the screening can be measured against a human decision; a converter for real 3076 extracts for the terrestrial path; and a run of the prose step against a real OpenAI-compatible endpoint, which the tests currently cover only with a stub.

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

TODO (human): Janne creates or pushes the GitHub repository and pastes the URL here. Not filled in this
draft, because the URL does not exist yet (`main` is not pushed). If the repository stays private, the
judges use the source zip below.

**Demo video** (YouTube, public or unlisted, ideally under 2 min; no file uploads)

TODO (human): Janne records it. Script and exact commands are in `docs/demo.md` (three minutes on stage,
under two minutes on video, product visible in the first 20 seconds). No link is invented here.

**Source code .zip** (one file, max 100 MB; leave out dependencies and data)

`make submission-zip` writes `dist/kaista-submission.zip` from the tracked files at HEAD, under a
`kaista/` prefix. It holds the repository's tracked files only: no `data/`, `out/`, `.venv/`, `.git/`
or `dist/`. Run it after the final commit, attach the file.

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
  deterministic template. The drafting LLM proposed for the Red Hat award (Granite 3.3 2B Instruct,
  served by KServe and vLLM in OpenShift AI) was planned but not deployed.

**Challenge terms**: accepted by submitting. The challenge transfers no ownership (Traficom is not
confidential), so no personal ticks are needed.

**Public summary**: confidential challenges only. Traficom is not confidential.

## Optional

- Demo URL (judges see it, voters do not): TODO (human), only if a public instance is kept up. The local
  run is the primary demo, and the sandbox expires after 30 days.
- Pitch deck (one PDF or PowerPoint): not produced.
- Supporting documents (max two): `docs/features.md` and `docs/decisions.md` are the two candidates.
- Partner technologies: not claimed, see below.

## Optional award: Red Hat OpenShift AI (1 000 €)

**Not claimed: F12 (OpenShift AI) was scoped P2 and not implemented.** No box under Partner technologies
is ticked, because a Red Hat reviewer checks the evidence and there is none: no InferenceService was
deployed, no model was served, and the app never called a vLLM endpoint.

The checklist below is kept as a record of the plan and stays unticked.

- [ ] The drafting LLM (Granite 3.3 2B Instruct modelcar) served by KServe + vLLM CPU runtime in OpenShift AI
- [ ] The app calls it through the OpenAI-compatible endpoint; the numeric guard tests pass against its output
- [ ] `deploy/openshift/` in repo: InferenceService YAML, build commands, namespace
- [ ] Screenshot or short recording of a successful call; no keys or tokens in it
- [ ] "How did you use it?" field, 40+ characters
- [ ] One About-text line: what runs in the cluster, what runs locally

The About text above mentions no cluster, and that is deliberate.

Sandbox facts (verified 6 Nov 2026, namespace `janner-1-dev`), kept for any later attempt:

- KServe is available: `oc auth can-i create inferenceservices` = yes. Runtime template
  `vllm-cpu-x86-runtime-template` in `redhat-ods-applications`. No GPU quota.
- Build without PyPI: `oc new-build --binary --name=app --image-stream=python:3.12-ubi9`, `.s2i/bin/run`
  with `exec python app.py`, then `oc start-build app --from-dir=. -F`.
- `oc expose` makes an HTTP-only route and `https://` returns 503. Patch edge TLS immediately, then both work.
- Sandbox expires 30 days after activation (~6 Dec 2026). Never the only demo link.

## Final check before 10:00

Automated, done in the repository

- [x] `make check` green: ruff check, ruff format --check, 114 tests passed
- [x] README run steps work in a clean clone (102 passed, 12 skipped without `data/`)
- [x] Pre-existing work and outside assets stated in README and About (template commit `6fe98b9`)
- [x] No secrets or challenge data committed; `data/` and `out/` are gitignored
- [x] `make submission-zip` builds `dist/kaista-submission.zip`, tracked files at HEAD only, no data
- [x] `docs/architecture.md` present and linked from the README documentation table
- [x] Submission-form field text lengths checked: name 6, tagline 58, About under 5,000 characters

Human steps, before submitting

- [ ] Push: decide on `origin/main` and push the deadline commit (`main` was ahead of origin and not pushed)
- [ ] Demo video on YouTube, public or unlisted, under 2 minutes, product visible in the first 20 seconds
- [ ] Source zip rebuilt after the final commit and attached to the form (under 100 MB)
- [ ] Repository URL pasted into the form (and the repo made readable to judges)
- [ ] Demo URL opens logged out, if a demo URL is given at all
- [ ] Every field of the form copied over and the form submitted by 09:00
- [ ] Red Hat award left unticked
- [ ] `SUBMISSION.md` is a draft of the form, TODOs and all: decide whether it stays in a public
      repository as-is or is moved out once the fields are submitted
