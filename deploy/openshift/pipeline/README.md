# The IFIC run as a Data Science Pipeline

The triage funnel runs in the cluster as an OpenShift AI Data Science Pipeline: one
pipeline, three container tasks, and a run whose own metrics are the point. Every IFIC
package is a new run, so the numbers can be compared from one package to the next.

## What runs where

| Piece | Where | What |
|---|---|---|
| `kaista-pipelines` (DataSciencePipelinesApplication) | OpenShift AI sandbox `janner-1-dev` | Managed MinIO for artifacts, MariaDB for run metadata, the KFP v2 API server, the Argo workflow controller |
| `kaista-pipeline` (image) | built in-cluster from this repo | `app/` plus the three stage bodies in `pipeline_stages.py`, with `mdbtools` for the BR IFIC Access database |
| `kaista-workspace` (PVC) | the three tasks | The only thing the stages share: the extracted database, the register, M4 and the run's output |
| `ific` (bucket) | managed MinIO | The published IFIC package, the register CSV and the M4 table |
| `granite` (InferenceService) | same project | The prose step, called over the in-cluster KServe service |
| Everything else | laptop | UI, tests, this repository |

## The pipeline

```
ingest ──▶ triage ──▶ metrics
```

| Task | What it does |
|---|---|
| `ingest` | Lists the `ific` bucket, fetches the published package zip and the two side inputs, and unpacks `ific3074.mdb`. Fails if the database or `mdb-export` is missing. |
| `triage` | Runs the deterministic funnel (gates → cards), one chat call per card to the served model, and the numeric guard. Writes `cases.json`, `funnel.json`, the queue and the letters into `/workspace/out`. |
| `metrics` | Reads `funnel.json` and `cases.json` back and reports the funnel numbers and the guard's rejection share, writing `metrics.json`. |

Caching is off on all three tasks: a cached task would hand the next run the previous
package's workspace.

The deterministic core runs as one task because `app.pipeline.run` computes the whole
funnel in a single pass and writes its results as files; that task's log carries the
gate-by-gate numbers. The metrics task is what turns those files into the run's record.

## Build the task image

The build context is the repository without `data/`, so the IFIC data never enters the
image or the repository:

```bash
oc project janner-1-dev
oc apply -f deploy/openshift/pipeline/buildconfig.yaml
tar czf /tmp/ctx.tgz app rules templates pyproject.toml uv.lock \
  deploy/openshift/pipeline/Dockerfile deploy/openshift/pipeline/pipeline_stages.py
oc start-build kaista-pipeline --from-archive=/tmp/ctx.tgz --follow
```

## Apply the pipeline server

```bash
oc apply -f deploy/openshift/pipeline/dspa.yaml
oc get dspa kaista-pipelines     # Ready True when the API server and the workflow controller are up
oc apply -f deploy/openshift/pipeline/workspace-pvc.yaml
```

## Seed the object store

The ingest task reads the bucket anonymously, so the credentials never reach a task. The
inputs are public regulatory data.

```bash
oc run kaista-seed --restart=Never --image=python:3.12-slim --command -- sleep 3600
tar cf - -C data/itu-ific-3074 ific3074.zip | oc exec -i kaista-seed -- tar xf - -C /tmp/data
oc exec -i kaista-seed -- tar xf - -C /tmp/data < <(tar cf - -C data \
  frequencies_of_interest.csv taajuusjakotaulukko.json)
# then upload + set the bucket policy (see the runbook in the handoff)
```

## Run it

```bash
oc port-forward svc/ds-pipeline-kaista-pipelines 8443:8443 &
python pipeline.py --submit --host https://127.0.0.1:8443
```

## Measured evidence

Filled from the run on 7.11.2026 (sandbox `janner-1-dev`).

### The pipeline server

```
$ oc get dspa kaista-pipelines
DatabaseAvailable=True ... APIServerReady=True ... WorkflowControllerReady=True ... Ready=True
```

```
$ oc get pods
mariadb-kaista-pipelines-...          1/1  Running
minio-kaista-pipelines-...            1/1  Running
ds-pipeline-kaista-pipelines-...      2/2  Running
ds-pipeline-workflow-controller-...   1/1  Running
ds-pipeline-persistenceagent-...      1/1  Running
```

### The run

```
$ oc get workflow
kaista-ific-triage-zszqk   Succeeded   <duration>
```

### ingest

```
ingest: ific3074.zip -> /workspace/in/ific3074.zip (60837631 B)
ingest: extracted ['ific3074.mdb'] from ific3074.zip
ingest: m4.json -> /workspace/in/m4.json (4359860 B)
ingest: register.csv -> /workspace/in/register.csv (95876 B)
ingest: database /workspace/in/ific3074.mdb (286654464 B), mdb-export present
```

### triage

```
<pending>
```

### metrics

```
<pending>
```

## Limitations

1. **The sandbox has a 3 CPU request quota.** The DS Pipelines components plus the
   InferenceService do not fit at the documented Granite request of 2 CPU. The cluster copy
   of the `granite` InferenceService was lowered to 1 CPU request for the run; the
   repository keeps the documented value. Details below.
2. **The managed MinIO health check fails on this sandbox.** The operator reported
   `ObjectStoreAvailable=False ... context deadline exceeded` while a signed request from a
   pod against the same service returned in 11 ms with the operator's own credentials, and
   the API server created the `mlpipeline` bucket. The DSPA sets
   `objectStore.disableHealthCheck: true` to get past it.
3. **The task pods run as a random OpenShift UID.** The image must `chmod a+rX` the code,
   and the tasks write only to the workspace PVC.
4. **CPU-only prose.** One card takes 40–120 s on the sandbox's CPU vLLM, so the letters
   are generated in a run and never live in the demo.
