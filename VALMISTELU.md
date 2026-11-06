# Since AI Hackathon 2026: valmistelu

Kaikki 15 haastebriifiä: HAASTEET.md.

Lähteet: sinceai.ai/hackathon, /hackathon-2026/guide, /guide/builders, /guide/resources, /faq, /projects. Luettu 27.10.2026, sivut päivitetty 26.10.2026.

## Perustiedot

- 6.–8.11.2026, Turku (Kupittaa). 48 h. Ilmainen. Kieli englanti. Paikan päällä, ei etäosallistumista.
- 15 yrityshaastetta, kaikissa sama rahapalkinto. Palkintopotti yhteensä 50 000 €.
- Tiimi 1–5 henkeä. Yksin saa osallistua, mutta tekninen tiimi tarkistaa yhden hengen tiimin rekisteröinnissä.
- Haasteyritykset: Valmet, Bayer, Turku Energia, Apetit, Takomo Golf, Forcit Group (vaatii NDA:n), Elisa, Meyer Turku, Traficom, Lindström, Business Turku, DNA, Fonecta, Europress. Yksi yritys julkistetaan vielä.
- Palautus tehdään sinceai.appissa (ei Devpostissa) su 8.11. klo 10.00. Takaraja on ehdoton.
- Tekoälytyökalut ovat sallittuja ja suositeltuja (Claude Code mainitaan nimeltä). Lomakkeessa pitää kertoa käytetyt GenAI-työkalut. Ennen tapahtumaa tehty koodi pidetään erillään tapahtumassa tehdystä.

## Aikataulu

| Milloin | Mitä |
|---|---|
| **pe 30.10.** | Takaraja: CSC/LUMI-rekisteröinti (valinnainen) ja ateriailmoittautuminen (Meal RSVP) sinceai.appissa |
| to 5.11. klo 15 | Haasteiden tiivistelmät aukeavat sinceai.appissa. Tiimi sopii vähintään 3 haastetta |
| pe 6.11. klo 15 | **Haasteiden tarkemmat tiedot julki** (Discord 6.11.: 2 h ennen avajaisia). Haastekohtaiset tukikanavat auki, jos edustaja paikalla |
| pe 6.11. klo 15 | Ilmoittautuminen EduCityssä (Joukahaisenkatu 7). Jokainen jäsen paikan päällä |
| pe 15.00–17.30 | Tiiminvetäjä merkitsee tiimin valmiiksi ja valitsee haasteen. Valinta on lopullinen, paikkoja rajoitetusti, nopein saa |
| pe 16.45 | Tiimin muodostus sulkeutuu |
| pe 17.00 | Avajaiset, sitten Jason Mayes (Google Web AI) 17.30–18.30 |
| pe 18.50–19.30 | Yrityksen briefing. Koko haaste ja data aukeavat appissa 19.30 |
| la 9–12 ja 14.30–18 | Yritysten Q&A Jokessa |
| **su 10.00** | **Palautus** |
| su 10–12 | Osallistujaäänestys (10 ratkaisua per henkilö). Viisi eniten ääniä saanutta finaaliin |
| su 13.15 | Päätöstilaisuus, 13.30 jokaisen haasteen top 3, 14.00 finaali (4 min esitys + 6 min kysymyksiä) |

Kalenteri: https://sinceai.ai/hackathon-2026/guide/calendar/builders

## Arviointi

- Jokainen yritys arvioi oman haasteensa omilla kriteereillään ja valitsee top 3:n.
- Yleisiä kriteerejä: toimiiko, vastaako haasteeseen, käytännön ja liiketoiminnan arvo, tekninen laatu, toteutettavuus, osaako tiimi selittää ratkaisunsa, yksityisyys, tietoturva ja datan vastuullinen käsittely.
- Pelkkä mockup ei kelpaa. Toimiva demo ensin, slidet ovat vapaaehtoisia.
- Finaalin tuomaristo: Runeberg (Maria 01), Elers (Voima Ventures), Mäkilä (UTU, tutkii tekoälyagentteja ja LLM-koodia), Harmaala (Inovexus), Challagonda (FIWARE).

## Palautuslomakkeen pakolliset kentät (kerätään rakentamisen aikana)

- projektin nimi
- submission URL (pitää toimia tapahtuman jälkeenkin)
- About, enintään 5 000 merkkiä
- repo- tai demolinkki (testaa uloskirjautuneena)
- Built with
- Technology feedback
- GenAI tools used
- Generative AI in your project
- jokainen jäsen hyväksyy IP-ehdot itse

