$ErrorActionPreference = "Stop"

Write-Host "=== Zdrowie: publikacja na GitHub ==="

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "Brak GitHub CLI (gh). Zainstaluj GitHub CLI i uruchom ponownie."
}

gh auth status

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

git add .
git commit -m "Initial commit: Zdrowie desktop app" 2>$null

$repoExists = $false
try {
    gh repo view "Cisowiankaa/Zdrowie" *> $null
    $repoExists = $true
} catch {}

if (-not $repoExists) {
    gh repo create "Cisowiankaa/Zdrowie" --private --source . --remote origin --push
} else {
    if (-not (git remote | Select-String "^origin$")) {
        git remote add origin "https://github.com/Cisowiankaa/Zdrowie.git"
    }
    git push -u origin main
}

Write-Host "Gotowe: https://github.com/Cisowiankaa/Zdrowie"
