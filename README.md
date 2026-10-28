# Middager hos oss

Liten, privat nettside med ukemeny og middagsforslag for familien Vefferstad Ness.
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
  data/retter.js   <- generert, ikke rediger
last-opp.sh        <- bygger og laster opp til webhotellet
.env.eksempel      <- mal for FTP-innstillingene
skript/lag_rett.py <- lager en ny rett ut fra et forslag (bruker Mistral)
skript/endre_rett.py <- endrer en rett som allerede finnes (bruker Mistral)
.github/           <- forslagsskjemaene og de automatiske arbeidsflytene
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

Åpne så <http://localhost:8000>.

Du kan også bare dobbeltklikke på `docs/index.html`: rettene følger med i
`docs/data/retter.js`, så siden virker også rett fra disk. Husk å kjøre
`python3 bygg.py` etter at du har endret en oppskrift, ellers viser siden den
gamle versjonen.

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

Hver gang noe er endret:

```bash
python3 bygg.py
git add -A
git commit -m "Ny oppskrift"
git push
```

## Foreslå en ny rett (automatisk flyt)

Andre kan foreslå middager uten å kunne noe om kode:

1. De går til <https://github.com/torbjone/vness_middager/issues/new/choose> og
   fyller ut **Foreslå en ny rett** (navn, kategori, anledning, sesong og
   eventuelle ønsker). De trenger ikke skrive oppskriften selv.
2. Repo-eier (Torbjørn) får varsel på mail fra GitHub med en gang forslaget kommer inn.
3. Forslaget kan da godkjennes ved at repo-eier svare på issuen med kommentaren:

   ```
   /godkjenn
   ```

4. Da starter `.github/workflows/ny-rett.yml`, som:
   - lar Mistral skrive oppskriften i husets stil (`skript/lag_rett.py`),
   - lagrer den som `retter/<slug>.md`,
   - kjører `python3 bygg.py`,
   - committer og laster opp `docs/` til nettsiden via FTP,
   - kommenterer og lukker issuen når retten er ute.

Bare kommentarer fra eier eller en collaborator starter flyten, så ingen
kan publisere noe selv. Husk å kjøre `git pull` etterpå, siden roboten committer
rett på `main`. Går noe galt, legger roboten igjen en kommentar med lenke til loggen.

## Foreslå en endring i en rett som allerede ligger ute

Samme flyt, men for retter som finnes fra før:

1. De fyller ut **Foreslå en endring i en rett** på samme
   <https://github.com/torbjone/vness_middager/issues/new/choose>: hvilken rett
   det gjelder, hva som skal endres, og eventuelt ny kategori, anledning eller
   sesong (velg `behold` på det som skal stå som før).
2. Repo-eier får varsel på mail og godkjenner med samme kommentar: `/godkjenn`.
3. Da starter `.github/workflows/endre-rett.yml`, som kjører
   `skript/endre_rett.py`. Skriptet finner riktig fil i `retter/`, sender den
   eksisterende oppskriften og det ønskede til Mistral, og skriver filen på nytt
   i husets stil. Deretter bygges siden, endringen committes og lastes opp.

To ting er med vilje låst: **filnavnet endres aldri**, og **navnet på retten
beholdes**, slik at ukemenyen og eventuelle lenker fortsetter å virke. Skal
retten hete noe annet, er det enklest å rette `navn:` i filen selv etterpå.

Retten kjennes igjen på navnet slik det står på siden, men det holder ofte med
en del av navnet (`fiskegrateng`) eller filnavnet. Treffer det flere retter,
stopper roboten og sier fra i en kommentar i stedet for å gjette.

Siden hele oppskriften skrives om, er det lurt å lese gjennom resultatet
etterpå – enten i committen eller på siden.

### Engangsoppsett (gjelder begge flytene)

Legg inn disse under **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Verdi |
| --- | --- |
| `MISTRAL_API_KEY` | API-nøkkel fra <https://console.mistral.ai> |
| `FTP_VERT` | Samme som i `.env` |
| `FTP_BRUKER` | Samme som i `.env` |
| `FTP_PASSORD` | Samme som i `.env` |
| `FJERNMAPPE` | Valgfri. Standard er `/www/middager` |

Sjekk også at **Settings → Actions → General → Workflow permissions** står på
*Read and write permissions*, ellers får ikke roboten lov til å committe.

Vil du ha varsel på en annen adresse enn GitHub-kontoen din, setter du den opp
under <https://github.com/settings/notifications> (eller legger adressen til som
*backup email* og slår på varsling for den).

### Lage en rett manuelt med Mistral

Du kan bruke samme skript lokalt, uten å gå veien om en issue:

```bash
export MISTRAL_API_KEY=...
python3 skript/lag_rett.py --navn "Fiskesuppe" --kategori fisk \
  --anledning "hverdag og helg" --sesong "host og vinter" \
  --onsker "Gjerne med rotgrønnsaker"
python3 bygg.py
```

Les alltid gjennom resultatet før du laster opp – språkmodeller finner av og til
på mengder som ikke stemmer. Du kan bytte modell med `MISTRAL_MODELL`.

### Endre en rett manuelt med Mistral

```bash
export MISTRAL_API_KEY=...
python3 skript/endre_rett.py --rett fiskegrateng \
  --endring "Bytt brokkoli med blomkål, og legg revet ost på toppen"
python3 bygg.py
```

Valgfritt kan du også sende `--kategori`, `--anledning` og `--sesong`. Standarden
er `behold`, altså at feltet står som før. Vil du heller gjøre endringen for
hånd, åpner du bare filen i `retter/` som beskrevet lenger opp.

## Slik velges ukemenyen

- Uken fylles fra mandag til søndag, uten gjentakelser.
- Fredag og lørdag får retter merket `helg`, de andre dagene retter merket `hverdag`.
- Fredag er tacodag. Unntaket er uker der menyen foreslår kebab – da blir det ikke taco i det
  hele tatt den uken.
- Minst tre av dagene er fiskeretter.
- Retter i inneværende årstid (eller `hele-aret`) foretrekkes.
- Ukemenyen er den samme for alle i familien gjennom hele uken.
  **Foreslå middag** gir et helt nytt forslag, og **Bytt** bytter ut én enkelt dag.