Vapaaehtoiset: noin 2 min demovideo (MP4/WebM tai YouTube), pitch deck (PDF/PPTX). ZIP-tiedostoja ei hyväksytä.

## Partnereiden resurssit

- **CSC/LUMI + Aitta** (OpenAI-yhteensopiva API avoimille malleille): rekisteröinti pe 30.10. mennessä. Vaatii oman organisaation sähköpostin (Laurea käy). Ohjeet tulivat Since AI -sähköpostissa 25.10., otsikossa "SUPERCOMPUTER".
- **Featherless**: 25 $ inferenssikrediittiä (avoimet mallit, OpenAI-tyylinen API), 1 200 ensimmäiselle.
- **Pruna**: kuva- ja videogenerointi yhteisellä API-avaimella, vain backendissä.
- **ElevenLabs**: Creator-tilaus kuukaudeksi.
- **Lovable**: 100 krediittiä.
- **n8n**: Cloud Pro kuukaudeksi, 200 ensimmäiselle.
- **Red Hat OpenShift Developer Sandbox**: 30 päivää ilmaiseksi. Ohje: aktivoi ennen tapahtumaa, esim. 3.–5.11., jolloin se on voimassa koko viikonlopun.
- Aiven (Postgres, Kafka jne.) ja FIWARE: tavalliset ilmaiset tasot.
- Koodit tulevat Since AI -viesteissä ja Discordissa (discord.gg/vMWdrVUPws).

## Red Hat OpenShift AI -palkinto (1 000 €)

Rastitetaan palautuslomakkeessa Partner technologies -kohdasta. Red Hatin arvioija katsoo evidenssin, joten maininta ei riitä.

Tila 6.11. klo 12.50: sandbox käytössä, projekti `janner-1-dev`. Build, deploy, edge-TLS Route ja inferenssi todistettu smoke-mallilla (R² 0,985). KServeä ei ole asennettu, joten malli ajetaan omassa serving-kontissa.

**Vaadittu lisäys tapahtuman aikana:** yksi Data Science Pipeline -ajo OpenShift AI:ssa, joka treenaa saman mallin kuin mitä sovellus servaa. Tehdään vasta kun demoydin toimii, ei ennen. Evidenssi = onnistuneen ajon run id ja kuva ajonäkymästä. Tämä on ainoa puuttuva pala palkinnon evidenssissä.

Checklist myös `SUBMISSION.md`:ssä. Ohje ja ansat: skill `hackathon-preparation/references/redhat-openshift-sandbox.md`.

## Vuoden 2025 haasteet (antavat suuntaa tyypeistä)

Kongsberg: merenkulun äänimerkkien tunnistus. Sandvik: varaosakyselyagentti (RAG). Valmet: kenttälaitteiden konenäkötunnistus. Business Turku: rahoitusneuvoja (RAG). Eisko: komponenttilistat PDF:istä (OCR). A'Pelago: syanobakteeridatan aikasarjat. Lisäksi B2B-liidiagentti ja turvallisuusdatan visualisointi.
Toistuvat teemat ovat RAG/agentit, dokumentti-AI, konenäkö ja aikasarjat. Valmet ja Business Turku ovat mukana uudelleen.

## Sopivuus Jannelle (alustava, tarkistetaan to 5.11.)

- **Traficom**: Kyberturvallisuuskeskus on osa Traficomia. Vahvin kyber-kytkös.
- **DNA, Elisa**: telcot, tietoturvakulmat todennäköisiä. DNA on jo hakemuslistalla.
- **Turku Energia**: kotienergian osaaminen (spot-hinnat, kuormanohjaus).
- **Meyer Turku, Valmet**: harjoittelulistan teollisuusyrityksiä, verkostoitumisarvo.
- Rekrytointi: yritysten edustajat ovat paikalla koko viikonlopun. Q&A on hyvä hetki myös harjoittelukeskusteluihin.

## Tehtävät ennen tapahtumaa

