# Granite on OpenShift AI: what runs where

The case-drafting model runs in the cluster. Everything else runs on the laptop.

| Piece | Where | What |
|---|---|---|
| `vllm-cpu-x86-runtime` (ServingRuntime) | OpenShift AI sandbox `janner-1-dev` | vLLM CPU serving runtime, image pinned by digest |
| `granite` (InferenceService, RawDeployment) | same project | Granite 3.3 2B Instruct from the Red Hat modelcar catalog, 4096 token context |
| Route `granite` | same project | Edge TLS, redirects HTTP to HTTPS |
| `app/pipeline.py` and the rest | laptop | Ingestion, gates, PFD, cards, funnel, UI |
| `app/llm.py` (one chat call per card) | laptop to route | The only network call in a run, and only in the optional prose step |

The deterministic path never opens a connection. Unset `LLM_BASE_URL` and the cards get the
deterministic template instead. Tests never need the network.

## Apply it

```bash
oc project janner-1-dev
oc apply -f deploy/openshift/servingruntime.yaml
oc apply -f deploy/openshift/inferenceservice.yaml
oc get isvc granite          # READY True when the modelcar pull and vLLM start are done
oc get route granite
```

The image comes from the modelcar catalog, so there is no build step and no model download at
start: KServe pulls `quay.io/redhat-ai-services/modelcar-catalog:granite-3.3-2b-instruct` as an
OCI artifact and mounts it at `/mnt/models`.

First start took about 8 minutes on this node: the modelcar pull, then the vLLM load of 4.72 GiB of
weights. The `READY` column read `False` for 8 minutes after the first apply, then went `True`.

## Call it

```bash
U=https://granite-janner-1-dev.apps.rm2.thpm.p1.openshiftapps.com
curl $U/v1/models
curl $U/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"granite","messages":[{"role":"user","content":"Say hello in one short sentence."}]}'
```

## Run the pipeline against it

```bash
export LLM_BASE_URL=https://granite-janner-1-dev.apps.rm2.thpm.p1.openshiftapps.com/v1
export LLM_MODEL=granite
uv run python -m app.pipeline --ific data/itu-ific-3074 \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json --out out/
```

`app/llm.py` speaks the OpenAI chat API, so the same command works against any endpoint that
does. The card records the served model in `prose.model` when the model text is kept.

## Measured evidence (7.11.2026, sandbox `janner-1-dev`)

`oc get isvc granite`, after the rollout:

```
NAME      URL                                                               READY   AGE
granite   https://granite-janner-1-dev.apps.rm2.thpm.p1.openshiftapps.com   True    34m
```

Conditions `IngressReady`, `PredictorReady` and `Ready` are all `True`; pod
`granite-predictor-*` is 3/3 Running (kserve-container, kube-rbac-proxy, modelcar).

`/v1/models`, truncated:

```
{"object":"list","data":[{"id":"granite","object":"model","owned_by":"vllm",
  "root":"/mnt/models","max_model_len":4096}]}
HTTP 200 0.52s
```

One short chat completion, truncated:

```
{"id":"chatcmpl-8b87c753cb961efb","model":"granite",
 "choices":[{"message":{"role":"assistant","content":"\"Hello there!\""}}],
 "usage":{"prompt_tokens":66,"completion_tokens":5}}
HTTP 200 9.03s
```

One full case card prompt (1002 prompt tokens, 155 completion tokens):

```
HTTP 200 41.84s
```

Before the router timeout was raised, the same card prompt returned:

```
504 Gateway Time-out
HTTP 504 30.31s
```

A slice run against the served model, 18 cards:

```
196 notices -> G1 41 -> G2 19 -> G3 18 + 1 cannot decide
exceeds 9, near 5, clear 4, 19 in the queue (1 groups, 2 bands)
```

Funnel and class counts are identical to the local run. The prose step changes nothing but the
sentences, and the guard is why.

`prose.source` over the 18 cards: **llm 5, template_guard 12, template 1**. The guard rejected
12 of the 17 drafts it saw, 71 %. Three of those drafts were re-asked to see the reason: two were rejected by a list marker (`1.` in
a numbered answer counts as a number) and one by an invented band (`300-400 MHz FSS`). The other
nine rejections were not inspected one by one.

Response time per card, one chat call each, in card order:

| case | class | prose | s |
|---|---|---|---|
| 3074-124545403 | exceeds | llm | 57.7 |
| 3074-125500066 | exceeds | template_guard | 48.8 |
| 3074-125500277 | exceeds | llm | 36.6 |
| 3074-103500417 | exceeds | template_guard | 108.7 |
| 3074-303500417 | exceeds | template_guard | 71.4 |
| 3074-124520183 | exceeds | template | 120.3 |
| 3074-119500051 | exceeds | llm | 82.7 |
| 3074-319500051 | exceeds | template_guard | 82.4 |
| 3074-124520184 | exceeds | llm | 74.9 |
| 3074-124520214 | near | template_guard | 114.6 |
| 3074-95500027 | near | template_guard | 108.7 |
| 3074-322500245 | near | llm | 56.4 |
| 3074-103500416 | near | template_guard | 91.1 |
| 3074-303500416 | near | template_guard | 72.0 |
| 3074-125512022 | clear | template_guard | 112.9 |
| 3074-125512023 | clear | template_guard | 97.4 |
| 3074-109500876 | clear | template_guard | 99.5 |
| 3074-309500876 | clear | template_guard | 98.8 |

18 calls, 36.6 s to 120.3 s, median 86.9 s. The whole run took 25.6 min. The deterministic part of
the same run took 1.19 s.

## Limitations

1. **CPU only.** The sandbox has no GPU and a 3 CPU request quota, so the model is small and one
   card takes about 85 s. Case letters are generated in a run, never in the live demo.
2. **Route timeout.** The router default of 30 s returns 504 on any real card. The annotation
   `haproxy.router.openshift.io/timeout: 300s` on the InferenceService fixes it. It has to be on
   the isvc: the KServe controller owns the route and resets annotations set on the route itself.
3. **Client timeout.** `app/llm.py` gives up after 120 s. The slowest card measured 120.3 s, right
   at that ceiling, and one card of 18 fell back to the template. The fallback is by design, and
   the card says so.
4. **The route is unauthenticated.** The InferenceService carries
   `networking.kserve.io/visibility: exposed`, so anyone with the URL can call the model. That is
   acceptable for a sandbox demo and is why no token is used here and none is stored in the repo.
5. **The guard checks numbers, not meaning.** All five kept drafts use numbers that are in the
   card, and some of them still put a correct number in the wrong role (an M4 antenna gain
   reported as the victim's gain, `PSD -42.8 dBW/Hz` for a PFD). The guard cannot catch that, and
   this is exactly why the pipeline leaves the verdict to a human.
6. **Sandbox lifetime.** The OpenShift AI sandbox expires about 6.12.2026. The local run is the
   primary demo, and this route is the bonus.
