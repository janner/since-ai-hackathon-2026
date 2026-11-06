# sinceai.app submission draft

Fill in while building. Deadline Sun 8 Nov 10:00 EET. Submit by 09:00.

- Challenge: (pre-filled)
- Project name:
- Submission URL (must work after the event):
- About the project (max 5,000 chars):
- Repository / demo link (test logged out):
- Built with (comma-separated):
- Technology feedback:
- GenAI tools used:
- Generative AI in your project (how and why, or N/A):
- [ ] Challenge IP terms accepted
- Optional: video URL, pitch deck (PDF), supporting docs. No ZIP files.

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

- [ ] Repo public or reviewer-accessible (only if IP terms allow)
- [ ] README run steps work in a clean clone
- [ ] Demo URL opens logged out
- [ ] No secrets or challenge data committed
