# Pipeline task image for the IFIC triage Data Science Pipeline.
# The app is stdlib-only for the deterministic path (fastapi is only the web UI),
# so the image carries the code and nothing else.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/kaista

WORKDIR /opt/kaista
COPY app/ app/
COPY rules/ rules/
COPY templates/ templates/
COPY deploy/openshift/pipeline/pipeline_stages.py pipeline_stages.py
# mdbtools: the deterministic core reads the BR IFIC Access database with mdb-export.
RUN apt-get update \
    && apt-get install -y --no-install-recommends mdbtools \
    && rm -rf /var/lib/apt/lists/*
# The build context keeps the repo's 0600 modes; the pod runs as a random
# OpenShift UID, so make the code world-readable and the dirs traversable.
RUN chmod -R a+rX /opt/kaista
