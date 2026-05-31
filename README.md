# Choose Your Way

Choose Your Way is a 2D networked multiplayer top-down shooter built with [pygame-ce](https://github.com/pygame-community/pygame-ce). Pick a character, host or join a room over the network (or play offline), then move, aim, and shoot your way through waves of zombies on a Tiled-authored map.

## Gameplay

Enter a name, pick one of **8 characters**, then choose how to play:

- **New Game** — play offline on your own.
- **Create Room** — host an online room others can join (up to **4 players**).
- **Connect** — join an existing room by its room ID.

Players and zombies start with **100 HP**. Zombies home in on the nearest player (falling back to your base when out of range); shooting kicks back and emits a muzzle flash. The camera follows your player around the map.

### Characters

`hitman` · `man_blue` · `man_brown` · `man_old` · `robot` · `solider` · `survivor` · `woman_green`

### Controls

| Action | Input |
|---|---|
| Move | `W` `A` `S` `D` or arrow keys |
| Aim | Mouse |
| Shoot | Left click (hold to auto-fire) |
| Back / menu | `Esc` |
| Toggle debug overlay | `F1` |
| Toggle fullscreen | `F11` |

## Multiplayer

The host runs a dedicated server window:

```bash
uv run python server.py     # or: server.bat
```

Clients launch the game, **Create Room** (host) or **Connect** by room ID (others). For play over the internet, the bundled `ngrok.exe` can expose the local server as a public endpoint; on the same LAN, clients connect directly.

## Requirements

- Python 3.12+
- [pygame-ce](https://github.com/pygame-community/pygame-ce), colorama, pyyaml, pytmx (resolved automatically from `pyproject.toml` / `uv.lock`)
- [uv](https://docs.astral.sh/uv/) (optional but recommended)

## Running

```bash
git clone --recurse-submodules https://github.com/umutcanekinci/choose-your-way.git
cd choose-your-way
uv sync
uv run python __main__.py
```

If you forgot `--recurse-submodules`: `git submodule update --init`.

Without `uv`: `pip install .` then `python __main__.py` (Windows: `ChooseYourWay.bat`).

## Project layout

```
__main__.py            Entry point — injects src/ + src/pygame_core/ into sys.path
server.py              Dedicated multiplayer server (Tk window)
src/app/game.py        Game class — wires panels, networking, and the game loop
src/gameplay/          Entities (player, mob, bullet), map, camera, collision
src/net/               Client + server networking, room / player state
src/ui/                Panel widgets (vector buttons, text input)
src/util/              Constants, database helper
src/pygame_core/       Engine submodule (Application, GameObject/ECS, PanelLoaderExt, ...)
config/                YAML: assets, panels
assets/                Images, Tiled maps
tests/                 Test suite — protocol/transport/game-server, unit → e2e
bench/                 Headless performance benchmarks (mob capacity)
```

The game runs on the shared [`pygame_core`](https://github.com/umutcanekinci/pygame-core) engine: `Game` extends `pygame_core.Application`, the menu is panel-driven (`config/panels.yaml` + `PanelManager`), and in-world entities are `GameObject`s with `SpriteRenderer2D` components.

## Testing

Tests are organized as a pyramid over the networking stack:

- **Unit** (`test_protocol.py`, `test_game_server.py`) — no sockets. Framing/codec edge cases and game-server command dispatch via fakes. Fast.
- **Integration** (`test_transport.py`, marked `integration`) — real `BaseClient`/`BaseServer` over loopback.
- **End-to-end** (`test_e2e.py`, marked `e2e`) — full `GameServer` + clients.

```bash
uv run --group dev pytest                              # everything
uv run --group dev pytest -m "not integration and not e2e"   # fast unit tests only
```

CI (GitHub Actions, `.github/workflows/tests.yml`) runs the **full** suite on every push and on PRs into `main`.

### Performance benchmark

`bench/bench_mobs.py` is a headless capacity benchmark — how many zombies the
simulation sustains before missing the 60 FPS frame budget. It times the per-frame
update (AI/physics) and draw separately for increasing mob counts:

```bash
uv run python bench/bench_mobs.py
```

Numbers are machine-relative — use them to compare before/after an optimization
on the same machine, not as an absolute FPS promise.

A [pre-commit](https://pre-commit.com/) hook runs ruff (lint + format) and the **fast** tests on each commit, leaving the socket-backed tests to CI. Enable it once per clone:

```bash
uv run pre-commit install
```

Bypass a hook run with `git commit --no-verify`; run all hooks manually with `uv run pre-commit run --all-files`.

## Credits

Character and tile art from [Kenney](https://www.kenney.nl/) — [Topdown Shooter](https://www.kenney.nl/assets/topdown-shooter).

## Contributing

1. Fork this repository.
2. Clone your fork: `git clone --recurse-submodules https://github.com/<you>/choose-your-way.git`
3. Set up dev tooling: `uv sync` then `uv run pre-commit install` (runs lint/format + fast tests on commit).
4. Create a branch: `git checkout -b feature/<your-feature>`
5. Commit + push: `git commit -am "<message>" && git push origin feature/<your-feature>`
6. Open a pull request.

## Author

Umutcan Ekinci — [umutcannekinci@gmail.com](mailto:umutcannekinci@gmail.com)

See also the [contributors](https://github.com/umutcanekinci/choose-your-way/contributors).

## License

See [LICENSE](LICENSE).
