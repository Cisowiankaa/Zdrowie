#!/usr/bin/env bash
set -euo pipefail

echo "=== Zdrowie: publikacja na GitHub ==="

command -v gh >/dev/null || {
  echo "Brak GitHub CLI (gh). Zainstaluj GitHub CLI i uruchom ponownie."
  exit 1
}

gh auth status

if [ ! -d .git ]; then
  git init
  git branch -M main
fi

git add .
git commit -m "Initial commit: Zdrowie desktop app" || true

if gh repo view "Cisowiankaa/Zdrowie" >/dev/null 2>&1; then
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/Cisowiankaa/Zdrowie.git"
  git push -u origin main
else
  gh repo create "Cisowiankaa/Zdrowie" --private --source . --remote origin --push
fi

echo "Gotowe: https://github.com/Cisowiankaa/Zdrowie"
