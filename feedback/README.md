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

## Testaus 7.11.2026

Kaksi testaajaa: asiantuntija (P) ja Traficomin erityisasiantuntija (O). Molemmat tekivät
tehtävät itsenäisesti. Raakavastaukset ovat repon ulkopuolella:
`~/.hermes/hackathon-feedback/feedback.md`.

- Hyödyllisyys 4/5 molemmilla, pilottihalukkuus kyllä molemmilla.
- Tehtävä 1 onnistui: IFIC 3075, 129 ilmoitusta.
- Luottamus lukuun: P 2/5, O 4/5. P haluaa tarkemmat viittaukset ennen luottamista.
- P: yläpalkista ei näe, onko paketti Space vai Terrestrial.
- O: kortista puuttuu julkaisun tyyppi (API, CRC, CRD, Part II) ja tieto siitä, missä
  vaiheessa tapaus on. O painottaa suunnitteluvaiheessa olevia tapauksia.
- Molemmat: ei-päätettäviä ei löydy listana, vain lukuna. Worst case -sijainti Suomessa puuttuu.

Näiden pohjalta 7.11. tehdyt muutokset: hakuteksti kertoo dokumenttisarjan (space), kortti
näyttää sääntelyvaiheen ITU-lyhenteellä, julkaisutyypin ja BR IFIC -session (API/A, API/B,
CR/C, CR/D, CR/E, RES4, RES49; ilmoitus ilman pub_ssn-riviä on Part II-S), suojaavan aseman
koordinaatit ja worst case -pisteen, suppilo listaa ei-päätettävät ilmoitukset syineen ja
tarvittavine arvoineen, laskelman avaus näyttää kaavan, Table 21-4 -rivin (A, K,
referenssikaista, sivu) ja lähtötiedot, kortti listaa aiemmat valitukset samalle hallinnolle
tai verkolle vastausmuistiinpanoineen, ja kortin teksti on englanniksi.

Avoinna: CEPT/ECC-vertailu. Q2:n mukaan Table 21-4 on ensisijainen raja eikä CEPT ole erillinen
raja tässä buildissa; kortti sanoo tämän criterion-rivillä. P:n viittaustarkkuus on nyt
Table 21-4 -rivin ja BR IFIC -session tasolla, O:n CRD/Part II -tarkennus on pub_ssn-taulussa,
ja aiempien valitusten historia on kortin listassa.

## Testi

```bash
curl -s -X POST http://127.0.0.1:8322/api/feedback \
  --data-urlencode 'feedback=Testipalaute' \
  --data-urlencode 'useful=5'
```

Testipalaute kannattaa poistaa tiedostosta ennen asiakastilaisuutta.
