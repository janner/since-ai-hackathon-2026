# Architecture

One package, one funnel, six output files. The deterministic path runs offline; the only optional
step is card prose, and a numeric guard stands between the model and the output.

## The pipeline

```mermaid
flowchart LR
  subgraph inputs [Inputs]
    I1["IFIC 3074 .mdb tables"]
    I2["frequencies of interest<br/>(.xlsx / .csv)"]
    I3["M4 allocation table<br/>(.json)"]
    I4["rules/rr21_table21_4.csv"]
  end

  I1 --> ING["app/ingest.py<br/>normalise units, SHA256"]
  I2 --> ING
  I3 --> ING
  ING --> BANDS["app/bands.py<br/>protected bands from the register"]
  BANDS --> G1["G1 band overlap"]
  G1 --> G2["G2 visible from Finland"]
  G2 --> G3["G3 PFD vs Table 21-4"]
  I4 --> PFD["app/pfd.py<br/>slant range, FSPL, limit"]
  PFD --> G3
  G3 -->|"case with a number"| CARD["app/cards.py<br/>card, Markdown, CSV, run log"]
  G2 -->|"survived, no number: queue.md + CSV row"| CARD
  G3 -->|"no number: queue.md + CSV row"| CARD
  CARD --> QUEUE["queue.md, no cap"]
  CARD --> PROSE["app/prose.py<br/>optional, uses app/llm.py"]
  TPL["templates/"] --> PROSE
  PROSE --> GUARD["app/guard.py<br/>every number must exist in the card"]
  GUARD --> OUT["out/<br/>cases.json, cases.md, queue.md,<br/>funnel.json, 3074_results.csv, run.log"]
  OUT --> API["app/main.py<br/>read-only API"]
  API --> UI["app/static/index.html<br/>funnel, queue, selected card"]

  subgraph terr_side [Terrestrial side path]
    T1["two 3076-style extracts<br/>(JSON)"] --> TERR["app/terrestrial.py<br/>diff, 1 000 km filter, P.1546-6"]
    I2 --> TERR
    TERR --> TOUT["out/<br/>terrestrial_findings.json,<br/>terrestrial_trends.csv, TERRESTRIAL.md"]
  end
```

The web UI reads `out/` and nothing else. It runs no LLM call, opens no connection and does no
calculation: without `out/` the page still loads and the API answers 503 with the command to run.

## Modules

| Module | Responsibility |
|---|---|
| `app/config.py` | Static configuration: the seven space bands, the demo slice, the rules version, and the number formatting used in the documents. No channel frequency is hardcoded here; protected bands always come from the register. |
| `app/ingest.py` | Reads the IFIC tables, the Finnish register and the M4 allocation table. Normalises units ("3 520.500 MHz", "300k", "1.5 GHz"), keeps missing values as `None`, and computes the input SHA256. Computes no gates. |
| `app/bands.py` | Derives the protected bands from the register rows that overlap one of the seven space allocations, merges overlapping and near bands, and lists which stations sit on them. |
| `app/pfd.py` | Geometry and the limit: slant range and elevation from GEO longitude or a non-GSO sweep, free-space loss, and the Article 21 Table 21-4 limit read from `rules/rr21_table21_4.csv`. No limit is hardcoded in code. |
| `app/gates.py` | The funnel G1 to G4: band overlap, visibility from Finland, the PFD computation and the class (`exceeds` / `near` / `clear`), plus the reason code for every drop and the decision-order queue. |
| `app/cards.py` | Builds the case card (source rows, calculation, M4 lookup, missing fields, one question), renders the Markdown, the queue, the CSV and the run log, and writes the six output files. |
| `app/pipeline.py` | The CLI: one IFIC package in, the six output files out. The deterministic path never touches the network; the optional prose step calls the endpoint in `LLM_BASE_URL` through `app/llm.py`. |
| `app/prose.py` | Card prose. The LLM drafts it, the guard checks it, the deterministic template in `templates/` is the floor. Also holds the correspondence-letter template and function. |
| `app/guard.py` | Numeric guard: scans the prose for numbers and rejects a sentence that carries a number the card does not have. |
| `app/llm.py` | The single OpenAI-compatible chat call. The endpoint and key come from `.env` (`LLM_BASE_URL`, `LLM_API_KEY`), never from code. The model runs wherever that URL points: the OpenShift AI sandbox in the Red Hat setup, another endpoint, or nowhere at all when the variable is unset. |
| `app/terrestrial.py` | The side path: diffs two 3076-style land-mobile extracts, keeps what is within 1 000 km of Finland and overlaps the register, and computes ITU-R P.1546-6 field strength at four Finnish test points. stdlib only, no network, writes its own three files. |
| `app/main.py` | Read-only FastAPI app: six endpoints (`/`, `/health`, `/api/funnel`, `/api/cases`, `/api/cases/{id}`, `/api/queue`) over the files in `out/`, plus the one page. `KAISTA_OUT` points it at another output directory. |

Data flow goes one way. Nothing in the UI writes, and the deterministic path never reads the network.
The prose model is the one piece that can run outside the laptop: with `LLM_BASE_URL` set to the
served Granite in OpenShift AI, `app/llm.py` sends one chat call per card to the cluster, and the
guard still decides what reaches the output. Unset it and the run is local and offline.

Back to the documentation index in [README.md](../README.md#documentation).