- [ ] Varmista hyväksyntä ja sinceai.app-tili (onko tiimi vai tullaanko yksin/route B?)
- [ ] **Meal RSVP pe 30.10. mennessä**
- [ ] **LUMI-rekisteröinti pe 30.10. mennessä** (jos halutaan; Laurean sähköposti)
- [ ] Liity Discordiin, seuraa partnerikoodeja
- [ ] Tiimin repo valmiina, kaikilla push-oikeus (tyhjä runko + README-pohja; valmis koodi merkitään pre-existingiksi)
- [ ] Lataa etukäteen työkalut, kontit ja paikalliset mallit (wifi on jaettu, BioCityn ohjeet vielä auki). Puhelimen hotspot varalle.
- [x] to 5.11. klo 15: tiivistelmät luettu, kolmen lista tehty (ks. Päätös 5.11.2026)
- [ ] pe: tiiminvetäjä valmiina valitsemaan heti klo 15 jälkeen (paikat täyttyvät)
- [ ] Mukaan: läppäri, laturi, adapterit, juomapullo, kynä, eväät yöksi
- [ ] Majoitusta ei tarvita (Raisio). Parkki: ParkCity, enintään 15 €/vrk, ei sisäänajoa 00–06. Yöllä P-Station Kupittaa (24/7).

## Huomioita

- Verkkoja ei saa skannata eikä niihin saa tehdä tietoturvatestejä (koskee myös kyber-ideoita).
- Henkilötietoja tai luottamuksellista dataa ei saa lähettää ulkoiselle AI-palvelulle ilman lupaa. Tämä on sopusoinnussa Jannen privacy routingin kanssa: paikallinen malli tai LUMI/Aitta on etu arvioinnissa.
- Julkinen repo vain, jos haasteen IP-ehdot sallivat.
- Nukkumatiloja ei ole.

## Päätös 5.11.2026: kolmen lista

Tiimi: Greedy Decoding (soolo). Tiiminvetäjä on Janne itse, joten valinta tehdään itse perjantaina 15.00. Valinta on lopullinen ja paikkoja on rajoitetusti.

| # | Haaste | Idea | Miksi tämä sija |
|---|---|---|---|
| 1 | Traficom | Taajuusikkuna: laskee linkkibudjetin ja näyttää kartalla, missä paikallinen 3,8–4,2 GHz:n verkko voi häiritä satelliittia tai kiinteää linkkiä, ja perustelee riskin | RF-osaaminen, julkinen data, 4,05–4,2 GHz:n päätös 2.11.2026, vähän kilpailijoita |
| 2 | TrustED | Todistepaketti: privacy/utility-käyrä synteettisellä datalla, uudelleentunnistusyritys, tulos allekirjoitettu ed25519:llä ja ketjutettu | Tekninen vaikeus 5/5, erottuvuus 5/5, virallisilla painoilla toinen. Riski: demo 2/5, jos hyökkäys ei onnistu |
| 3 | Turku Energia | Päätöskortti 36 h: lämpö- ja hintanäkymä ennusteväleillä, kolme toimenpidevaihtoehtoa kustannus- ja päästöhaarukoilla, päätös jää ihmiselle | Oikea tekninen sisältö (kvantiiliennuste), kotienergian osaaminen, demo julkisella datalla |
| 4 | DNA | Huijaustriage, "olen itse kohde" -tarina | Varmin demo, mutta tekninen vaikeus 1/5 ja kovin kilpailu |

**Lukittu 5.11.2026 illalla: Traficom, TrustED, Turku Energia.** Peruste: kilpailu edellä, teknisesti haastava haaste ja helppo erottua. TrustED palasi DNA:n tilalle, koska DNA:n tarina parantaa pitchiä mutta ei teknistä pistettä. TrustED on lisäksi parempi varavaihtoehto: kapea haaste täyttyy todennäköisesti hitaammin kuin kuluttajademo. Discord-kysymyksiin ei ollut vastausta lukitushetkellä.

Pisteet Jannen kriteereillä (max 25): Traficom 22, Turku Energia 20, TrustED 19, DNA 19, FORCIT 18. Virallisilla painoilla: Traficom 4,65, TrustED 4,40, FORCIT 4,20, DNA 4,10, Turku Energia 3,90. Tekninen vaikeus: Traficom 5, TrustED 5, Turku Energia 3, DNA 1.

### Ehdot, jotka muuttavat järjestystä

- Traficom: jos heillä on jo sisäinen yhteensopivuuslaskenta, idea vaihtuu hakemusseulaksi tai GNSS-häiriökompassiksi. Traficom pysyy ykkösenä.
- TrustED: jos vaaditaan EDC-, Gaia-X- tai IDSA-integraatio tai oikeaa henkilödataa, TrustED putoaa ja DNA nousee kolmanneksi.
- Turku Energia: jos pääongelma on pelkkä tasepoikkeama, Turku putoaa DNA:n taakse.
- FORCIT: ei listalla. Data aukeaa vasta pe 18.50, ala on uusi ja iso potti tuo todennäköisesti enemmän tiimejä.

