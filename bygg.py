#!/usr/bin/env python3
"""Bygger nettsiden: leser oppskriftene i retter/ og lager docs/data/retter.json.

Kjor:  python3 bygg.py
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys

ROT = pathlib.Path(__file__).resolve().parent
RETTER = ROT / "retter"
UT = ROT / "docs" / "data" / "retter.json"
UT_JS = ROT / "docs" / "data" / "retter.js"

GYLDIG_KATEGORI = {"fisk", "kjott", "kylling", "vegetar"}
GYLDIG_ANLEDNING = {"hverdag", "helg"}
GYLDIG_SESONG = {"hele-aret", "vinter", "var", "sommer", "host"}


def les_frontmatter(tekst: str, filnavn: str) -> tuple[dict, str]:
    if not tekst.startswith("---"):
        raise ValueError(f"{filnavn}: mangler frontmatter (filen må starte med ---)")
    deler = tekst.split("---", 2)
    if len(deler) < 3:
        raise ValueError(f"{filnavn}: frontmatter er ikke avsluttet med ---")
    felt: dict = {}
    for linje in deler[1].strip().splitlines():
        linje = linje.strip()
        if not linje or linje.startswith("#"):
            continue
        if ":" not in linje:
            raise ValueError(f"{filnavn}: skjønner ikke linjen «{linje}»")
        nokkel, verdi = linje.split(":", 1)
        nokkel = nokkel.strip()
        verdi = verdi.strip()
        if verdi.startswith("[") and verdi.endswith("]"):
            felt[nokkel] = [b.strip().strip("\"'") for b in verdi[1:-1].split(",") if b.strip()]
        else:
            felt[nokkel] = verdi.strip("\"'")
    return felt, deler[2].strip()


def md_til_html(md: str) -> str:
    """Enkel markdown -> HTML (overskrifter, lister, avsnitt, fet/kursiv)."""

    def innmat(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        return s

    ut: list[str] = []
    liste: str | None = None

    def lukk() -> None:
        nonlocal liste
        if liste:
            ut.append(f"</{liste}>")
            liste = None

    for linje in md.splitlines():
        stripped = linje.strip()
        if not stripped:
            lukk()
            continue
        if stripped.startswith("#"):
            lukk()
            niva = len(stripped) - len(stripped.lstrip("#"))
            niva = min(max(niva, 1), 6)
            ut.append(f"<h{niva + 1}>{innmat(stripped[niva:].strip())}</h{niva + 1}>")
            continue
        if re.match(r"^[-*]\s+", stripped):
            if liste != "ul":
                lukk()
                ut.append("<ul>")
                liste = "ul"
            ut.append(f"<li>{innmat(re.sub(r'^[-*]\s+', '', stripped))}</li>")
            continue
        if re.match(r"^\d+[.)]\s+", stripped):
            if liste != "ol":
                lukk()
                ut.append("<ol>")
                liste = "ol"
            ut.append(f"<li>{innmat(re.sub(r'^\d+[.)]\s+', '', stripped))}</li>")
            continue
        lukk()
        ut.append(f"<p>{innmat(stripped)}</p>")
    lukk()
    return "\n".join(ut)


def sjekk_ukemeny(retter: list[dict]) -> list[str]:
    """Sjekker at hver sesong har nok retter til en uke med minst tre fiskedager.

    Uken har 5 hverdager (man-tor + sondag) og 2 helgedager (fredag, lordag).
    """
    meldinger = []
    for sesong in ("vinter", "var", "sommer", "host"):
        def utvalg(anledning: str) -> list[dict]:
            passer = [r for r in retter if anledning in r["anledning"]]
            i_sesong = [r for r in passer if "hele-aret" in r["sesong"] or sesong in r["sesong"]]
            return i_sesong or passer

        hverdag = utvalg("hverdag")
        helg = utvalg("helg")
        if len(hverdag) < 5:
            meldinger.append(f"{sesong}: bare {len(hverdag)} hverdagsretter, trenger 5.")
        if len(helg) < 2:
            meldinger.append(f"{sesong}: bare {len(helg)} helgeretter, trenger 2.")

        fisk = {r["slug"] for r in hverdag + helg if r["kategori"] == "fisk"}
        if len(fisk) < 3:
            meldinger.append(f"{sesong}: bare {len(fisk)} fiskeretter tilgjengelig, trenger 3.")
    return meldinger


def main() -> int:
    if not RETTER.is_dir():
        print(f"Finner ikke mappen {RETTER}", file=sys.stderr)
        return 1

    retter = []
    feil: list[str] = []
    for fil in sorted(RETTER.glob("*.md")):
        try:
            felt, brodtekst = les_frontmatter(fil.read_text(encoding="utf-8"), fil.name)
        except ValueError as e:
            feil.append(str(e))
            continue

        navn = felt.get("navn", "").strip()
        if not navn:
            feil.append(f"{fil.name}: mangler «navn»")
            continue

        kategori = (felt.get("kategori") or "annet").lower()
        anledning = [a.lower() for a in felt.get("anledning") or ["hverdag", "helg"]]
        sesong = [s.lower() for s in felt.get("sesong") or ["hele-aret"]]

        if kategori not in GYLDIG_KATEGORI:
            feil.append(f"{fil.name}: ukjent kategori «{kategori}» (gyldige: {', '.join(sorted(GYLDIG_KATEGORI))})")
        if not set(anledning) <= GYLDIG_ANLEDNING:
            feil.append(f"{fil.name}: ugyldig anledning {anledning} (gyldige: hverdag, helg)")
        if not set(sesong) <= GYLDIG_SESONG:
            feil.append(f"{fil.name}: ugyldig sesong {sesong} (gyldige: {', '.join(sorted(GYLDIG_SESONG))})")

        retter.append(
            {
                "slug": fil.stem,
                "navn": navn,
                "kategori": kategori,
                "anledning": anledning,
                "sesong": sesong,
                "tid": felt.get("tid", ""),
                "porsjoner": felt.get("porsjoner", ""),
                "beskrivelse": felt.get("beskrivelse", ""),
                "oppskrift": md_til_html(brodtekst),
            }
        )

    if feil:
        print("Fant feil i oppskriftsfilene:", file=sys.stderr)
        for f in feil:
            print("  - " + f, file=sys.stderr)
        return 1

    antall_fisk = sum(1 for r in retter if r["kategori"] == "fisk")
    for melding in sjekk_ukemeny(retter):
        print("Advarsel: " + melding, file=sys.stderr)

    UT.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(retter, ensure_ascii=False, indent=1)
    UT.write_text(data + "\n", encoding="utf-8")
    # Samme data som vanlig skriptfil, slik at index.html ogsa virker nar den
    # apnes rett fra disk (file://), der nettleseren blokkerer fetch.
    UT_JS.write_text("window.RETTER = " + data + ";\n", encoding="utf-8")
    print(f"Skrev {len(retter)} retter ({antall_fisk} fiskeretter) til {UT.relative_to(ROT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
