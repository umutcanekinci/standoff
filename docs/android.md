# Android port roadmap

**Target:** a native Android APK, phone acts as a **client only** (a desktop/VPS
hosts the server; `server_app.py`'s tkinter admin never ships to Android).

**Toolchain:** [buildozer] + [python-for-android] with the **SDL2 bootstrap**.
Chosen over pygbag (web/WASM) so raw **TCP sockets keep working** — the existing
`pygame_core/net/transport.py` survives nearly unchanged. The cost is build
fiddliness (the pygame-ce recipe on p4a is the weak link), not an architecture
rewrite.

[buildozer]: https://buildozer.readthedocs.io
[python-for-android]: https://python-for-android.readthedocs.io

## Why this project is a good fit
- Mobs are simulated **server-side** (`game_server._simulate_mobs`); the client
  only interpolates — right call for a CPU-weak phone.
- Transport is decoupled via callbacks, so the socket layer is swappable.
- Display already uses `pygame.FULLSCREEN | pygame.SCALED`, which scales to a
  phone screen (lock landscape).

## Steps (in order)

1. **Input abstraction — DONE.** `gameplay/controls.py` defines a `Controls`
   interface read by the local `Player` (move / aim / fire intent). Desktop uses
   `KeyboardMouseControls` (unchanged feel); `TouchControls` is a scaffold to
   fill. Nothing else in `Player`/the scene knows about the device.

2. **Touch backend — DONE.** `TouchControls` in `gameplay/controls.py`: an
   analog left-thumb virtual joystick (`movement()`), auto-aim at the nearest mob
   (`aim_angle()`), and a fire button (`is_firing()`), driven by
   `pygame.FINGER*` events and drawn as a corner HUD. `make_controls()` selects it
   on Android (or on desktop when `STANDOFF_TOUCH=1`, which also mirrors the mouse
   onto the HUD so it can be play-tested without a phone). UI sprites are sliced
   from the `MobileControls` Unity atlas (`style-a`) into
   `assets/images/MobileControls/{joystick_base,joystick_knob,fire_button}.png`,
   registered in `config/assets.yaml` as `touch_*`.

3. **Menus & text entry — DONE.** SDL maps touches to mouse events, so the
   button menus / death screen already work. Text fields (`ui/widgets.py`
   `InputObject` — the name field and the server IP/port) now consume `TEXTINPUT`
   instead of `KEYDOWN.unicode`, and `LobbyScene._sync_soft_keyboard()` raises the
   on-screen keyboard (`pygame.key.start_text_input` + `set_text_input_rect`) while
   a field is focused and lowers it otherwise — driven once per frame off each
   field's `editing` flag, so it's immune to per-widget click ordering.

4. **Display/orientation.** Lock landscape, letterbox non-16:9 ratios.

5. **Networking hardening.**
   - **pickle -> JSON — DONE.** The wire codec is now `TypedJSONCodec`, built in
     one place (`net/wire.py::make_protocol`, shared by server, client, and the
     e2e tests). `PlayerInfo`/`Room`/`MobInfo` cross via `to_dict`/`from_dict`
     (with `__type__` tags); JSON's quirks are handled explicitly — the
     `PlayerInfo<->Room` cycle is broken with `include_room`, and `base_points`
     travels as `[[n,[x,y]],...]` so its int keys / tuple points survive (the
     server also re-coerces `CREATE_ROOM` keys). No more RCE-on-unpickle.
   - **Server-address menu — DONE.** A `server_menu` panel (reached via SERVER on
     the game-type menu) takes IP + port, pre-filled with the current defaults
     (`CLIENT_IP`/`CLIENT_PORT`), and `Game.connect_to_server()` re-dials there.
     Status is polled async; on success it re-announces the player (`SET_PLAYER`)
     and returns to the now-enabled create/join options. Editable on Android via
     the soft keyboard (step 3).

6. **Packaging — config DONE, APK not yet built.** `buildozer.spec` is in the
   repo (client-only `main.py` entry, `INTERNET` permission, landscape, assets
   bundled by extension, desktop server excluded); `constants.py` host resolution
   is device-safe (loopback fallback).

   **Buildozer only runs on Linux** — note that an SDL install on Windows does
   *not* help (it cross-compiles its own SDL for ARM). Two ways to get an APK:

   - **Local WSL2 (recommended here — Ubuntu is installed):** run the helper,
     which installs deps into an isolated venv, mirrors the project off NTFS into
     the Linux fs (faster + symlink-safe), builds, and copies the APK back to
     `bin/`:
     ```powershell
     ./build-android.ps1                 # first run: ./build-android.ps1 -InstallDeps
     ```
     (or directly: `wsl bash tools/build_android.sh`). Then
     `adb install -r bin/standoff-*-debug.apk`.
   - **CI (no local Linux):** `.github/workflows/build-android.yml` builds the
     debug APK on an Ubuntu runner and uploads it as an artifact. Run it from the
     Actions tab (`workflow_dispatch`) or by pushing a `v*` tag.

   Risk to watch (will surface in the build logs): the `pygame` p4a recipe builds
   upstream pygame (SDL2); the project targets pygame-ce (API-compatible). If a
   CE-specific build is needed, point a local recipe at it or override
   `--requirements`. Also re-check the `pygame.FINGER*` -> logical-coordinate
   mapping on a real device (untested off hardware).

## Desktop-only, never shipped to Android
- `src/app/server_app.py` (tkinter admin)
- `tools/online_test.py`
- the server-hosting path (phone joins, never hosts)
