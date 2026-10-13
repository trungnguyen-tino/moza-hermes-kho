#!/usr/bin/env bash
# The add-ons' own tests (plugins against fake Google / portal, skills against the portal's rules).
# The review itself is Moza Connect's lab scan, per add-on and per commit (README, "Quy trình duyệt").
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$root/.venv/bin/python" ]]; then
  uv venv -q --python 3.12 "$root/.venv"
  uv pip install -q --python "$root/.venv/bin/python" 'pytest>=8,<9' 'pyyaml>=6,<7'
fi
cd "$root/tests"
"$root/.venv/bin/python" -m pytest -q -p no:cacheprovider
