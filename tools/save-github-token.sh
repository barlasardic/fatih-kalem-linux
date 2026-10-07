#!/usr/bin/env bash
# Save a GitHub token for pushing, without it ever touching shell history,
# the chat log, or a file on disk.
#
#   ./tools/save-github-token.sh
#
# The token is typed with echo disabled and goes straight into git's in-memory
# credential cache (4 hours). A fine-grained PAT with "Contents: read and
# write" on this repository is enough - it expires, so nothing long-lived is
# left behind.
set -euo pipefail

DEFAULT_USER="barlasardic"
HOST="github.com"

read -rsp "GitHub token (gizli, görünmez): " TOKEN
echo
if [ -z "${TOKEN}" ]; then
  echo "token boş - iptal edildi" >&2
  exit 1
fi

read -rp "Kullanıcı adı [${DEFAULT_USER}]: " USER
USER="${USER:-${DEFAULT_USER}}"

printf 'protocol=https\nhost=%s\nusername=%s\npassword=%s\n' \
  "${HOST}" "${USER}" "${TOKEN}" | git credential approve

unset TOKEN

echo
echo "Kaydedildi (bellekte, 4 saat). Şimdi push edebilirim."
echo "Bitince temizlemek için:  git credential reject"