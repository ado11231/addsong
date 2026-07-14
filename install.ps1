<#
.SYNOPSIS
  One-command installer for addsong on native Windows (PowerShell).

.DESCRIPTION
  Installs Git, Python, yt-dlp, and ffmpeg via winget, then installs the
  addsong Python package (pipx preferred, pip --user fallback) which puts
  an `addsong` console script on PATH.

.EXAMPLE
  irm https://ado11231.github.io/addsong/install.ps1 | iex

.NOTES
  Override the download ref with $env:ADDSONG_REF (defaults to main).
#>

$ErrorActionPreference = 'Stop'

$Repo = 'ado11231/apple-music-pipeline'
$Ref  = if ($env:ADDSONG_REF) { $env:ADDSONG_REF } else { 'main' }

function Info($m) { Write-Host $m -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "install: $m" -ForegroundColor Red; exit 1 }

Info 'addsong installer  (platform: Windows)'

# --- winget is the bootstrap; everything else rides on it -------------------
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Die @'
winget was not found. Install "App Installer" from the Microsoft Store
(https://aka.ms/getwinget), then re-run this command.
'@
}

# --- dependencies ----------------------------------------------------------
# Map: command to probe -> winget package id to install if missing.
$deps = [ordered]@{
  'git'    = 'Git.Git'
  'python' = 'Python.Python.3.12'
  'yt-dlp' = 'yt-dlp.yt-dlp'
  'ffmpeg' = 'Gyan.FFmpeg'
}
Info 'Checking dependencies ...'
foreach ($cmd in $deps.Keys) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) {
    Ok "$cmd found"
  } else {
    Warn "$cmd missing - installing $($deps[$cmd]) ..."
    winget install --id $deps[$cmd] -e --source winget `
      --accept-package-agreements --accept-source-agreements
  }
}

# Refresh PATH so freshly-installed tools are visible in this session.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + `
            [Environment]::GetEnvironmentVariable('Path', 'User')

# --- download the source archive and install via pipx/pip -------------------
$ArchiveUrl = "https://github.com/$Repo/archive/refs/heads/$Ref.tar.gz"
Info "Downloading addsong source ($Ref) ..."
$Tmp = Join-Path $env:TEMP "addsong-install-$(New-Guid)"
New-Item -ItemType Directory -Force -Path $Tmp | Out-Null
Invoke-WebRequest -Uri $ArchiveUrl -OutFile (Join-Path $Tmp 'addsong.tar.gz') -UseBasicParsing
New-Item -ItemType Directory -Force -Path (Join-Path $Tmp 'src') | Out-Null
tar -xzf (Join-Path $Tmp 'addsong.tar.gz') -C (Join-Path $Tmp 'src') --strip-components=1
$Src = Join-Path $Tmp 'src'

Info 'Installing addsong ...'
if (Get-Command pipx -ErrorAction SilentlyContinue) {
  pipx install $Src
} else {
  python -m pip install --user --upgrade $Src
}

# --- verify ----------------------------------------------------------------
try {
  $v = & addsong --version 2>$null
  Ok "Installed: $v"
} catch {
  Ok 'Installed addsong.'
}
Info 'Done. Open a new terminal, then try:  addsong "songname"'