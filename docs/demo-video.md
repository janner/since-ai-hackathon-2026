# Demo video: two-minute script

The video the submission links to. The organiser guide's structure: problem 0–15 s,
solution 15–35 s, live demo 35–95 s, business impact 95–120 s. English narration,
English captions. Narration is 272 words, about 1:49 at 150 words per minute, so
transitions and the end card fit inside two minutes. Each narration line below is
one caption line.

The three-minute stage script is `docs/demo.md` §10. This is the shorter cut: the
terrestrial pass and the draft letter stay off the video.

## The script

| Time | On screen | Narration (spoken and captioned) |
|---|---|---|
| 0:00 | The raw rows of the challenge package (the `data/` export or the challenge workbook), slow scroll | Every two weeks the ITU publishes a BR IFIC: new satellite filings. |
| 0:05 | same, still scrolling | This one has 196 notices and 95,865 frequency rows. |
| 0:10 | same, end of scroll | A specialist at the regulator reads all of it by hand, to find the few that matter for Finnish radio use. |
| 0:15 | Browser on `http://localhost:8000`, the funnel panel | Kaista does that first pass. |
| 0:20 | the funnel | It keeps the notices that overlap a band in the run's scope and can be seen from Finland, then computes their power flux density against the ITU Radio Regulations, and checks the band against Finland's own allocation. |
| 0:28 | the funnel, hover the last stage | Every number is computed from the real ITU data. Nothing is simulated. |
| 0:33 | top bar, the automatic-check panel | And the tool finds the next package by itself. |
| 0:38 | the status line: "New IFIC 3075 fetched and processed 7 Nov 2026, 09:43 · 129 notices." Do not click "Check now", see below | This morning the tool asked ITU for the next package and processed it: 129 new notices. |
| 0:45 | the funnel of the 3075 run | Of the 129, 19 overlap a band in the scope. Nine can be seen from Finland. |
| 0:52 | same funnel | Seven get a computed number. Two cannot be decided, and the tool says so. |
| 0:58 | queue, open card `3075-108501259` | First case: APSTAR-92E, 3,440 to 3,480 megahertz. |
| 1:05 | the card | Its power flux density is 0.43 decibels over the Article 21, Table 21-4 limit, and the band is not a satellite allocation in Finland at all. |
| 1:12 | "Show calculation" | Open the calculation: every input is on screen. |
| 1:18 | the calculation block | Max power density, 26 decibels of beam gain, 41,222 kilometres of path, 163 decibels of free-space loss, against the limit row. |
| 1:27 | the card's `Coverage` and `Missing` lines | The beam data is empty in this package, so the worst case is assumed: the peak gain is aimed at the territory edge. Nothing is listed as missing. |
| 1:33 | the drafted question | It drafts the question for the other administration: confirm the worst-case PFD on Finnish territory. The tool does not guess. |
| 1:40 | `runs/3075/queue.md` rows 8–9 (the two refused) or `out/cases.md` | On the challenge package the same pass turns 196 notices and 95,865 rows into 20 case cards, with the numbers already done. |
| 1:48 | same | Nothing is dropped silently: every notice keeps a stage and a reason. |
| 1:52 | same | The specialist decides. The tool does the reading, and it repeats for free every two weeks. |
| 1:58 | end card: **Kaista** — "From 95,865 frequency rows to every case that needs a human decision." | Kaista: from 95,865 frequency rows to every case that needs a human decision. |

Block word counts: problem 42, solution 48, live demo 123, impact 59.

## Recording notes

- **Do not click "Check now".** On the submission tree it would fetch IFIC 3076 and move
  `runs/latest`. The demo reads the status line the 3075 run left. If a recording of the real
  7 Nov 09:43 fetch exists, splicing it in over 0:38–0:45 is stronger than the status line.
- **Optional Red Hat line**, swap in at 0:28 if the OpenShift award is worth the time (takes
  the video to about 2:03, so trim one live-demo line with it): "The card summary is drafted
  by a language model in an OpenShift AI sandbox, but the model never supplies a number."
- **Numbers are honest as they stand.** Both runs are on record: 3075 is the automatic path
  (`runs/3075/`), 3074 is the accuracy material. The video says which run it shows.
- OBS for screen and voice, captions in CapCut or as YouTube subtitles. Localhost is the
  demo environment; the guide says that is enough.

## Before submitting

- [ ] Someone outside the team watches it once and says back what the tool does.
- [ ] The exported video is watched end to end before it is uploaded.
- [ ] The YouTube link (public or unlisted) is pasted into the `Demo video` field of
      `SUBMISSION.md`. Deadline Sun 8 Nov 10:00 EET, submit by 09:00.
