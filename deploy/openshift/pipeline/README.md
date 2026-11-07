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
oc apply -f deploy/openshift/pipeline/workspace-pvc.yaml
oc get dspa kaista-pipelines   # Ready True once the API server and the workflow controller are up
```

## Seed the object store

The ingest task reads the bucket anonymously, so the credentials never reach a task, and
the inputs are public regulatory data. `scripts/fetch_data.py` fills `data/` first.

```bash
oc run kaista-seed --restart=Never --image=python:3.12-slim --command -- sleep 3600
tar cf - -C data/itu-ific-3074 ific3074.zip | oc exec -i kaista-seed -- tar xf - -C /tmp/data
tar cf - -C data frequencies_of_interest.csv taajuusjakotaulukko.json \
  | oc exec -i kaista-seed -- tar xf - -C /tmp/data
# upload the three objects into the `ific` bucket and set its anonymous-read policy
# (bucket + policy, see the seeder used for the measured run)
```

## Run it

```bash
oc port-forward svc/ds-pipeline-kaista-pipelines 8443:8443 &
python pipeline.py --submit --host https://127.0.0.1:8443
```

## Measured evidence (7.11.2026, sandbox `janner-1-dev`)

### The pipeline server

```
$ oc get dspa kaista-pipelines
DatabaseAvailable=True   ObjectStoreAvailable=True   APIServerReady=True
PersistenceAgentReady=True   ScheduledWorkflowReady=True   WorkflowControllerReady=True
```

```
$ oc get pods
ds-pipeline-kaista-pipelines-596c4fcd7f-cth6n                     2/2   Running
ds-pipeline-workflow-controller-kaista-pipelines-ff8666b479kgsh   1/1   Running
ds-pipeline-persistenceagent-kaista-pipelines-68d7dbffc6-w7k5m    1/1   Running
ds-pipeline-scheduledworkflow-kaista-pipelines-7666b4b6bd-gkzhj   1/1   Running
ds-pipeline-metadata-grpc-kaista-pipelines-b6bb99cb9cb6-lsgz8     1/1   Running
mariadb-kaista-pipelines-7cf645bb6f-xvcqh                          1/1   Running
minio-kaista-pipelines-5d88d947dc-kdnr7                            1/1   Running
```

### The run

```
$ oc get workflow
NAME                       STATUS      AGE
kaista-ific-triage-zszqk   Succeeded   49m
```

Run id `febefa66-4181-43c4-92b5-78235f1f1c23`, submitted through the DSPA API server.

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
triage: database /workspace/in/ific3074.mdb
triage: model endpoint http://granite-predictor.janner-1-dev.svc.cluster.local/v1
196 notices → G1 41 → G2 19 → G3 18 + 1 cannot decide
exceeds 9, near 5, clear 4, 15 in the queue (1 groups, 2 bands, 7.42 s)
wrote /workspace/out/cases.json, cases.md, queue.md, funnel.json, 3074_results.csv, run.log, letters/
```

The funnel reproduces the laptop run of the same commit exactly (196 → 41 → 19 → 18 + 1); the
deterministic part took 7.42 s in the cluster. The current code's slice is 196 → 41 → 21 → 20 + 1
after the fail-closed and full-table fixes, so this run is dated evidence, not the current count.

### metrics

```
metrics: 196 notices → G1 41 → G2 19 → G3 18 + 1 cannot decide
metrics: exceeds 9, near 5, clear 4, 15 in the queue
metrics: prose sources {'template': 16, 'llm': 2}
metrics: guard rejected 0/2 drafts, 0%
metrics: wrote /workspace/out/metrics.json
```

**This is where the run fell short of the laptop.** Only 2 of 18 cards kept model prose;
16 fell back to the deterministic template, so the guard saw 2 drafts and rejected none.
The cause is throughput, not correctness: the sandbox Granite request was lowered to
1 CPU for this run (see limitation 1), `app/llm.py` gives up after 120 s, and 11 of the
18 calls had reached the model by the time the task ended. The funnel, the guard and the
metrics path are exercised end to end; the prose step needs the model at its documented
size, or a higher client timeout, to be more than a sample.

## Limitations

1. **The sandbox has a 3 CPU request quota.** The DS Pipelines components plus the
   InferenceService do not fit at the documented Granite request of 2 CPU (that pair needs
   ~2.96 of the 3 CPUs, which leaves no room for the pipeline's own components). The cluster
   copy of the `granite` InferenceService was lowered to 1 CPU request for this run; the
   repository keeps the documented value in `deploy/openshift/inferenceservice.yaml`. Raise
   it back and the prose step recovers its documented speed.
2. **The managed MinIO health check fails on this sandbox.** The operator reported
   `ObjectStoreAvailable=False ... context deadline exceeded` while a SigV4-signed request
   from a pod against the same service, with the operator's own credentials, returned in
   11 ms, and the API server then created the `mlpipeline` bucket. The DSPA sets
   `objectStore.disableHealthCheck: true` to get past the check. The object store itself is
   healthy.
3. **The task pods run as a random OpenShift UID.** The image must `chmod a+rX` the code,
   and the tasks write only to the workspace PVC or `/tmp`.
4. **The KFP launcher waits on the model.** One card takes 40–120 s on a CPU vLLM, so the
   letters are generated in a run and never in the live demo. The `triage` task carries a
   5400 s deadline for the same reason.
5. **KFP caches tasks by default.** With caching on, a second run of the same pipeline
   skipped `ingest` and inherited the first package's workspace. Every task sets
   `set_caching_options(False)`.
