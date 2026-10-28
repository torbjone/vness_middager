#!/usr/bin/env bash
# Bygger nettsiden og laster den opp til vness.no/middager.
#
# Bruk:   ./last-opp.sh
# Krever: lftp (sudo apt install lftp) og en utfylt .env-fil (se .env.eksempel).

set -euo pipefail

ROT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROT"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a; . ./.env; set +a
else
  echo "Fant ingen .env – kopier .env.eksempel til .env og fyll inn." >&2
  exit 1
fi

: "${FTP_VERT:?Mangler FTP_VERT i .env}"
: "${FTP_BRUKER:?Mangler FTP_BRUKER i .env}"
: "${FTP_PASSORD:?Mangler FTP_PASSORD i .env}"
FJERNMAPPE="${FJERNMAPPE:-/www/middager}"

echo "==> Bygger..."
python3 bygg.py

if ! command -v lftp >/dev/null 2>&1; then
  echo "lftp er ikke installert. Kjør: sudo apt install lftp" >&2
  exit 1
fi

echo "==> Laster opp docs/ til ${FTP_VERT}:${FJERNMAPPE}"
lftp -c "
set ftp:ssl-force true;
set ftp:ssl-protect-data true;
set ssl:verify-certificate no;
open -u '${FTP_BRUKER}','${FTP_PASSORD}' '${FTP_VERT}';
mirror --reverse --delete --verbose --parallel=4 docs/ '${FJERNMAPPE}';
"

echo "==> Ferdig. Se https://vness.no/middager"
