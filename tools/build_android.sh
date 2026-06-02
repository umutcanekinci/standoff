#!/usr/bin/env bash
# Build the Standoff Android debug APK inside WSL/Linux (buildozer is Linux-only).
#
# From the project root, either:
#   ./build-android.ps1            # Windows PowerShell wrapper, o
#   wsl bash tools/build_android.sh
#
# Assumes an Ubuntu/Debian WSL distro. First run is slow (downloads the Android
# SDK/NDK and cross-compiles Python + SDL2 + pygame for ARM); later runs reuse the
# ~/.buildozer cache. Set INSTALL_DEPS=1 to force the apt/pip step to re-run.
set -euo pipefail

# Install buildozer at USER level, not in a venv: python-for-android installs its
# own host deps with `pip install --user`, which pip refuses from inside a venv.
# PEP-668 "externally managed" is bypassed for these dev tools via
# PIP_BREAK_SYSTEM_PACKAGES (this WSL is a dedicated build box); exporting it also
# carries into p4a's own `pip --user` calls so they clear the same hurdle.
export PIP_BREAK_SYSTEM_PACKAGES=1
export PATH="$HOME/.local/bin:$PATH"

# python-for-android's "Installing pure Python modules" step spins up a throwaway
# venv and runs `pip install -U pip` in it (hardcoded in p4a's build.py). The
# current newest pip (26.1.2) ships a self-inconsistent vendored resolvelib —
# `pip install` then dies with "cannot import name 'RequirementInformation' from
# pip._vendor.resolvelib.structs", failing the build right before packaging. Pin
# that upgrade to pip <25 (older, consistent resolvelib): p4a copies os.environ
# into the venv's build env, so PIP_CONSTRAINT reaches it.
PIP_CONSTRAINTS_FILE="$HOME/.standoff-pip-constraints.txt"
echo 'pip<25' > "$PIP_CONSTRAINTS_FILE"
export PIP_CONSTRAINT="$PIP_CONSTRAINTS_FILE"

if ! command -v buildozer >/dev/null 2>&1 || [ "${INSTALL_DEPS:-0}" = "1" ]; then
  echo ">> Installing build dependencies (needs sudo)…"
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends \
    python3 python3-dev python3-pip git zip unzip rsync ccache cmake \
    openjdk-17-jdk autoconf automake libtool libltdl-dev pkg-config \
    zlib1g-dev libncurses-dev libffi-dev libssl-dev build-essential
  python3 -m pip install --user --upgrade pip
  python3 -m pip install --user buildozer cython
fi

BUILDOZER="$(command -v buildozer)"
SRC="$(pwd)"

# Building on /mnt/c (NTFS) is slow and can break p4a's symlinks. If we're unde
# /mnt, mirror the project into the Linux home fs and build there.
BUILD_DIR="$SRC"
if [[ "$SRC" == /mnt/* ]]; then
  BUILD_DIR="$HOME/standoff-build"
  echo ">> Mirroring project off NTFS into $BUILD_DIR (faster, symlink-safe)…"
  mkdir -p "$BUILD_DIR"
  # NOTE: 'recipes' is excluded — it's synced + verified separately, because the
  # NTFS(9p)->WSL view can lag a just-written file by a beat, and a recipe that
  # mirrors empty silently falls back to p4a's default (wrong Python/pygame).
  rsync -a --delete \
    --exclude '.venv' --exclude '.git' --exclude '.buildozer' \
    --exclude 'bin' --exclude '__pycache__' --exclude '.pytest_cache' \
    --exclude 'recipes' \
    "$SRC/" "$BUILD_DIR/"

  # Sync the local p4a recipes separately and VERIFY the copy landed. The 9p
  # (/mnt/c) view can serve a just-edited file as stale/empty for a beat; a recipe
  # that mirrors wrong silently falls back to p4a's default (e.g. stale pygame
  # 2.1.0 instead of our pygame-ce override), wasting a full build. Retry the copy
  # until a sentinel from the current recipe is present.
  for attempt in 1 2 3 4 5; do
    rm -rf "$BUILD_DIR/recipes"
    cp -r "$SRC/recipes" "$BUILD_DIR/recipes"
    if grep -q '_strip_build_system' "$BUILD_DIR/recipes/pygame/__init__.py" 2>/dev/null; then
      echo ">> recipes synced and verified"
      break
    fi
    echo ">> recipe view looked stale (attempt $attempt/5), retrying…"
    sleep 2
    if [ "$attempt" = "5" ]; then
      echo "!! Could not verify recipes/pygame sync off the NTFS mount." >&2
      exit 1
    fi
  done
fi

cd "$BUILD_DIR"
echo ">> Running buildozer in $BUILD_DIR …"
# Auto-accept the Android SDK licence prompts so the build runs unattended. `yes`
# is killed by SIGPIPE when buildozer exits, so read buildozer's REAL exit code
# from PIPESTATUS instead of letting pipefail report the broken pipe as failure.
set +o pipefail
yes | "$BUILDOZER" -v android debug
rc=${PIPESTATUS[1]}
set -o pipefail
if [ "$rc" -ne 0 ]; then
  echo ">> buildozer exited with code $rc"
  exit "$rc"
fi

APK="$(ls -t "$BUILD_DIR"/bin/*.apk | head -n1)"
echo ">> Built: $APK"
if [ "$BUILD_DIR" != "$SRC" ]; then
  mkdir -p "$SRC/bin"
  cp "$APK" "$SRC/bin/"
  echo ">> Copied to $SRC/bin/$(basename "$APK")"
fi
echo ">> Done. Install with:  adb install -r \"$SRC/bin/$(basename "$APK")\""
