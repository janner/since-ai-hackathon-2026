# Kaista käyttäjän silmin

Tämä sivu on Traficomin taajuusasiantuntijalle. Viisi askelta, ei yhtään komentoriviä.

**Ennen kuin alat.** Työkalu avataan selaimessa. Palvelu hakee uuden BR IFIC -paketin itse ITU:lta
kahden viikon välein, joten sinun ei tarvitse tuoda tiedostoa. Yläpalkin "Tarkista nyt" -nappi kysyy
ITU:lta heti (komentoriviltä sama on `python scripts/monitor.py --check`). Jos automaattihaku ei
toimi tai sinulla on paketti kädessä, tiedoston tuonti on varatie.

## Viisi askelta

1. **Avaa osoite selaimessa.** Yläpalkki näyttää suppilon luvut ja jonon pituuden. Vasemman
   sarakkeen Suppilo kertoo, montako ilmoitusta seulottiin ja miksi loput putosivat pois.
2. **Tarkista uusi aineisto.** Palvelu hakee uuden BR IFIC -paketin ITU:lta itse; sinä et tuo
   tiedostoa. Yläpalkin "Tarkista nyt" -nappi kertoo, onko uutta pakettia, ja ajaa sen. Rekisteri ja
   M4 eivät vaihdu joka paketissa, joten ne ovat palvelimella.
3. **Katso jono kohdasta 2.** Ylittävät ensin, sitten lähellä rajaa olevat. Etujulkaisu ja
   koordinaatiopyyntö tulevat ennen MIFR-kirjattuja, koska niihin voi vielä vaikuttaa.
4. **Avaa tapaus.** Lue "Mitä tämä tarkoittaa" ja "Mitä tietoa puuttuu". Laskelma on piilossa
   "Näytä laskelma" -painikkeen alla; avaa se, jos haluat tarkistaa luvun itse.
5. **Kopioi kysymys kohdasta "Kysymys toiselle hallinnolle"** ja lähetä kirje omasta
   sähköpostistasi.

## Mitä työkalu ei tee

Työkalu ei tee päätöstä: jokainen luku tulee koodista, ei kielimallista. Se ei lähetä kirjettä
puolestasi, vaan antaa luonnoksen, jonka sinä luet ja lähetät. Se ei myöskään tallenna, mitä olet
katsonut: ei "katsottu"-merkintää, ei kommentteja, ei omistajia.
