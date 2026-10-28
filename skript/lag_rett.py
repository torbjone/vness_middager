#!/usr/bin/env python3
"""Lager en ny fil i retter/ ut fra et godkjent forslag (GitHub-issue).

Skjemafeltene (navn, kategori, anledning, sesong) settes rett inn i frontmatter,
mens selve oppskriften skrives av Mistral i samme stil som de andre rettene.

Kjor:
    MISTRAL_API_KEY=... python3 skript/lag_rett.py --issue-fil issue.md
    MISTRAL_API_KEY=... python3 skript/lag_rett.py --navn "Fiskesuppe" --kategori fisk

Skriver stien til den nye filen pa siste linje av stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROT = pathlib.Path(__file__).resolve().parent.parent
RETTER = ROT / "retter"

API_URL = "https://api.mistral.ai/v1/chat/completions"
MODELL = os.environ.get("MISTRAL_MODELL", "mistral-large-latest")

GYLDIG_KATEGORI = {"fisk", "kjott", "kylling", "vegetar"}
GYLDIG_ANLEDNING = {"hverdag", "helg"}
GYLDIG_SESONG = {"hele-aret", "vinter", "var", "sommer", "host"}

TEGN = {
    "æ": "ae", "ø": "o", "å": "a",
    "é": "e", "è": "e", "ê": "e", "ü": "u", "ö": "o", "ä": "a",
}


def slugify(navn: str) -> str:
    s = navn.lower().strip()
    for fra, til in TEGN.items():
        s = s.replace(fra, til)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "ny-rett"


SKJEMA_NY_RETT = {
    "hva heter retten?": "navn",
    "kategori": "kategori",
    "nar passer retten?": "anledning",
    "sesong": "sesong",
    "onsker eller notater": "onsker",
}


def les_skjema(tekst: str, noklene: dict[str, str] | None = None) -> dict[str, str]:
    """Plukker feltene ut av et utfylt GitHub-issue-skjema.

    Skjemaet kommer som «### Overskrift» etterfulgt av verdien.
    """
    felt: dict[str, str] = {}
    noklene = noklene or SKJEMA_NY_RETT
    gjeldende: str | None = None
    linjer: list[str] = []

    def lagre() -> None:
        if gjeldende:
            verdi = "\n".join(linjer).strip()
            if verdi and verdi != "_No response_":
                felt[gjeldende] = verdi

    for linje in tekst.splitlines():
        if linje.startswith("###"):
            lagre()
            linjer = []
            overskrift = linje.lstrip("#").strip().lower()
            for fra, til in TEGN.items():
                overskrift = overskrift.replace(fra, til)
            gjeldende = noklene.get(overskrift)
            continue
        if gjeldende:
            linjer.append(linje)
    lagre()
    return felt


def normaliser_liste(verdi: str, gyldige: set[str], standard: list[str]) -> list[str]:
    biter = [b for b in re.split(r"[,\s]+og[,\s]+|[,\s]+", verdi.lower()) if b]
    valgt = [b for b in biter if b in gyldige]
    return valgt or standard


SYSTEMPROMPT = """\
Du skriver middagsoppskrifter for en liten familienettside. Oppskriftene skal
kunne folges av en 10-aring under oppsyn av en voksen. Skriv pa norsk bokmal.

Regler:
- Oppskriften er til 5 porsjoner.
- Skriv korte, konkrete setninger. Ett handgrep per punkt.
- Forste steg er alltid at man vasker hendene.
- Bruk metriske mal (g, dl, ts, ss) og grader i celsius.
- Ikke bruk emoji, ikke bruk fet eller kursiv skrift.

