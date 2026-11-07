# Sanasto

Termit ovat englanniksi, koska data ja kirjeet ovat englanniksi. Selitys on suomeksi ja jokaisessa
on lähde.

| Termi | Selitys | Lähde |
|---|---|---|
| **BR IFIC** | ITU:n Radioviestintätoimiston (BR) joka toinen viikko julkaisema taajuusilmoituskiertokirje, jonka uudet satelliittiverkkojen ilmoitukset työkalu lukee. | ITU BR IFIC (Space Services), Preface |
| **API/A ja CR/C** | Ilmoituslomakkeet: API/A on ennakkojulkaisu (Art. 9.1) ja CR/C on koordinaatiopyyntö (Art. 9.6); molemmat kertovat, voiko toinen hallinto vielä vaikuttaa ilmoitukseen. | ITU RR 2024, Vol 1, No. 9.1 ja 9.6 |
| **IFIC-numero** | Kiertokirjeen juokseva numero (esim. 3074), joka yksilöi paketin ja näkyy kortin tunnisteessa. | ITU BR IFIC |
| **M4** | Traficomin radiotaajuusmääräys 4 AG/2026M, jonka liitteen taajuusjakotaulukko kertoo, mille palveluille kaista on Suomessa jaettu. | Traficom M4 (4 AG/2026M), liite s. 147–148; `data/taajuusjakotaulukko.json` |
| **M15** | Traficomin radiotaajuusmääräys 15 AV/2025M, jonka briiffi mainitsee ristiintarkistuksena mutta jota työkalu ei käytä. | Traficom M15 (15 AV/2025M) |
| **PFD** | Power flux density, tehon vuontiheys: satelliitin lähettämä teho pinta-alayksikköä kohti, jota työkalu vertaa ITU:n rajaan. | ITU RR 2024, Art. 21; `app/pfd.py` |
| **dB(W/m²/Hz)** | PFD:n yksikkö: desibeleinä ilmaistu teho neliömetriä ja hertsiä kohti. | ITU RR 2024, Art. 21 |
| **marginaali (margin)** | Lasketun PFD:n ja rajan ero desibeleinä; positiivinen marginaali tarkoittaa, että laskettu yläraja on rajan yli. | `cases.json`, kenttä `calculation.margin_db` |
| **yläraja (upper bound)** | Työkalun luku on seulonnan yläraja, ei väite häiriöstä: se yhdistää suurimman tehon, suurimman keilan vahvistuksen ja vapaan tilan vaimennuksen. | `README.md`, "Known limitations" 1 |
| **GSO ja NGSO** | Geostationaarinen (GSO) satelliitti pysyy kiinteällä pituusasteella, kun taas ei-geostationaarinen (NGSO) liikkuu, joten työkalu laskee sille pyyhkäisyn. | ITU RR 2024, Vol 1 (Definitions); `app/gates.py` |
| **MIFR** | Master International Frequency Register, ITU:n rekisteri kirjatuista taajuusmäärityksistä; No. 11.2 -ilmoitus on jo siinä, joten siihen ei voi enää vaikuttaa. | ITU RR 2024, Vol 1, No. 11.2 |
| **No. 9.1 / 9.6 / 11.2** | Radion sääntöjen kohdat, jotka määräävät ilmoituksen vaiheen: 9.1 ennakkojulkaisu ja 9.6 koordinaatiopyyntö (molempiin voi vielä vaikuttaa), 11.2 MIFR-kirjaus (ei enää). | ITU RR 2024, Vol 1 |
