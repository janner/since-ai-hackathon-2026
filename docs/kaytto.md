# Kaista käyttäjän silmin

Tämä sivu on Traficomin taajuusasiantuntijalle. Viisi askelta, ei yhtään komentoriviä.

**Ennen kuin alat.** Työkalu avataan selaimessa. Palvelu hakee uuden BR IFIC -paketin itse ITU:lta
kahden viikon välein, joten sinun ei tarvitse tuoda tiedostoa. Yläpalkin "Check now" -nappi kysyy
ITU:lta heti (komentoriviltä sama on `python scripts/monitor.py --check`). Jos automaattihaku ei
toimi, kehittäjä ajaa putken käsin (`python -m app.pipeline --ific <mdb>`); sivulla ei ole tiedoston
tuontia.

## Viisi askelta

1. **Avaa osoite selaimessa.** Yläpalkki näyttää suppilon luvut ja jonon pituuden. Vasemman
   sarakkeen "Funnel" (suppilo) kertoo, montako ilmoitusta seulottiin ja miksi loput putosivat pois.
2. **Tarkista uusi aineisto.** Palvelu hakee uuden BR IFIC -paketin ITU:lta itse; sinä et tuo
   tiedostoa. Yläpalkin "Check now" -nappi kertoo, onko uutta pakettia, ja ajaa sen. Rekisteri ja
   M4 eivät vaihdu joka paketissa, joten ne ovat palvelimella.
3. **Katso "Queue" (jono).** Jono järjestää ensin sääntelyvaiheen: "Advance publication" ja
   "Coordination request" tulevat ennen "Recorded in the MIFR", koska niihin voi vielä vaikuttaa.
   Vaiheen sisällä järjestys on "Exceeds limit", "Near limit", "No satellite use in Finland" (kaista,
   jolla ei ole Suomessa satelliittikäyttöä) ja "Cannot decide". Marginaali ei järjestä jonoa.
4. **Avaa tapaus.** Lue "What this means" ja "What information is missing". Laskelma on piilossa
   "Show calculation" -painikkeen alla; avaa se, jos haluat tarkistaa luvun itse.
5. **Kopioi kysymys kohdasta "Question to the other administration"** ja lähetä kirje omasta
   sähköpostistasi.

## Mitä työkalu ei tee

Työkalu ei tee päätöstä: jokainen luku tulee koodista, ei kielimallista. Se ei lähetä kirjettä
puolestasi, vaan antaa luonnoksen, jonka sinä luet ja lähetät. Se ei myöskään tallenna, mitä olet
katsonut: ei "katsottu"-merkintää, ei kommentteja, ei omistajia.
