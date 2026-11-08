# Feedback form (Kaista demo)

The form is a small usability test, not just a feedback form. The customer does the tasks
themselves with the demo open. Do not explain the demo beforehand. The form guides; you sit next to
them and write down what you observe.

The customer writes the answers straight into the form. The answers are stored in Hermes' home
directory, not in the repository and not with a third party.

## Tasks

1. Background: how the work is done today, who fetches the IFIC and how long it takes.
2. Automatic fetch: which IFIC was fetched last and how many notices it held.
3. Case: why the top case in the queue is on the list and what information it is missing.
4. Next step: what is done about the case and where on the card that is visible.
5. Undecidables: find two notices the tool cannot decide.
6. Calculation and trust: PFD, limit and margin; trust 1-5.

At the end: usefulness, understanding, willingness to pilot, UI language, "what the tool does not
do", free feedback and contact details. The required fields are "Task 2: case" and "Task 3: next
step"; the rest are optional.

## Address

`https://hermesagent.hamster-herring.ts.net:8452`

Tailnet only. Do not share the address outside the tailnet.

## Start

```bash
cd ~/since-ai-hackathon-2026
.venv/bin/python scripts/feedback_server.py
```

In a second terminal:

```bash
sudo tailscale serve --bg --https=8452 http://127.0.0.1:8322
```

Check:

```bash
tailscale serve status
curl -s http://127.0.0.1:8322/health
```

## Responses

- `~/.hermes/hackathon-feedback/latest.md` — the latest response, ready to read.
- `~/.hermes/hackathon-feedback/feedback.md` — every response.
- `~/.hermes/hackathon-feedback/feedback.jsonl` — the same, machine-readable.
- `~/.hermes/hackathon-feedback/latest.json` — the latest as JSON.

Hermes reads a response by asking, for example:

```text
read ~/.hermes/hackathon-feedback/latest.md
```

Every response also sends a best-effort message to the Matrix home channel. If Matrix does not
answer, the response is still in the file.

## Test run 7 Nov 2026

Two testers: a specialist (P) and a Traficom senior specialist (O). Both did the tasks on their own.
The raw answers are outside the repository: `~/.hermes/hackathon-feedback/feedback.md`.

- Usefulness 4/5 for both, willingness to pilot yes for both.
- Task 1 succeeded: IFIC 3075, 129 notices.
- Trust in the number: P 2/5, O 4/5. P wants more precise references before trusting it.
- P: the top bar does not show whether the package is Space or Terrestrial.
- O: the card lacks the publication type (API, CRC, CRD, Part II) and the stage the case is at.
  O weights cases in the planning stage.
- Both: the undecidables cannot be found as a list, only as a count. The worst-case location in
  Finland is missing.

Changes made on 7 Nov on the basis of these: the search text names the document series (space), the
card shows the regulatory stage with the ITU abbreviation, the publication type and the BR IFIC
session (API/A, API/B, CR/C, CR/D, CR/E, RES4, RES49; a notice without a `pub_ssn` row is Part II-S),
the coordinates of the protecting station and the worst-case point, the funnel lists the undecidable
notices with their reasons and the values they would need, the calculation expands to the formula,
the Table 21-4 row (A, K, reference band, page) and the input values, the card lists earlier
complaints for the same administration or network with their reply notes, and the card text is in
English.

Open: the CEPT/ECC comparison. Per Q2, Table 21-4 is the primary limit and CEPT is not a separate
limit in this build; the card says so on its criterion line. P's reference precision is now at the
level of the Table 21-4 row and the BR IFIC session, O's CRD/Part II detail is in the `pub_ssn`
table, and the earlier complaints are in the card's list.

## Test

```bash
curl -s -X POST http://127.0.0.1:8322/api/feedback \
  --data-urlencode 'feedback=Test feedback' \
  --data-urlencode 'useful=5'
```

Delete the test response from the file before a customer session.
