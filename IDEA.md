# Traficom-hanke: päätelmät ja tuotteen rajaus

Päivitetty 6.11.2026. Perustuu: Laatu 2015, EU 2025/2425, CEPT Report 88, FCC C-band, NTIA/CSMAC CBRS, NASEM 2015.

## 1. Mitä Laatu 2015 opettaa

- Täsmälleen sama kaista ja sama viranomainen. Työ tehtiin Viestintäviraston taajuushallinnolle. Ei siis hypoteettinen skenaario.
- Menetelmä on valmis: skenaariot, etenemismalli, ITU:n suojelukriteerit, antennikuviot, tehot, suojakaistat ja liitteiden parametrit. Fysiikkaa ei tarvitse keksiä uudelleen.
- Johtopäätös on prosessi, ei teknologia: sopimus tai tapauskohtainen koordinointi. Juuri sitä manuaalista työtä haaste pyytää automatisoimaan.
- Työ on staattinen ja vuodelta 2015. Se antaa metodin ja historiallisen kontekstin, ei nykytilaa. Nykytila pitää laskea uudelleen EU 2025/2425:n ja Traficomin 2026 sääntöjen mukaan.
- Työn raja: muutama skenaario, ei työkalua. Meidän etu: monta kandidaattitapausta, nopea triage ja selitys.

## 2. Mitä muiden maiden prosessit opettavat

- Koko kaistaa ei avata kerralla. Yläpää jää viimeiseksi: USA 4,16–4,2, Japani 4,1–4,2, Kanada 3,9–4,2, Australia 4,0–4,2. Suomen 4,05–4,2 on vaikein kohta.
- Kolme mallia: siirto (USA C-band), dynaaminen jako (CBRS), paikallinen matala/keskiteho tapauskohtaisesti (EU 3,8–4,2). Suomi valitsi kolmannen.
- Tapauskohtaisuus on virallinen johtopäätös: EU 2025/2425, CEPT Report 88 ja Laatu 2015 sanovat saman. Ei siis merkki huonosta suunnittelusta, vaan lopputulos.
- Data on pullonkaula: EU olettaa, että tukiasemien, kiinteiden linkkien ja FSS-maa-asemien sijainnit tiedetään. CBRS:ssä ULS-data oli puutteellista ja epätarkkaa; liikkuvat maa-asemat vaativat paikan päällä koordinointia.
- Ylisuojelu on kallista: CBRS:n konservatiiviset etenemismallit, Whisper Zone -vyöhykkeet ja 24 tunnin aggregate interference -koordinointi. AI voi vähentää sitä vain jäljitettävällä todisteketjulla.
- Älä rakenna SAS:ää. CBRS:n SAS on monimutkainen, kallis ja hidas. Rakenna tapauslöytäjä ja todisteketju.
- Viereiset kaistat: radio altimetrit 4,2–4,4, C-bandin ja CBRS:n naapurihäiriö, TDD-synkronointi. Mukaan sääntögraafiin.
- NASEM 2015: C-band on myös tutkimuskäyttöä. Suojelu pitää perustaa mitattuun RFI-ympäristöön ja instrumenttikohtaisiin mittareihin.

## 3. Johtopäätökset tuotteelle

1. Rajaus: 3,8–4,2 GHz paikalliset matala- ja keskitehoiset verkot, painopiste 4,05–4,2 GHz:ssä ja maa-asemien suojelussa. Ei kansallista 5G-huutokauppaa.
2. Ydinvirta: ITU-filing + kansallinen sääntö + maa-asemarekisteri + tukiasemaehdotus → suojeluetäisyys/PFD → puuttuvan datan liputus → tapauksen rankkaus → todisteketju → ihminen päättää.
3. Ulostulo: tapauskortti. Osapuolet, kaista, sovellettu sääntö, laskenta, epävarmuus, puuttuva data, ehdotettu seuraava askel ja lähteet.
4. Demo: yksi todellinen tai havainnollistava tapaus lähellä rekisteröityä maa-asemaa tai rajaa. Näytä sääntö, laskenta ja ihmisen päätös. Toinen tapaus voi olla väärä hälytys, jotta rankkaus näkyy.
5. Pitch: "Laatu 2015 ja EU 2025/2425 päätyvät molemmat tapauskohtaiseen koordinointiin. Me automatisoimme tapauskohtaisen työn, emme päätöstä."
6. Älä lupaa: kansallista 5G-verkkoa, reaaliaikaista SAS:ää, automaattista lupapäätöstä tai täydellistä datapohjaa.

## 4. Demon käsikirjoitus (3 min)