### Varasuunnitelma perjantaille

1. Traficom täynnä klo 15.05 → TrustED viimeistään 15.07.
2. TrustED täynnä → Turku Energia viimeistään 15.10.
3. Turku täynnä → DNA viimeistään 15.12.
4. DNA täynnä → paras jäljellä oleva. FORCIT vain jos NDA:n ehdot hyväksytään.

Ennen perjantaita tarkistettava: TrustED-raportin väite, että SmartNoise-putki on jo ajettu tällä koneella. Jos se ei toimi, TrustEDin kakkossija on heikompi kuin pisteet näyttävät. Traficomin osalta lue `IDEA.md`:n päätelmät ja `HAASTEET.md`:n Laatu 2015 -osio ennen klo 15.00.

Ennen klo 15.00 valmiina: kirjautuminen sinceai.appiin toimii, tämä lista on auki puhelimessa, pisteytyslomake (alla) täyttövalmiina, ja kaksi teknistä pohjaa (selain-UI ja dataputki) ovat olemassa, jotta haasteen vaihto ei ala nollasta.

### Perjantain 2 tunnin ikkuna (15.00–17.00)

Discord 6.11.: haasteiden tarkemmat tiedot julkaistaan 2 h ennen avajaisia eli klo 15.00, ja tukikanavat avataan, jos yritysedustaja on paikalla. Valintaa ei siis tehdä pelkkien tiivistelmien varassa, mutta ikkuna on lyhyt ja paikat menevät nopeimmalle. Lukittu järjestys pysyy oletuksena; vain alla olevat ehdot muuttavat sitä, eikä mikään muu.

| Klo | Mitä |
|---|---|
| 14.45 | Puhelin auki sinceai.appissa, tämä lista ja pisteytyslomake valmiina. Ole paikalla ennen 15.00 |
| 15.00 | Ilmoittautuminen. Avaa haastelista heti |
| 15.00–15.15 | Lue vain kärkikolmikko: Traficom, TrustED, Turku Energia. 5 min per haaste |
| 15.15 | Valitse, jos mikään ei kaatunut. Paikat menevät nopeimmalle, joten älä lue muita ensin |
| 15.15–15.45 | Vasta jos kärki kaatui: lue DNA ja muut, valitse viimeistään 15.45 |
| 15.20–15.50 | Valitun haasteen tukikanavassa yksi kaatava kysymys, jos edustaja on paikalla. "Ei osaa sanoa" siirtyy briiffiin 18.50 |
| 16.45 | Tiimin muodostus sulkeutuu; valinnan on oltava tehty |

Pisteytyslomake, yksi rivi per haaste jonka tieto muuttui:

| Haaste | Mikä muuttui | Kaatava ehto täyttyi | Uusi sija |
|---|---|---|---|

### Yrityshyöty: mitä valinnalta pitää kysyä

Hyöty ei ole uusi pisteytysrivi. Se on kolme ehtoa, jotka vain yritys voi vahvistaa:

1. Omistaja: jollakin on tämä ongelma työnään, ei ideana.
2. Korvattava työ: ratkaisu poistaa käsityötä, jonka joku tekee nyt. Mitä harvinaisempi tekijä, sitä isompi hyöty.
3. Käyttöönottopolku: yhdellä lauseella, kuka ottaa sen käyttöön ja mitä se vaatii.

Testi: jos edustaja ei nimeä henkilöä, joka käyttäisi sitä, ja lukua, joka muuttuisi, hyötyä ei ole. Kohteliaisuus ei ole signaali.

Valinta tehdään klo 15–16 ja tarkemmat tiedot aukeavat klo 15.00. Siksi hyötykulma ei valitse haastetta, se vahvistaa tai kaataa suunnitelman. Järjestys: Traficom, TrustED, Turku Energia, DNA.

Ohjeen viisi kysymystä näin:

| Ohjeen kysymys | Mitä se testaa | Milloin |
|---|---|---|
| Mikä on suurin ratkaistava ongelma? | kaatuuko meidän idea | briiffi 18.50 |
| Kuka käyttäisi? | omistaja | la 9-12 |
| Mikä tekee siitä arvokkaan? | luku | la 9-12 |
| Mikä estäisi käyttämästä? | este, tärkein ja vähiten kysytty | la 14.30-16 |
| Saammeko näyttää prototyypin? | lukko, sovi aika heti | briiffi, aika la 15-16 |

Säännöt:

