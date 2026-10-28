#!/usr/bin/env python3
"""Endrer en rett som allerede finnes i retter/, ut fra et godkjent forslag.

Skriptet finner riktig fil, sender den eksisterende oppskriften og den onskede
endringen til Mistral, og skriver filen pa nytt i samme stil. Filnavnet (slug)
endres aldri, slik at lenker og ukemenyen fortsetter a virke.

Kjor:
    MISTRAL_API_KEY=... python3 skript/endre_rett.py --issue-fil forslag.md
    MISTRAL_API_KEY=... python3 skript/endre_rett.py --rett pizza --endring "Mer ost"
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lag_rett import (  # noqa: E402
    GYLDIG_ANLEDNING,
    GYLDIG_KATEGORI,
    GYLDIG_SESONG,
    ROT,
    RETTER,
    kall_mistral,
    lag_tekst,
    les_skjema,
    normaliser_liste,
    slugify,
)

SKJEMA_ENDRE_RETT = {
    "hvilken rett gjelder det?": "rett",
    "hva skal endres?": "endring",
    "kategori": "kategori",
    "nar passer retten?": "anledning",
    "sesong": "sesong",
}

SYSTEMPROMPT = """\
Du vedlikeholder middagsoppskrifter for en liten familienettside. Oppskriftene
skal kunne folges av en 10-aring under oppsyn av en voksen. Skriv pa norsk bokmal.

Du far en oppskrift som allerede finnes, og en onsket endring. Gjor endringen,
men la resten av oppskriften sta mest mulig som for. Ikke skriv om steg som ikke
berores av endringen.

Regler:
- Oppskriften er til 5 porsjoner.
- Skriv korte, konkrete setninger. Ett handgrep per punkt.
- Forste steg er alltid at man vasker hendene.
- Bruk metriske mal (g, dl, ts, ss) og grader i celsius.
- Ikke bruk emoji, ikke bruk fet eller kursiv skrift.

Svar KUN med gyldig JSON pa dette formatet, uten kodeblokk rundt, og ta med hele
den oppdaterte oppskriften (ikke bare det som er endret):
{
  "tid": "30 min",
  "beskrivelse": "En setning som beskriver retten.",
  "ingredienser": ["1,2 kg poteter", "4 gulrotter"],
  "fremgangsmate": ["Vask hendene.", "Sett pa potetene."],
  "tips": ["Ett kort tips."]
}
"""


def les_frontmatter(tekst: str) -> tuple[dict, str]:
    """Enkel frontmatter-leser, samme format som bygg.py forventer."""
    deler = tekst.split("---", 2)
    if not tekst.startswith("---") or len(deler) < 3:
        raise ValueError("filen mangler frontmatter")
    felt: dict = {}
    for linje in deler[1].strip().splitlines():
        linje = linje.strip()
        if not linje or linje.startswith("#") or ":" not in linje:
            continue
        nokkel, verdi = linje.split(":", 1)
        nokkel, verdi = nokkel.strip(), verdi.strip()
        if verdi.startswith("[") and verdi.endswith("]"):
            felt[nokkel] = [b.strip().strip("\"'") for b in verdi[1:-1].split(",") if b.strip()]
        else:
            felt[nokkel] = verdi.strip("\"'")
    return felt, deler[2].strip()


def finn_rett(navn: str) -> pathlib.Path | None:
    """Finner md-filen ut fra navn, filnavn eller en del av navnet."""
    sok = navn.strip().lower().removesuffix(".md")
    direkte = RETTER / f"{slugify(sok)}.md"
    if direkte.exists():
        return direkte

    kandidater = []
    for fil in sorted(RETTER.glob("*.md")):
        try:
            felt, _ = les_frontmatter(fil.read_text(encoding="utf-8"))
        except ValueError:
            continue
        rettnavn = str(felt.get("navn", "")).lower()
        if rettnavn == sok:
            return fil
        if sok and (sok in rettnavn or sok in fil.stem):
            kandidater.append(fil)
    if len(kandidater) == 1:
        return kandidater[0]
    return None


def velg(ny: str, gammel, gyldige: set[str], standard: list[str]) -> list[str]:
    """Bruker det nye valget hvis det er satt og ikke «behold»."""
    ny = (ny or "").strip().lower()
    if not ny or ny == "behold":
        return [str(v).lower() for v in (gammel or standard)] or standard
    return normaliser_liste(ny, gyldige, standard)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--issue-fil", help="fil med teksten fra GitHub-issuen")
    p.add_argument("--rett", help="navn eller filnavn pa retten som skal endres")
    p.add_argument("--endring", default="", help="hva som skal endres")
    p.add_argument("--kategori", default="behold")
    p.add_argument("--anledning", default="behold")
    p.add_argument("--sesong", default="behold")
    args = p.parse_args()

    felt: dict[str, str] = {}
    if args.issue_fil:
        felt = les_skjema(
            pathlib.Path(args.issue_fil).read_text(encoding="utf-8"), SKJEMA_ENDRE_RETT
        )

    rettnavn = (args.rett or felt.get("rett", "")).strip()
    if not rettnavn:
        print("Fant ikke hvilken rett det gjelder.", file=sys.stderr)
        return 1

    endring = (args.endring or felt.get("endring", "")).strip()
    if not endring:
        print("Fant ingen beskrivelse av hva som skal endres.", file=sys.stderr)
        return 1

    fil = finn_rett(rettnavn)
    if fil is None:
        print(f"Finner ingen rett som heter «{rettnavn}». Rettene vi har:", file=sys.stderr)
        for annen in sorted(RETTER.glob("*.md")):
            print(f"  - {annen.stem}", file=sys.stderr)
        return 2

    gammel_tekst = fil.read_text(encoding="utf-8")
    gammelt_felt, _ = les_frontmatter(gammel_tekst)

    navn = str(gammelt_felt.get("navn", "")).strip() or rettnavn

    kategori = (args.kategori or felt.get("kategori") or "behold").strip().lower()
    if not kategori or kategori == "behold":
        kategori = str(gammelt_felt.get("kategori", "")).strip().lower()
    if kategori not in GYLDIG_KATEGORI:
        print(
            f"Ugyldig kategori «{kategori}» (gyldige: {', '.join(sorted(GYLDIG_KATEGORI))})",
            file=sys.stderr,
        )
        return 1

    anledning = velg(
        felt.get("anledning") or args.anledning,
        gammelt_felt.get("anledning"),
        GYLDIG_ANLEDNING,
        ["hverdag"],
    )
    sesong = velg(
        felt.get("sesong") or args.sesong,
        gammelt_felt.get("sesong"),
        GYLDIG_SESONG,
        ["hele-aret"],
    )

    bruker = (
        f"Rett: {navn}\nKategori: {kategori}\n\n"
        f"Onsket endring:\n{endring}\n\n"
        f"Oppskriften slik den er i dag:\n{gammel_tekst}"
    )
    svar = kall_mistral(SYSTEMPROMPT, bruker)

    try:
        ny_tekst = lag_tekst(navn, kategori, anledning, sesong, svar)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    if ny_tekst == gammel_tekst:
        print(f"{fil.relative_to(ROT)} er uendret.", file=sys.stderr)
        return 3

    fil.write_text(ny_tekst, encoding="utf-8")
    print(f"Endret {fil.relative_to(ROT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
