# BUG LIST

No known open bugs.

## Resolved

- **Join-in-progress was broken.** A player who joined after the match started
  was stuck in the lobby until the host died. Now the server drops late joiners
  straight into the running match. (`787d85a`)
- **Guests couldn't enter a running match.** The lobby's "Ready" button is now a
  contextual **"Join Game"** button: it readies up before the match starts, or
  drops the player into a match already in progress. (`net/commands.py`,
  `app/lobby_scene.py`)
- **Bullets occasionally hit without dealing damage.** The bullet was destroyed
  but the target's HP was unchanged — a hit-race between clients. (`787d85a`)
- **Respawn HP bar desync.** After respawn the player's own HP bar showed full
  but stayed at 0 on other clients; respawn HP is now synced. (`787d85a`)