- Briiffissä yksi kysymys per yritys, se joka voi kaataa suunnitelman. Sali on täynnä, muuta ei ehdi.
- Lauantain aamu on skooppi ja data. Iltapäivä on prototyyppi ja este. Suunnanvaihto viimeistään klo 16.
- Kirjaa vastaus sanasta sanaan. Demon arvolause lainataan edustajalta, ei keksitä.

Pakollinen kysymys per haaste:

- Traficom: onko 3,8-4,2 GHz:n yhteensopivuuslaskenta käsityötä vai työkalu, ja kuka sitä tekee. Kysy myös montako häiriöilmoitusta tulee viikossa.
- TrustED: pitääkö prototyypin istua EDC/Gaia-X/IDSA-arkkitehtuuriin, riittääkö synteettinen data, ja kuka valitsee top 3:n (onko paikalla Turussa).
- Turku Energia: mitä päätöstä halutaan parantaa. Kysy paljonko yksi tasepoikkeama maksaa.
- DNA: onko pääkäyttäjä kuluttaja vai pk-yritys, ja mikä estäisi ottamasta työkalua käyttöön.

### Tarinan kulma: olen itse kohde (vain jos valinta päätyy DNA:han)

DNA:n haaste puhuu ihmisistä ja pienyrityksistä. Janne on itse pienyritys, jolla ei ole IT-osastoa. Se on aito ero, jota kukaan tiimi ei voi kopioida, ja se korjaa DNA:n heikoimman pisteen eli erottuvuuden.

Miten se tehdään uskottavasti, ei myyntipuheena:

- Demon käyttäjä on Turun Mainostuote, ei kuvitteellinen yritys. Yhden hengen B2B-verkkokauppa, jolla on oikeat laskut, oikeat toimittajat ja oikeat huijausyritykset sähköpostissa.
- Materiaali on Jannen oma postilaatikko, ei asiakkaiden data. Redaktoi nimet ja osoitteet, ja sano ääneen että ne on redaktoitu.
- Ensimmäinen lause demossa: "Rakensin tämän omalle yritykselleni, koska minä olen kohde." Ei "käyttäjätutkimuksen mukaan".
- Sama tarina vastaa responsible-kriteeriin: viestit käsitellään paikallisesti, mitään ei lähetetä eteenpäin, ja jokainen vastaus näyttää perustelun.
- Älä tee demosta työnhakuperformanssia. Työnhaku hoidetaan Q&A:ssa, ei slidessä.

### Raportit

Kaikki viisi yritysraporttia ja synteesi: `/home/hermes/hackathon-research/2026-11-05/`. Yhteensä 150 lähdettä. Kanban-board: `since-ai-2026`.

## 6.11.2026 klo 15.04: Traficomin pitkä teksti julkaistu

Teksti siirtää painopisteen laskennasta analyysityöhön. Lauseet, jotka ratkaisevat:

- "interpret international filings, national rules and large amounts of complicated information"
- "discover relevant filings, understand their implications, connect evidence across sources and identify situations worth investigating"
- "regulatory intelligence, information extraction, technical reasoning and explainable AI"
- "keeping human experts firmly in control of consequential decisions"

Tämä on valmistelussa kirjattu haarautumisehto ("idea vaihtuu hakemusseulaksi"), mutta ehto ei ollut yrityksen sisäinen laskenta vaan tekstin oma rajaus. Ykkössija ei muutu: kaatavat ehdot eivät täyty, ja tekstin vaikeustaso on korkeampi kuin pelkässä linkkibudjetissa.

Uusi yhden lauseen idea: hakemusseula, joka poimii ITU:n kaavakkeista ja Traficomin kansallisista säännöistä taajuudet, peitot ja tehot, laskee karkean yhteensopivuuden Suomen järjestelmiä vastaan ja näyttää jokaisesta lipusta todisteketjun (kaavake, säädös, laskettu luku) sekä ihmisen hyväksy/hylkää-päätöksen.

Säilyy: RF-laskenta on "technical reasoning" -moduuli, ei koko tuote. Kartta ja linkkibudjetti jäävät, mutta otsikko on triage.
Säilyy: Jannen etu. Dronescanner on sama työ skaalassa (säädös → tekninen raja → tarkistus), joten tarina on aito.

Demon aineisto: ITU:n julkiset kaavakkeet (IFIC/SNL) C-kaistalta, Traficomin oma 2.11. päätös 4,05–4,2 GHz:stä, sekä kansallinen määräyskokoelma. Synteettinen tai julkinen data riittää, ei sisäistä aineistoa.

