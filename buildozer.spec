# Buildozer config — Android client build for Standoff.
#
# The phone is a CLIENT ONLY: main.py launches app.game.Game and never imports
# app.server_app, so tkinter and the host path stay out of the APK. The desktop
# server (server.py / src/app/server_app.py) is excluded below.
#
# Build (needs Linux or WSL with the Android SDK/NDK that buildozer fetches):
#   pipx install buildozer            # or: pip install buildozer
#   buildozer -v android debug        # produces bin/standoff-*-debug.apk
#   buildozer android deploy run logcat   # install + run + tail logs on a device

[app]
title = Standoff
package.name = standoff
package.domain = com.umutcanekinci

# Project root holds main.py; assets/ and config/ are bundled by extension below.
source.dir = .

# Files to package: code + every asset type the game loads at runtime. Anything
# with these extensions under source.dir is included regardless of folder, so the
# tmx maps, tilesets, character pngs, ogg/wav sounds, fonts and the asset/panel
# YAML manifests all come along.
source.include_exts = py,png,jpg,jpeg,ogg,wav,ttf,otf,tmx,tsx,yaml,yml,json,db,txt

# Keep desktop-only and dev-only trees out of the APK.
source.exclude_dirs = tests,bench,tools,docs,.venv,.git,.github,__pycache__,bin,.buildozer
# Desktop server entry points (tkinter) and the desktop launcher.
source.exclude_patterns = server.py,__main__.py,src/app/server_app.py

version = 0.1.1

# python3 + the libs the client imports. NOTE: this uses python-for-android's
# `pygame` recipe (SDL2). The project targets pygame-ce, which is API-compatible;
# if the build needs the CE fork specifically, point a local recipe at it or
# override with `--requirements`. pytmx and pyyaml are pure-Python and build fine.
requirements = python3,pygame,pytmx,pyyaml,colorama

orientation = landscape
fullscreen = 1

# Multiplayer needs the network; no other permissions required (client-only).
android.permissions = INTERNET

android.api = 34
# 26 (Android 8.0), not 24: CPython 3.12's grp module calls setgrent/getgrent/
# endgrent, which Bionic only declares at API 26+. Covers virtually all devices.
android.minapi = 26
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = 1

# SDL2 bootstrap is what the pygame recipe uses; stated explicitly for clarity.
p4a.bootstrap = sdl2

# Local recipe override: builds pygame-ce 2.5.7 (Python 3.14-compatible) in place
# of p4a's stale pygame 2.1.0 recipe. See recipes/pygame/__init__.py.
p4a.local_recipes = ./recipes

# Optional branding — drop files here and uncomment when ready.
# icon.filename = %(source.dir)s/assets/images/icon.png
# presplash.filename = %(source.dir)s/assets/images/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
