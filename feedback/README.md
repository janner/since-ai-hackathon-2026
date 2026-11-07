# Palaute­lomake (Kaista-demo)

Lomake on pieni käyttäjätesti, ei pelkkä palautelomake. Asiakas tekee tehtävät
itse demo auki. Älä selitä demoa etukäteen. Lomake ohjaa; sinä istut vieressä ja
kirjaat havainnot.

Asiakas kirjoittaa vastaukset suoraan lomakkeeseen. Vastaukset tallentuvat
Hermeksen kotihakemistoon, eivät repoon eivätkä kolmannelle osapuolelle.

## Tehtävät

1. Tausta: miten työ tehdään tänään, kuka hakee IFIC:n ja kuinka kauan se kestää.
2. Automaattihaku: mikä IFIC on viimeksi haettu ja montako ilmoitusta siinä oli.
3. Tapaus: miksi jonon ylin tapaus on listalla ja mitä tietoa siitä puuttuu.
4. Seuraava askel: mitä tapaukselle tehdään ja mistä kortin kohdasta sen näkee.
5. Ei-päätettävät: etsi kaksi ilmoitusta, joita työkalu ei voi päättää.
6. Laskelma ja luottamus: PFD, raja ja marginaali; luottamus 1–5.

Lopuksi: hyödyllisyys, ymmärrys, pilottihalukkuus, UI-kieli, "mitä työkalu ei
tee", vapaa palaute ja yhteystieto. Lomakkeen pakolliset kentät ovat "Tehtävä 2:
tapaus" ja "Tehtävä 3: seuraava askel"; muut ovat valinnaisia.

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
