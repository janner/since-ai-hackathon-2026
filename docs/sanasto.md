# Glossary

The term itself is in English, because the data and the letters are in English. The explanation and
the source are here for each one.

| Term | Explanation | Source |
|---|---|---|
| **BR IFIC** | The frequency information circular the ITU Radiocommunication Bureau (BR) publishes every two weeks; the tool reads its new satellite network notices. | ITU BR IFIC (Space Services), Preface |
| **API/A and CR/C** | Notice forms: API/A is advance publication (Art. 9.1) and CR/C is a coordination request (Art. 9.6); both say whether another administration can still influence the notice. | ITU RR 2024, Vol 1, No. 9.1 and 9.6 |
| **IFIC number** | The running number of the circular (for example 3074), which identifies the package and appears in the card's identifier. | ITU BR IFIC |
| **M4** | Traficom's radio frequency regulation 4 AG/2026M; the frequency allocation table in its annex says which services the band is allocated to in Finland. | Traficom M4 (4 AG/2026M), annex p. 147-148; `data/taajuusjakotaulukko.json` |
| **M15** | Traficom's radio frequency regulation 15 AV/2025M, which the brief mentions as a cross-check but the tool does not use. | Traficom M15 (15 AV/2025M) |
| **PFD** | Power flux density: the power a satellite transmits per unit area, which the tool compares with the ITU limit. | ITU RR 2024, Art. 21; `app/pfd.py` |
| **dB(W/m²/Hz)** | The unit of PFD: power in decibels per square metre and per hertz. | ITU RR 2024, Art. 21 |
| **margin** | The difference between the computed PFD and the limit in decibels; a positive margin means the computed upper bound is over the limit. | `cases.json`, field `calculation.margin_db` |
| **upper bound** | The tool's number is a screening upper bound, not a claim of interference: it combines the highest power, the highest beam gain and free-space loss. | `README.md`, "Known limitations" 1 |
| **GSO and NGSO** | A geostationary (GSO) satellite stays at a fixed longitude, while a non-geostationary (NGSO) one moves, so the tool computes a sweep for it. | ITU RR 2024, Vol 1 (Definitions); `app/gates.py` |
| **MIFR** | Master International Frequency Register, the ITU register of recorded frequency assignments; a No. 11.2 notice is already in it, so it can no longer be influenced. | ITU RR 2024, Vol 1, No. 11.2 |
| **No. 9.1 / 9.6 / 11.2** | The Radio Regulations provisions that set a notice's stage: 9.1 advance publication and 9.6 coordination request (both can still be influenced), 11.2 MIFR recording (no longer). | ITU RR 2024, Vol 1 |
