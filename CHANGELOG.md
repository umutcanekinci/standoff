# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] – 2026-08-12

### Added

- `engine-tests` CI job running `pygamine`'s own test suite.

### Changed

- Renamed the `pygame_core` submodule/dependency to `pygamine`; rebased `gameplay.Camera` onto
  `pygamine.Camera` instead of duplicating it.

### Fixed

- A real broken import in `tools/online_test.py`, plus stale doc references.
- A redundant `sys.path` hack in `tests/test_camera.py`.

## [0.1.6] – 2026-07-09

- Hide desktop-only settings on Android; warn instead of block hosting.
- Renamed the built APK to match the desktop asset naming pattern.

## [0.1.5] – 2026-07-08

- Attach the Android APK to the GitHub Release too.
- `buildozer` now reads the app version from `pyproject.toml` instead of duplicating it.

## [0.1.4] – 2026-07-08

- Publish the debug APK to itch.io's Android channel on tag push.

## [0.1.3] – 2026-07-08

- Fixed the Android build pipeline (buildozer container patches, `hostpython3` recipe override,
  `patchelf`).

## [0.1.2] – 2026-07-08

- Settings menu: window mode/resolution and SFX/BGM volume, persisted.
- Startup splash screen; itch.io/storefront cover art.

## [0.1.1] – 2026-07-07

- Desktop PyInstaller build + release automation; itch.io publish automation.
- Real in-game screenshots plus a headless capture harness for storefront assets.

## [0.1.0] – 2026-06-15

Initial release. Multiplayer top-down survival shooter with server-authoritative mobs, a lobby/room
system, join-in-progress, a death screen with respawn, and Android touch-control support.
