# itch.io page kit — Standoff

Everything needed to stand up an itch.io page. itch has no API to *create* a
page, so the page itself is made once in the browser at **itch.io/game/new**;
all the content below is paste-ready, and builds can be uploaded by drag-and-drop
(butler is optional — see the end).

---

## 1. Page setup (itch.io/game/new)

| Field | Value |
|---|---|
| **Title** | Standoff |
| **Project URL** | `standoff` (→ umutcanekinci.itch.io/standoff) |
| **Short description / tagline** | Co-op top-down zombie shooter — host a room, grab a friend, survive the swarm. |
| **Classification** | Games |
| **Kind of project** | Downloadable |
| **Release status** | Released |
| **Pricing** | No payments (free) — *or* "$0 or donate" if you want a tip jar |

### Metadata (right-hand sidebar)

- **Genre:** Action / Shooter
- **Tags:** `multiplayer`, `co-op`, `top-down`, `shooter`, `zombies`, `pygame`, `arcade`, `lan`, `local-multiplayer`, `2d`
- **Average session:** A few minutes
- **Multiplayer:** Server-based networked multiplayer; Local multiplayer (LAN)
- **Player count:** 1–4
- **Platforms:** Windows, Linux, Android *(desktop runs via Python; Android is a sideloadable APK — see uploads)*
- **Inputs:** Keyboard, Mouse, Touchscreen

---

## 2. Description (paste into the page body)

**Standoff** is a 2D networked multiplayer top-down zombie shooter. Pick one of
8 characters, host or join a room over the network — or play solo offline — then
move, aim, and shoot your way through endless waves of zombies on a
Tiled-authored map.

**Features**

- 🎮 **8 playable characters**, twin-stick-style WASD + mouse aim, hold-to-auto-fire with kickback and muzzle flash.
- 🌐 **Online multiplayer** — host or join rooms (up to 4 players) with a public room browser, host-from-game, and **join-in-progress**: drop straight into a match that's already running.
- 🧟 **Endless zombies** that home in on the nearest player and swarm your base.
- 🕹️ **Offline mode** for solo play — no server needed.
- 📱 **Android build** with on-screen touch controls (sideload the APK).

**How to play**

- **Desktop:** download the source from [GitHub](https://github.com/umutcanekinci/standoff) and run `uv sync` then `uv run python __main__.py`. One player runs `server.py` to host; others Connect by IP.
- **Android:** download the APK below, enable "install from unknown sources," and install. Connect to a desktop host on your LAN.

*Built with [pygame-ce](https://github.com/pygame-community/pygame-ce). Character and tile art from [Kenney](https://www.kenney.nl/assets/topdown-shooter).*

---

## 3. Uploads

| File | Channel / label | itch settings |
|---|---|---|
| `bin/standoff-0.1.0-arm64-v8a_armeabi-v7a-debug.apk` | Android APK | Tick **"This file will be played in the browser"** = OFF; set platform **Android** |
| *(optional)* a Windows `.exe` (PyInstaller) | Windows | set platform **Windows** |

> The APK is the only one-click-playable artifact today. Desktop currently means
> "clone + run Python," so for now the page can link to GitHub for desktop and
> offer the APK as the download. A standalone Windows `.exe` (via PyInstaller) is
> a nice future addition but isn't built yet.

### Images to upload

- **Cover image** (itch needs **630×500** ideally): none cropped to that ratio yet — crop one from `docs/screenshots/03_gameplay.png`, or make a simple title banner.
- **Screenshots** (drag these into the page gallery):
  - `docs/screenshots/03_gameplay.png` — the swarm (lead image)
  - `docs/screenshots/01_main_menu.png`
  - `docs/screenshots/02_character_select.png`

---

## 4. Uploading builds without the browser (optional — butler)

butler is itch's CLI for pushing builds. It couldn't be installed in this repo's
environment (its CDN host `broth.itch.ovh` didn't resolve), but you can install
it yourself and then pushing a new build is one command:

```bash
# install: https://itch.io/docs/butler/installing.html  (or via the itch app)
butler login
butler push bin/standoff-0.1.0-arm64-v8a_armeabi-v7a-debug.apk umutcanekinci/standoff:android
```

Each later release is just another `butler push` to the same `android` channel —
itch versions them automatically. Until then, drag-and-drop in the browser does
the same job.
