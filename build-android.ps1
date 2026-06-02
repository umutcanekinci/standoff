# Build the Android debug APK via WSL (Ubuntu). Run from the project root:
#   ./build-android.ps1
# Thin wrapper around tools/build_android.sh — see that script (and docs/android.md)
# for what it does. Pass -InstallDeps the first time (or after changing build deps)
# to (re)install the apt packages + buildozer venv.
param([switch]$InstallDeps)

$ErrorActionPreference = "Stop"

if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Error "WSL not found. Install it with:  wsl --install -d Ubuntu"
    exit 1
}

$env:WSLENV = "INSTALL_DEPS"
$installDeps = if ($InstallDeps) { "1" } else { "0" }

# Run from the repo root so the script's `pwd` is this project under /mnt/c/...
Push-Location $PSScriptRoot
try {
    wsl env INSTALL_DEPS=$installDeps bash tools/build_android.sh
} finally {
    Pop-Location
}
