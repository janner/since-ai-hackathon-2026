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

- [ ] App runs on OpenShift, public Route answers logged out
- [ ] Model served in-cluster, `/model` returns name, version, training data and R²
- [ ] `/predict` returns a real inference, not a constant
- [ ] `deploy/` in repo: build commands, manifests, namespace
- [ ] Data Science Pipeline run in OpenShift AI that trains the same model (run id + screenshot of a successful run)
- [ ] One About-text line: what runs in the cluster, what runs locally

Sandbox facts (verified 6 Nov 2026, namespace `janner-1-dev`):

- No KServe: `InferenceService` and `ServingRuntime` are not API resources. Serve the model from your own container.
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
