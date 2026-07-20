# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
This is **catking01's GitHub profile README repository**, not a deployable application. It contains:
- `README.md` — the profile page content.
- `github-metrics/`, `profile-3d-contrib/`, `profile-snake-contrib/` — generated SVG assets.
- `.github/workflows/*.yml` — GitHub Actions that regenerate those assets (metrics, waka, contrib, snake, blog). These run in CI on GitHub, **not locally**.
- `profile-dino-contrib/generate_dino_gif.py` — the only locally runnable code.

There is **no dev server, no build system, no test suite, and no linter** configured. Do not look for `package.json`, `Makefile`, or `docker-compose`; none exist.

### Running the only local application (dino GIF generator)
`profile-dino-contrib/generate_dino_gif.py` renders the Chrome dino-runner animation into `dino-runner.gif` (light) and `dino-runner-dark.gif` (dark) from the sprite sheet `100-offline-sprite.png`. It depends only on **Pillow** (installed by the update script).

Non-obvious gotcha: the script hardcodes a macOS path near the top:
`ROOT = Path('/Users/catking/Desktop/Github/catking01/profile-dino-contrib')`.
Running it directly will fail (sprite not found / cannot write output). To run it in this environment without editing the committed file, import it and override `ROOT`, `SPRITE_PATH`, `OUT_LIGHT`, and `OUT_DARK` to point at `profile-dino-contrib/` before calling `main()`. You can also shorten `DURATION_S`/`FRAMES` for a quick smoke run (default is a 60s, 1200-frame animation per theme). The script prints a `collision boxes overlap count: 0` audit line per theme on success.