Kysymys tukikanavaan ennen valintaa, vain tämä: onko oikea kohde ITU:n kaavakkeet ja kansalliset säännöt, ja kelpaako karkea laskettu yhteensopivuus näytöksi vai halutaanko pelkkä dokumenttien seulonta.

Jos vastausta ei tule, valinta tehdään tekstin oman sanamuodon perusteella: seulonta + laskettu vaikutus + ihmisen päätös.

## 6.11. klo 15.07: Turku Energian pitkä teksti

Kaatava ehto ("pääongelma on pelkkä tasepoikkeama") ei täyty. Tase on motivaatio, ei tehtävä. Tehtävä on sanasta sanaan: "turn complex energy-market information into a clearer view of what might happen next", "how uncertain is the forecast and when should a human trust it", ja työkalulista on "time-series modelling, probabilistic AI, explainability and thoughtful data visualisation".

Eilinen idea osuu tähän suoraan: päätöskortti, kvantiiliennuste, kolme vaihtoehtoa, ihminen päättää. Ei muutosta.

Sija ei nouse. Ennustehaaste on hackathonin yleisin muoto, joten kilpailu on kovempi ja erottuvuus heikompi kuin Traficomin kapeassa tekstissä. Erottuminen pitää hakea kohdasta "when should a human trust it": kalibroitu kateavuus ja ajurien selitys, ei piste-ennuste.

Operatiivinen muutos: jos Traficom on täynnä, valitse Turku Energia ennen TrustEDiä. Turku on nyt tarkistettu, TrustEDin kaatava ehto (EDC/Gaia-X/IDSA, oikea henkilödata) on yhä auki. Kiireessä tarkistettu voittaa pisteytetyn.

## 6.11. klo 15.07: TrustEDin pitkä teksti, ja edellisen kohdan kumoaminen

Kaatava ehto ei täyty. Teksti sanoo "inspired by the European TrustED project", ei "integroi EDC/Gaia-X/IDSA:an". Pakollista liitäntää ei mainita. Oikeaa henkilödataa ei vaadita: "a convincing prototype" ja "measurable trade-offs" riittävät, joten synteettinen data kelpaa.

Edellisessä kohdassa tehty vaihto (Turku ennen TrustEDiä) perustui siihen, että TrustED oli tarkistamaton. Se peruste on nyt pois. Järjestys palaa lukittuun: Traficom, TrustED, Turku Energia.

Teksti vahvistaa eilisen idean sanasta sanaan: "understand different kinds of sensitive information" (luokittelu), "choose appropriate privacy-enhancing transformations" (valinta), "demonstrate what analytical value remains afterward" (utility-mittaus). Todistepaketti osuu suoraan.

Auki jäävä riski on sama kuin eilen kirjattu: demo 2/5, jos uudelleentunnistus ei onnistu. Teksti vaatii nimenomaan "concrete, testable terms", joten pelkkä käyrä ei riitä, tarvitaan yritys ja sen tulos.

Yksi kysymys TrustEDin kanavaan: pitääkö prototyypin noudattaa European TrustED -projektin arkkitehtuuria vai riittääkö oma toteutus samoilla periaatteilla.

## 6.11. klo 15.07: FORCITin pitkä teksti

Sija ei muutu: ei listalla. Teksti vahvistaa eilisen perustelun sanasta sanaan: "Access to challenge data is subject to confidentiality requirements after selection." Dataa ei saa ennen valintaa, joten 48 h alkaa nollasta klo 19.30, ja NDA ratkaisee saako demoa ja repoa näyttää.

Tekninen istuvuus olisi hyvä (prosessilouhinta, poikkeamien tunnistus, selittävä AI, tapahtumaloki). Juuri siksi tämä on ainoa haaste, jossa data on ainoa este eikä tekniikka. Jos kaikki muut täyttyvät, FORCIT on vaihtoehto vasta kun NDA on luettu ja varmistettu, että anonymisoitu demo saa näkyä.

Teksti rajaa myös skoopin: "not a request to redesign blasting parameters". Joten räjäytysparametrien optimointi on väärä vastaus, vaikka data sitä houkuttelisi.

## 6.11. klo 15.07: tarkistus valmis

Kaikki neljä tekstiä luettu (Traficom, TrustED, Turku Energia, FORCIT), kaikki kaatavat ehdot tarkistettu, yksikään ei täyttynyt. Lukittu järjestys pitää: Traficom, TrustED, Turku Energia. FORCIT vain jos kaikki kolme ovat täynnä ja NDA on hyväksytty.

