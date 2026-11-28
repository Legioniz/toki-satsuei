#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN with Actions write permission is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"

response_file="$(mktemp)"
status="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' \
  --request POST \
  --header "Accept: application/vnd.github+json" \
  --header "Authorization: Bearer ${GH_TOKEN}" \
  --header "X-GitHub-Api-Version: 2026-03-10" \
  --header "Content-Type: application/json" \
  --data '{"ref":"main"}' \
  "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/deploy.yml/dispatches")"

if [[ "$status" != "204" ]]; then
  echo "::error::Unable to dispatch the verified GitHub Pages production workflow (HTTP $status)."
  cat "$response_file"
  rm -f "$response_file"
  exit 1
fi

rm -f "$response_file"
echo "Dispatched Build and deploy TOKI SATSUEI for the latest main commit."
