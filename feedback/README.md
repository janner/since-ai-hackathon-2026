# Palaute­lomake (Kaista-demo)

Asiakas kirjoittaa palautteen suoraan lomakkeeseen. Palautteet tallentuvat
Hermeksen kotihakemistoon, eivät repoon eivätkä kolmannelle osapuolelle.

## Osoite

`https://hermesagent.hamster-herring.ts.net:8452`

Vain tailnetissä. Älä jaa osoitetta tailnetin ulkopuolelle.

## Käynnistys

```bash
cd ~/since-ai-hackathon-2026
.venv/bin/python scripts/feedback_server.py
```

Toisessa terminaalissa:

```bash
sudo tailscale serve --bg --https=8452 http://127.0.0.1:8322
```

Tarkista:

```bash
tailscale serve status
curl -s http://127.0.0.1:8322/health
```

## Palautteet

- `~/.hermes/hackathon-feedback/latest.md` — viimeisin palaute luettavana.
- `~/.hermes/hackathon-feedback/feedback.md` — kaikki palautteet.
- `~/.hermes/hackathon-feedback/feedback.jsonl` — sama koneellisesti.
- `~/.hermes/hackathon-feedback/latest.json` — viimeisin JSON.

Hermes lukee palautteen pyytämällä esimerkiksi:

```text
lue ~/.hermes/hackathon-feedback/latest.md
```

Jokaisesta palautteesta lähtee myös best-effort-viesti Matrixin kotikanavalle.
Jos Matrix ei vastaa, palaute säilyy silti tiedostossa.

## Testi

```bash
curl -s -X POST http://127.0.0.1:8322/api/feedback \
  --data-urlencode 'feedback=Testipalaute' \
  --data-urlencode 'useful=5'
```

Testipalaute kannattaa poistaa tiedostosta ennen asiakastilaisuutta.