## 6.11. klo 15.20: valinta tehty, Traficom viimeisenä paikkana

Haaste: Traficom. Valinta on lopullinen. Tiimi: Greedy Decoding (soolo).

Seuraava kiinteä piste: briiffi 18.50, koko haaste ja data aukeavat 19.30. Siihen asti tehdään vain tutkimusta ja datan hankintaa, ei tapahtuman koodikerrosta.

Idea (kirjattu yllä): hakemusseula. ITU:n kaavakkeet + kansalliset säännöt sisään, karkea yhteensopivuuslaskenta, todisteketju per lippu, ihmisen hyväksy/hylkää.

Kolme asiaa jotka pitää selvittää ennen 18.50:
1. Saadaanko ITU:n kaavakkeista rakenteelliset parametrit (taajuus, peitto, EIRP, kiertorata) ilman käsityötä. Jos vain skannattuja PDF:iä, poiminta on raskaampi ja skooppi pienenee.
2. Mikä on se kansallinen lähde, jota vasten verrataan. Traficomin määräykset ja radioluparekisteri.
3. Yksi havainnollinen tapaus, jossa kaavake ja Suomen järjestelmä osuvat samalle kaistalle. Ilman sitä demossa ei ole tarinaa.

Kysymys briiffiin 18.50: onko oikea kohde ITU:n kaavakkeet ja kansalliset säännöt, ja kelpaako karkea laskettu yhteensopivuus näytöksi vai halutaanko pelkkä dokumenttien seulonta.

## 6.11. klo 15.30: ITU:n datan tekninen tarkistus

Tarkistettu oikeilla kutsuilla, ei muistista:

1. SNL Online on kuollut. `https://www.itu.int/online/snl/freqrnge_snl.sh` palauttaa 200 mutta ei tuloksia, vain ilmoituksen "The SNS Online application is reaching its end of life and will be shut down soon in 2025" ja osoitteen Space Exploreriin. Vanha kyselyrajapinta on siis pois pelistä.
2. Space Explorer on julkinen SPA: `https://www.itu.int/itu-r/space/apps/public/spaceexplorer/`. Sen bundle viittaa osoitteisiin `auth.itu.int` ja `oauth.itu.int` sekä polkuun `/api-terms-of-use`. Anonyymiä bulk-rajapintaa ei siis voi olettaa; ITU-tili näyttää todennäköiseltä.
3. ITU:n sivusto on WAF:n takana. Yksi pyyntö samaan osoitteeseen torjuttiin ("Request Rejected"), ja oikeilla otsakkeilla meni läpi. Verkkohaku demo-aikana on siis epävarma.

Seuraus: demoa ei rakenneta elävien ITU-kutsujen varaan. Kaavakkeet haetaan etukäteen tiedostoiksi repoon ja putki ajetaan niiden päällä. Se on myös parempi demo: deterministinen, offline, ei verkkoriskiä lavalla.

Avoin kysymys, joka ratkeaa 19.30: antavatko he kaavakeaineiston itse. Jos antavat, ongelma poistuu. Jos eivät, tarvitaan ITU-tili ja 10–30 kaavaketta ennen puoltayötä.

Sovitinpinta, joka pitää olla olemassa ennen kuin dataa on: yksi funktio, dokumentti sisään, parametrit ulos (taajuusalue, palvelu, kiertorata tai asema, EIRP), ja lähdeviite mukana. Ei muuta koodia ennen 19.30.

## 6.11. klo 15.40: kysymyslista Traficomille

Kieli englanti. Kirjaa vastaukset sanasta sanaan, ne lainataan pitchissä.

### Briiffi 18.50, kaksi kysymystä

1. "Is the target the ITU filings plus the Finnish national rules, and does a coarse computed compatibility check count as evidence, or do you want document triage only?"
   Ratkaisee, onko RF-laskenta tuote vai koriste.

2. "Do you review each IFIC against a comment deadline, and would a deadline-ordered queue match how you work?"
   Ratkaisee, onko tuote jono kellon kanssa vai pelkkä seula. Korvasi 15.56 datakysymyksen, koska materiaalit jaetaan briiffissä. Määräaikasääntö (RR Art. 9, noin 4 kk) on tarkistamatta, älä käytä pitchissä ennen tarkistusta.

   Vanha kysymys, vain jos briiffissä ei mainita dataa: "Do you hand us a document set at 19.30, or do we source the filings ourselves?"

### Lauantai 9–12, omistaja ja arvo

