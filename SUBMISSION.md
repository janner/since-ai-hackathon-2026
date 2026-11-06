# sinceai.app submission draft

Fill in while building. Deadline Sun 8 Nov 10:00 EET. Submit by 09:00.
Platform is sinceai.app, not Devpost.

## Required

Official list, Builder Guide 4 Nov 2026.

- Challenge: (pre-filled by the organiser, only they can change it)
- Project name (max 80 characters):
- Tagline (max 140, one sentence; voters read it first):
- About the project (max 5,000 chars): problem, solution, how it was built, what we met on the way, what comes next
- Built with (comma-separated; the first five become chips on the vote card):
- Repository (public or private; if private, judges read the source zip):
- Demo video (YouTube, public or unlisted, ideally under 2 min; no file uploads):
- Source code .zip (one file, max 100 MB; leave out dependencies and data):
- MLH questions: technology feedback, GenAI tools used (or "I did not use GenAI"), did you implement a generative AI model or API
- Challenge terms: accepted by submitting; if the challenge transfers ownership, every member ticks personally
- Public summary: confidential challenges only. Traficom is not confidential.

## Optional

- Demo URL (judges see it, voters do not)
- Pitch deck (one PDF or PowerPoint)
- Supporting documents (max two)
- Partner technologies (Red Hat OpenShift AI or FIWARE also enters that award)

## Optional award: Red Hat OpenShift AI (1 000 €)

Tick "Red Hat OpenShift AI" under Partner technologies in the form. A Red Hat reviewer checks the evidence, so it has to be real.

Rule (Field Guide): "meaningfully use Red Hat OpenShift AI, for example to build, serve or monitor the model your solution relies on". Weights: OpenShift AI use 35, business value 30, technical reliability 25, documentation 10.

- [ ] The drafting LLM (Granite 3.3 2B Instruct modelcar) served by KServe + vLLM CPU runtime in OpenShift AI
- [ ] The app calls it through the OpenAI-compatible endpoint; the numeric guard tests pass against its output
- [ ] `deploy/openshift/` in repo: InferenceService YAML, build commands, namespace
- [ ] Screenshot or short recording of a successful call; no keys or tokens in it
- [ ] "How did you use it?" field, 40+ characters
- [ ] One About-text line: what runs in the cluster, what runs locally (local run stays the primary demo; the sandbox expires after 30 days)

Sandbox facts (verified 6 Nov 2026, namespace `janner-1-dev`):

- KServe is available: `oc auth can-i create inferenceservices` = yes. Runtime template `vllm-cpu-x86-runtime-template` in `redhat-ods-applications`. No GPU quota.
- Build without PyPI: `oc new-build --binary --name=app --image-stream=python:3.12-ubi9`, `.s2i/bin/run` with `exec python app.py`, then `oc start-build app --from-dir=. -F`.
- `oc expose` makes an HTTP-only route and `https://` returns 503. Patch edge TLS immediately, then both work.
- Sandbox expires 30 days after activation (~6 Dec 2026). Never the only demo link.

## Final check before 10:00

- [ ] Repo accessible to judges (private is fine with the zip; public only if IP terms allow)
- [ ] README run steps work in a clean clone
- [ ] Demo video on YouTube, under 2 minutes, first 20 seconds shows the product
- [ ] Source zip is the deadline state and under 100 MB
- [ ] Demo URL opens logged out
- [ ] Pre-existing work and outside assets stated in README and About
- [ ] No secrets or challenge data committed
