<#
.SYNOPSIS
  One-command installer for addsong on native Windows (PowerShell).

.DESCRIPTION
  Installs Git, yt-dlp, and ffmpeg via winget, downloads the addsong script,
  and creates an "addsong" command that runs it through Git's bundled bash --
  so you can call `addsong "..."` from PowerShell or CMD like any other tool.

.EXAMPLE
  irm https://raw.githubusercontent.com/ado11231/apple-music-pipeline/main/install.ps1 | iex

.NOTES
  Override the download ref with $env:ADDSONG_REF (defaults to main).
#>

$ErrorActionPreference = 'Stop'

$Repo   = 'ado11231/apple-music-pipeline'
$Ref    = if ($env:ADDSONG_REF) { $env:ADDSONG_REF } else { 'main' }
$RawUrl = "https://raw.githubusercontent.com/$Repo/$Ref/addsong"

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

# --- locate Git bash (needed to run the script) ----------------------------
$bash = $null
foreach ($p in @(
    "$env:ProgramFiles\Git\bin\bash.exe",
    "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
    "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe")) {
  if (Test-Path $p) { $bash = $p; break }
}
if (-not $bash) {
  $g = Get-Command git -ErrorAction SilentlyContinue
  if ($g) { $bash = Join-Path (Split-Path (Split-Path $g.Source)) 'bin\bash.exe' }
}
if (-not $bash -or -not (Test-Path $bash)) {
  Die 'Could not locate Git bash. Open a new terminal so Git is on PATH, then re-run.'
}

# --- install the script + a wrapper that invokes it ------------------------
$Dir = Join-Path $env:USERPROFILE 'addsong'
New-Item -ItemType Directory -Force -Path $Dir | Out-Null

Info "Installing addsong -> $Dir"
Invoke-WebRequest -Uri $RawUrl -OutFile (Join-Path $Dir 'addsong') -UseBasicParsing
if (-not (Select-String -Path (Join-Path $Dir 'addsong') -Pattern '^VERSION=' -Quiet)) {
  Die 'Downloaded file does not look like addsong; aborting.'
}

# addsong.cmd: run the bash script through Git bash, forwarding all args.
$cmd = @"
@echo off
"$bash" "%~dp0addsong" %*
"@
Set-Content -Path (Join-Path $Dir 'addsong.cmd') -Value $cmd -Encoding ASCII

# --- PATH (user scope, idempotent) -----------------------------------------
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (($userPath -split ';') -notcontains $Dir) {
  [Environment]::SetEnvironmentVariable('Path', "$userPath;$Dir", 'User')
  Warn "Added $Dir to your PATH. Open a new terminal for it to take effect."
}
$env:Path = "$env:Path;$Dir"   # make it usable in this session for the check

# --- verify ----------------------------------------------------------------
try {
  $v = & (Join-Path $Dir 'addsong.cmd') --version 2>$null
  Ok "Installed: $v"
} catch {
  Ok 'Installed addsong.'
}
Info 'Done. Open a new terminal, then try:  addsong "songname"'