3. "Who does this interpretation today, and how long does one filing take them?"
   Kaatava ehto piilee tässä: jos vastaus on "we have a tool that does it", idea vaihtuu. Muuten tämä antaa omistajan ja korvattavan työn.

4. "What is the hardest part for you: finding the relevant filing, understanding it, or explaining it to someone else?"
   Yksi kysymys, joka kohdistaa tuotteen oikeaan pullonkaulaan. Vastaus valitsee, painotetaanko hakua, tulkintaa vai selitystä.

5. "How many filings a week could raise a question for systems in Finland?"
   Antaa mittakaavan ja sen, onko kyse kymmenistä vai tuhansista.

6. "What would you need to see on Monday morning to say this was useful?"
   Demon arvolause tulee tästä, ei keksitä.

7. "What would be an unacceptable false alarm?"
   Kertoo sekä sietorajan että sen, kuinka vahva todisteketju pitää olla.

### Lauantai 14.30–18, skooppi ja käyttöönotto

8. "One band or all of them? Which band has live questions right now?"
   48 h ei riitä kaikkiin. Yksi kaista, jossa on oikeita tapauksia, on parempi kuin koko spektri ilman tarinaa.

9. "Is the output a case file, a queue or a report, and who reads it next?"
   Määrittää käyttöliittymän muodon.

10. "Where must a human decide, and what must the tool never decide alone?"
    Teksti lupaa "human experts firmly in control". Tämä kertoo, miten se toteutetaan.

11. "May we show real filings in a public demo and a public repo?"
    Ratkaisee repon julkisuuden ja sen, mitä lavalla saa näyttää.

### Älä kysy

Onko ITU:n data julkista (se on), mitä mallia pitäisi käyttää, paljonko palkinto on, tai yleisiä arviointikriteerejä. Ne eivät muuta työtä ja vievät aikaa siltä yhdeltä kysymykseltä, joka muuttaa.

## 6.11. klo 15.56: materiaalit jaetaan briiffissä

Sivujen mukaan kaikki materiaalit aukeavat paikan päällä briiffissä, ja mukana tulee todennäköisesti myös dataa. Varmaa se ei ole.

Mitä tämä muuttaa ennen 18.50:

1. ITU-kaavakkeita ei haeta etukäteen. Se voi olla turhaa työtä, ja WAF ja ITU-tili vievät aikaa. Varasuunnitelma pidetään valmiina mutta tekemättä: jos dataa ei tule, haetaan 10–20 kaavaketta itse tai tehdään ITU-muotoiset synteettiset ja sanotaan se ääneen.
2. Rakennetaan vain datasta riippumattomat osat: linkkibudjetin laskenta ja todisteketjun muoto (lähde, parametri, laskettu luku, ihmisen päätös).
3. Briiffin kysymys 2 vaihdettu määräaikakysymykseksi (ks. kysymyslista).

Briiffissä data ratkaisee painotuksen:

| Mitä tulee | Mihin työ painottuu |
|---|---|
| Pelkkiä dokumentteja (PDF, säädöksiä) | Poiminta ja todisteketju. RF-lasku jää pieneksi moduuliksi |
| Rakenteellista dataa (taulukot, parametrit) | Poiminta kevenee, laskenta ja jono kasvavat |
| Valmis esimerkkitapaus | Demo rakennetaan sen ympärille. Se on tarina |
| Ei dataa | Varasuunnitelma: haetaan itse tai tehdään synteettiset |

Kulma kestää kaikki neljä. Ydin pysyy: kone lukee, fysiikka laskee, ihminen päättää. Jos data ohjaa selvästi muualle, seurataan dataa eikä omaa suunnitelmaa, koska Traficom arvioi sen mukaan mitä itse antoi.

Hienosäädöt, jotka pätevät datasta riippumatta:

- Häiriön suunta: kaukainen ulkomainen kaavake vaikuttaa suomalaiseen järjestelmään. Traficomin 2.11. päätös 4,05–4,2 GHz:stä on taustaa, ei demon päätapaus.
- Kielimalli poimii ja selittää, mutta ei tuota lukuja. Jokainen dB tulee deterministisestä laskusta.
- Pieni arviointi: 15–20 kaavaketta, itse merkityt oikeat vastaukset, löydetyt ja turhat liput yhdessä taulukossa.
- Yksi kaista ja yksi tarina. Kartta mukaan osallistujaäänestystä varten.
- Dronescanner vain yhtenä lauseena taustassa, ei demossa.