- 0:00–0:30: Ongelma. 3,8–4,2 GHz avataan paikallisverkoille. Maa-asemat ja kiinteät linkit pitää suojella tapauskohtaisesti.
- 0:30–1:00: Laatu 2015. Sama kaista, sama viranomainen, johtopäätös tapauskohtainen koordinointi. Yksitoista vuotta myöhemmin työ on yhä manuaalista.
- 1:00–2:00: Demo. Syötä tukiasemaehdotus, maa-asema ja säännöt. Työkalu laskee, näyttää lähteet, liputtaa puuttuvan datan ja rankkaa tapauksen.
- 2:00–2:30: Ihmisen päätös. Hyväksy, pyydä lisätietoja tai hylkää. Työkalu ei päätä.
- 2:30–3:00: Skaalautuvuus. Sama ketju kaikille tapauksille; uusi sääntö tai filing päivittyy graafiin.

## 5. Mitä pitää selvittää ennen perjantaita

- Onko maa-asemarekisteri julkinen? Mistä?
- Mikä on Traficomin 4,05–4,2 GHz:n päätös 2.11.2026 tarkalleen?
- Mitä dataa haaste tarjoaa? Filingit, säännöt, tapaukset?
- Kumpi kaista on varsinainen kohde: 3,8–4,2 vai 4,05–4,2?
- Onko esimerkkitapaus saatavilla vai rakennetaanko havainnollistava?

## 6. Riskit

- Data puuttuu: käytä julkista ja havainnollistavaa dataa, merkitse oletukset.
- Vuoden 2015 parametrit ovat vanhentuneet: käytä niitä vain metodina, laske nykysäännöillä.
- AI ei saa luvata liikaa: näytä epävarmuus ja lähteet; älä esitä "turvallinen/vaarallinen" -tuomiota.
- Aika: 34 h. Yksi tapaus, yksi kortti, yksi selitys. Ei koko Suomea.

## 7. Lähteet

- Laatu 2015: https://lutpub.lut.fi/handle/10024/117929
- EU 2025/2425: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025D2425
- CEPT Report 88 / ECC Decision (24)01: https://docdb.cept.org/download/4571
- FCC 26-46: https://docs.fcc.gov/public/attachments/FCC-26-46A1.pdf
- NTIA/CSMAC CBRS 2023: https://www.ntia.gov/sites/default/files/2023-12/cbrs_subcommittee_final_report.pdf
- NASEM 2015: https://nap.nationalacademies.org/read/21729/chapter/2
- Koko muistio: ~/.hermes/reference/taajuusalue-kansainvalinen.md

## 8. Hyödyllisimmät akateemiset lähteet

Laatu 2015 on ainoa suora osuma. Muut ovat metodeja, arkkitehtuureja tai varoituksia. Näistä on oikeasti hyötyä 34 tunnissa:

| Lähde | Miksi | Mitä lukea |
|---|---|---|
| Laatu 2015 | Täsmälleen kaista, suomalainen sääntelykonteksti, valmis laskentamenetelmä | Skenaariot 1–3, etenemismalli, suojelukriteerit, liite 4 |
| Hafez 2020 | ITU-R-yhteensopivuustutkimuksen rakenne: aggregoitu häiriö, suojelukriteerit, erotusetäisyys, suojakaista, OOBE | Skenaario, suojelukriteerit, johtopäätökset |
| Marttinen 2010 | Maa-aseman linkkibudjetti ja sijoituspaikka; ITU:n suositukset, C/Ku/Ka | Linkkibudjetti, antennit, sadevaimennus |
| Kalliovaara 2017 | Incumbentin käyttöaste ja suojelukriteerit käytännössä; miksi mitattu data voittaa teoreettisen | Tiivistelmä ja suojelukriteerit |
| Hariharakrishnan 2026 | Graafipohjainen RAG sääntelydokumenteille; todisteketju ja hallusinaation hallinta | Arkkitehtuuri ja retrieval-malli |
| Rana 2026 | LLM muuntaa sääntöjä koneellisesti tarkistettaviksi (RDF/SHACL) | Menetelmä ja esimerkki |
| Gustafsson 2026 | AI + SDR -monitorointi; CNN–LSTM ja synteettinen koulutusdata | Malli ja datan generointi |
| Huang 2016 | SAS–CBSD-arkkitehtuuri; samalla varoitus: älä rakenna SAS:ää | Rajapinta ja johtopäätökset |

Näitä ei kannata lukea kokonaan: Mustonen 2017, Virtanen 2021, Taskinen 2015, Piiroinen 2019, Dikmese 2015, Porko 2011, Mattsson 2025, Rantanen 2025, Aalto 2023 ja Alemu 2012. Ne ovat taustaa tai eri ongelmaa.

Varsinaiset laskentasäännöt ovat ITU-R P.452, P.2108, S.465 ja F.1336. Laatu ja Hafez käyttävät niitä. SEAMCAT on valmis työkalu samaan laskentaan; sitä ei kannata rakentaa uudelleen. Meidän kerros on filingit, säännöt, tapaukset ja todisteketju.
