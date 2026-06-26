# Manara installer for Windows (PowerShell).
# Clones (or updates) Manara into your Claude Code user-skills folder so it's
# available in every project. Safe to re-run — it updates an existing install.
#
# Run it with:
#   powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = 'Stop'

$Repo = 'https://github.com/OmerWafaey/manara.git'
$Dest = Join-Path $HOME '.claude\skills\manara'

Write-Host 'Manara installer'
Write-Host "  target: $Dest"

# Need git.
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error 'git is not installed. Please install git and re-run.'
    exit 1
}

$SkillsDir = Join-Path $HOME '.claude\skills'
New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null

if (Test-Path (Join-Path $Dest '.git')) {
    Write-Host 'Already installed — pulling the latest version...'
    git -C $Dest pull --ff-only
} elseif (Test-Path $Dest) {
    Write-Error "$Dest exists but is not a git clone. Move or remove it, then re-run."
    exit 1
} else {
    Write-Host 'Cloning Manara...'
    git clone --depth 1 $Repo $Dest
}

Write-Host ''
Write-Host "Done. Manara is installed at: $Dest"
Write-Host 'Next: cd into any project and run  /manara  inside Claude Code.'
Write-Host '(Python 3.7+ is required for the state/guard scripts — standard library only.)'
