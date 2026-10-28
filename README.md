# Middager hos oss

Liten, privat nettside med ukemeny og middagsforslag for familien.
Skal ligge på <https://vness.no/middager>.

## Slik henger det sammen

```
retter/            <- én tekstfil per rett (dette redigerer du)
bygg.py            <- leser retter/ og lager docs/data/retter.json
docs/              <- selve nettsiden (dette lastes opp)
  index.html
  stil.css
  app.js
  data/retter.json <- generert, ikke rediger
last-opp.sh        <- bygger og laster opp til webhotellet
.env.eksempel      <- mal for FTP-innstillingene
```

## Endre eller legge til en rett

1. Åpne (eller lag) en fil i `retter/`, f.eks. `retter/fiskeboller.md`, i en vanlig teksteditor.
2. Filen ser slik ut:

```
---
navn: Fiskeboller
kategori: fisk
anledning: [hverdag]
sesong: [host, vinter]
tid: 25 min
porsjoner: 5
beskrivelse: Mild klassiker med hvit saus, poteter og gulrot.
---

## Ingredienser

- 1 boks fiskeboller (500 g)

## Slik gjør du det

1. Sett på potetene.

## Tips

- Smak til med litt sitron.
```

3. Lagre, kjør `python3 bygg.py`, og last opp med `./last-opp.sh`.

### Feltene i toppen

| Felt | Betydning |
| --- | --- |
| `navn` | Navnet som vises på siden. |
| `kategori` | `fisk`, `kjott`, `kylling` eller `vegetar`. Retter med `fisk` teller som fiskedag. |
| `anledning` | `[hverdag]`, `[helg]` eller `[hverdag, helg]`. **Hverdag** = mandag–torsdag + søndag. **Helg** = fredag og lørdag. |
| `sesong` | `[hele-aret]` eller en liste av `vinter`, `var`, `sommer`, `host`. Retten foreslås i hovedsak i disse årstidene. |
| `tid` | Fritekst, f.eks. `30 min`. |
| `porsjoner` | Vanligvis `5`. |
| `beskrivelse` | Én linje som vises under navnet. |

Alt under toppen er vanlig markdown: `##` blir overskrift, `-` blir punktliste,
`1.` blir nummerert liste. Oppskriftene er skrevet slik at en 10-åring kan følge dem
under oppsyn, med `(spør en voksen)` på stegene som krever hjelp.

Nytt filnavn = ny rett. Slett filen for å fjerne retten. `bygg.py` sier fra hvis
noe er skrevet feil, eller hvis en årstid har for få retter til å fylle en uke
med tre fiskedager.

## Se siden lokalt

```bash
python3 bygg.py
python3 -m http.server -d docs 8000
```

Åpne så <http://localhost:8000>. (Siden må serveres over `http://` – å åpne
`index.html` direkte fra disk blir stoppet av nettleserens sikkerhetsregler.)

## Legge endringene ut på nett

Første gang:

1. Logg inn på domene.no → Mine sider → finn FTP-brukeren din.
2. `cp .env.eksempel .env` og fyll inn vert, brukernavn, passord og riktig mappe
   (ofte `/www/middager`, noen ganger `/public_html/middager`).
3. Installer lftp én gang: `sudo apt install lftp`.
4. `chmod +x last-opp.sh`

Deretter, hver gang du har endret en oppskrift:

```bash
./last-opp.sh
```

Scriptet bygger og speiler `docs/` opp til webhotellet (med `--delete`, så filer
du har slettet lokalt fjernes også på serveren). `.env` ligger i `.gitignore` og
blir aldri lastet opp.

Har webhotellet SSH, kan du bruke `rsync -av --delete docs/ bruker@vness.no:/www/middager/` i stedet.

## GitHub

Koden ligger på <https://github.com/torbjone/vness-middager>.

Første gang (kun én gang):

```bash
git remote add origin https://github.com/torbjone/vness-middager.git
git push -u origin main
```

Hver gang du har endret noe:

```bash
python3 bygg.py
git add -A
git commit -m "Ny oppskrift"
git push
```

### Gratis testside med GitHub Pages (valgfritt)

På GitHub: **Settings → Pages → Source: Deploy from a branch → Branch: `main`, mappe `/docs`**.
Siden blir da liggende på <https://torbjone.github.io/vness-middager/>, i tillegg til
vness.no/middager. Alle lenker i `docs/` er relative, så den fungerer begge steder.

## Slik velges ukemenyen

- Uken fylles fra mandag til søndag, uten gjentakelser.
- Fredag og lørdag får retter merket `helg`, de andre dagene retter merket `hverdag`.
- Minst tre av dagene er fiskeretter.
- Retter i inneværende årstid (eller `hele-aret`) foretrekkes.
- Ukemenyen er den samme for alle i familien gjennom hele uken.
  **Foreslå middag** gir et helt nytt forslag, og **Bytt** bytter ut én enkelt dag.