Svar KUN med gyldig JSON pa dette formatet, uten kodeblokk rundt:
{
  "tid": "30 min",
  "beskrivelse": "En setning som beskriver retten.",
  "ingredienser": ["1,2 kg poteter", "4 gulrotter"],
  "fremgangsmate": ["Vask hendene.", "Sett pa potetene."],
  "tips": ["Ett kort tips."]
}
"""


def kall_mistral(systemprompt: str, bruker: str) -> dict:
    """Sender en forespørsel til Mistral og returnerer svaret som JSON."""
    nokkel = os.environ.get("MISTRAL_API_KEY")
    if not nokkel:
        raise SystemExit("Mangler MISTRAL_API_KEY")

    kropp = json.dumps(
        {
            "model": MODELL,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": systemprompt},
                {"role": "user", "content": bruker},
            ],
        }
    ).encode("utf-8")

    forespor = urllib.request.Request(
        API_URL,
        data=kropp,
        headers={
            "Authorization": f"Bearer {nokkel}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(forespor, timeout=180) as svar:
            data = json.loads(svar.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Mistral svarte {e.code}: {e.read().decode('utf-8', 'replace')}")

    innhold = data["choices"][0]["message"]["content"].strip()
    innhold = re.sub(r"^```(?:json)?|```$", "", innhold, flags=re.MULTILINE).strip()
    return json.loads(innhold)


def sporr_mistral(navn: str, kategori: str, onsker: str) -> dict:
    bruker = f"Rett: {navn}\nKategori: {kategori}"
    if onsker:
        bruker += f"\nOnsker fra den som foreslo retten:\n{onsker}"
    return kall_mistral(SYSTEMPROMPT, bruker)


def punktliste(verdier) -> str:
    if isinstance(verdier, str):
        verdier = [verdier]
    return "\n".join(f"- {str(v).strip()}" for v in verdier if str(v).strip())


def nummerliste(verdier) -> str:
    if isinstance(verdier, str):
        verdier = [verdier]
    rene = [str(v).strip() for v in verdier if str(v).strip()]
    rene = [re.sub(r"^\d+[.)]\s*", "", v) for v in rene]
    return "\n".join(f"{i}. {v}" for i, v in enumerate(rene, 1))


def lag_tekst(
    navn: str,
    kategori: str,
    anledning: list[str],
    sesong: list[str],
    svar: dict,
) -> str:
    """Setter sammen hele md-filen av frontmatter og svaret fra Mistral."""
    tid = str(svar.get("tid", "")).strip() or "30 min"
    beskrivelse = " ".join(str(svar.get("beskrivelse", "")).split())
    ingredienser = punktliste(svar.get("ingredienser", []))
    fremgangsmate = nummerliste(svar.get("fremgangsmate", []))
    tips = punktliste(svar.get("tips", []))

    if not ingredienser or not fremgangsmate:
        raise ValueError("Mistral svarte uten ingredienser eller fremgangsmate.")

    tekst = (
        "---\n"
        f"navn: {navn}\n"
        f"kategori: {kategori}\n"
        f"anledning: [{', '.join(anledning)}]\n"
        f"sesong: [{', '.join(sesong)}]\n"
        f"tid: {tid}\n"
        "porsjoner: 5\n"
        f"beskrivelse: {beskrivelse}\n"
        "---\n\n"
        "## Ingredienser\n\n"
        f"{ingredienser}\n\n"
        "## Slik gjør du det\n\n"
        f"{fremgangsmate}\n"
    )
    if tips:
        tekst += f"\n## Tips\n\n{tips}\n"
    return tekst


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--issue-fil", help="fil med teksten fra GitHub-issuen")
    p.add_argument("--navn")
    p.add_argument("--kategori")
    p.add_argument("--anledning", default="hverdag")
    p.add_argument("--sesong", default="hele-aret")
    p.add_argument("--onsker", default="")
    args = p.parse_args()

    felt: dict[str, str] = {}
    if args.issue_fil:
        felt = les_skjema(pathlib.Path(args.issue_fil).read_text(encoding="utf-8"))

    navn = (args.navn or felt.get("navn", "")).strip()
    if not navn:
        print("Fant ikke navnet pa retten i forslaget.", file=sys.stderr)
        return 1

    kategori = (args.kategori or felt.get("kategori", "")).strip().lower()
    if kategori not in GYLDIG_KATEGORI:
        print(
            f"Ugyldig kategori «{kategori}» (gyldige: {', '.join(sorted(GYLDIG_KATEGORI))})",
            file=sys.stderr,
        )
        return 1

    anledning = normaliser_liste(
        felt.get("anledning") or args.anledning, GYLDIG_ANLEDNING, ["hverdag"]
    )
    sesong = normaliser_liste(
        felt.get("sesong") or args.sesong, GYLDIG_SESONG, ["hele-aret"]
    )
    onsker = (args.onsker or felt.get("onsker", "")).strip()

    slug = slugify(navn)
    mal = RETTER / f"{slug}.md"
    if mal.exists():
        print(f"retter/{slug}.md finnes allerede.", file=sys.stderr)
        return 2

    svar = sporr_mistral(navn, kategori, onsker)

    try:
        tekst = lag_tekst(navn, kategori, anledning, sesong, svar)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    mal.write_text(tekst, encoding="utf-8")
    print(f"Skrev {mal.relative_to(ROT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
