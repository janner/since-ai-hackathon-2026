"""The IFIC triage run as an OpenShift AI Data Science Pipeline.

Three container tasks on the `kaista-pipeline` image share the `kaista-workspace` PVC:

    ingest    the IFIC package and the two side inputs, copied out of the object store
    triage    the deterministic funnel (gates -> cards), the served model's prose and the guard
    metrics   the funnel numbers and the guard's rejection share, read back from the output

Compile only:

    python pipeline.py kaista-ific-triage.yaml

Compile and submit to the Data Science Pipelines API server:

    kubectl port-forward svc/ds-pipeline-kaista-pipelines 8443:8443 &
    python pipeline.py --submit --host https://127.0.0.1:8443
"""

# No `from __future__ import annotations` here: KFP reads the annotations at compile
# time, and PEP 563 turns them into strings, which KFP then mistakes for artifact types.

import argparse
import subprocess

from kfp import compiler, dsl, kubernetes

IMAGE = "image-registry.openshift-image-registry.svc:5000/janner-1-dev/kaista-pipeline:latest"
PVC = "kaista-workspace"
MOUNT = "/workspace"

# In-cluster addresses: the pipeline never leaves the cluster.
S3_BASE = "http://minio-kaista-pipelines.janner-1-dev.svc.cluster.local:9000"
S3_BUCKET = "ific"
LLM_BASE = "http://granite-predictor.janner-1-dev.svc.cluster.local/v1"
LLM_MODEL = "granite"

# The prose step is one chat call per card; the slice is 18 cards at up to ~120 s each.
TRIAGE_TIMEOUT_S = 5400


def _stage(stage: str, env: dict[str, str]) -> dsl.ContainerSpec:
    # Env goes through the shell: this kfp-kubernetes has no literal env setter for
    # container components, and the values are fixed for the cluster we deploy into.
    prefix = " ".join(f"{key}={value}" for key, value in env.items())
    return dsl.ContainerSpec(
        image=IMAGE,
        command=["sh", "-c"],
        args=[f"{prefix} python -m pipeline_stages {stage}"],
    )


@dsl.container_component
def ingest():
    return _stage("ingest", {"KAISTA_S3_BASE": S3_BASE, "KAISTA_S3_BUCKET": S3_BUCKET})


@dsl.container_component
def triage():
    return _stage("triage", {"LLM_BASE_URL": LLM_BASE, "LLM_MODEL": LLM_MODEL})


@dsl.container_component
def metrics():
    return _stage("metrics", {})


@dsl.pipeline(
    name="kaista-ific-triage",
    description="One IFIC package: ingest, funnel, served-model prose, numeric guard, metrics.",
)
def kaista_ific_triage():
    # Caching off: every run ingests a fresh IFIC package, so a cached task would
    # hand the next run the previous package's workspace.
    ingest_task = ingest()
    ingest_task.set_caching_options(False)
    kubernetes.mount_pvc(ingest_task, pvc_name=PVC, mount_path=MOUNT)

    triage_task = triage().after(ingest_task)
    triage_task.set_caching_options(False)
    kubernetes.mount_pvc(triage_task, pvc_name=PVC, mount_path=MOUNT)
    kubernetes.set_timeout(triage_task, TRIAGE_TIMEOUT_S)

    metrics_task = metrics().after(triage_task)
    metrics_task.set_caching_options(False)
    kubernetes.mount_pvc(metrics_task, pvc_name=PVC, mount_path=MOUNT)


def submit(host: str, experiment: str, token: str | None) -> str:
    import kfp

    token = (
        token
        or subprocess.run(
            ["oc", "whoami", "-t"], capture_output=True, text=True, check=True
        ).stdout.strip()
    )
    client = kfp.Client(host=host, existing_token=token, verify_ssl=False)
    run = client.create_run_from_pipeline_func(
        kaista_ific_triage, arguments={}, experiment_name=experiment
    )
    return run.run_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", nargs="?", default="kaista-ific-triage.yaml")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--host", default="https://127.0.0.1:8443")
    parser.add_argument("--experiment", default="kaista-pipelines")
    parser.add_argument("--token", default=None)
    args = parser.parse_args(argv)

    compiler.Compiler().compile(kaista_ific_triage, args.out)
    print(f"compiled {args.out}")
    if args.submit:
        print(f"run id {submit(args.host, args.experiment, args.token)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
