# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
This is a **GitHub profile README repository** (the special `catking01/catking01` repo whose `README.md` renders on the GitHub profile page). It is **not a traditional application**: there is no server, web app, database, build system, or automated test suite. Do not look for `dev`/`build`/`test` commands — none exist.

### What runs where
- All profile graphics (`github-metrics/`, `profile-3d-contrib/`, `profile-snake-contrib/`) are produced by scheduled GitHub Actions in `.github/workflows/` using third-party actions. These run in GitHub CI (not locally) and require repo secrets (`GITHUB_TOKEN`/`GH_TOKEN`, `WAKATIME_API_KEY`). They cannot be meaningfully run end-to-end outside GitHub.
- The **only locally runnable code** is `profile-dino-contrib/generate_dino_gif.py`, which regenerates the Chrome-dino animation embedded in the README. It needs **Python 3 + Pillow** (Pillow is installed by the startup update script).

### Running the dino generator (non-obvious gotcha)
`generate_dino_gif.py` uses a hardcoded absolute `ROOT` path (`/Users/catking/Desktop/Github/catking01/profile-dino-contrib`) for both its input sprite and its output GIFs. To run it without editing the script, make that path resolve to a directory containing `100-offline-sprite.png`, e.g.:

```bash
sudo mkdir -p /Users/catking/Desktop/Github/catking01
mkdir -p /tmp/dino_out && cp profile-dino-contrib/100-offline-sprite.png /tmp/dino_out/
ln -sfn /tmp/dino_out /Users/catking/Desktop/Github/catking01/profile-dino-contrib
python3 profile-dino-contrib/generate_dino_gif.py
# outputs dino-runner.gif and dino-runner-dark.gif into /tmp/dino_out
```

Pointing `ROOT` at a temp dir (rather than the repo) keeps the committed `.gif` files untouched. Output is **deterministic** (fixed RNG seed `20260528`), so a correct run reproduces the committed GIFs byte-for-byte and prints `collision boxes overlap count: 0` for both themes. Runtime is ~7s.
