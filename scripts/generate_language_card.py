#!/usr/bin/env python3
"""Generate self-hosted "Most Used Languages" SVG cards (light + dark).

Aggregates language bytes across all owned, non-fork public repos of USER
via the GitHub REST API (stdlib only), then renders:
  - github-metrics/languages.svg       (light theme)
  - github-metrics/languages.dark.svg  (dark theme)

Auth: uses the GITHUB_TOKEN env var when present, otherwise unauthenticated
(unauthenticated is capped at 60 req/hr per IP and unsuitable for CI).
"""

import json
import os
import sys
import urllib.request

USER = "catking01"
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "github-metrics")
API = "https://api.github.com"
MAX_LANGS = 6

# GitHub linguist colors for the languages likely to surface on this profile.
LINGUIST_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "HTML": "#e34c26", "CSS": "#563d7c", "SCSS": "#c6538c", "Less": "#1d365d",
    "Shell": "#89e051", "C": "#555555", "C++": "#f34b7d", "C#": "#178600",
    "Go": "#00ADD8", "Rust": "#dea584", "Java": "#b07219", "Kotlin": "#A97BFF",
    "Swift": "#F05138", "Objective-C": "#438eff", "PHP": "#4F5D95",
    "Ruby": "#701516", "Vue": "#41b883", "Svelte": "#ff3e00", "Astro": "#ff5a03",
    "Dart": "#00B4AB", "Scala": "#c22d40", "Elixir": "#6e4a7e",
    "Clojure": "#db5855", "Haskell": "#5e5086", "Lua": "#000080",
    "Perl": "#0298c3", "R": "#198CE7", "MATLAB": "#e16737", "Julia": "#a270ba",
    "Dockerfile": "#384d54", "Makefile": "#427819", "TeX": "#3D6117",
    "PowerShell": "#012456", "Assembly": "#6E4C13", "Nix": "#7e7eff",
    "Zig": "#ec915c", "Jupyter Notebook": "#DA5B0B", "Vim Script": "#199f4b",
}
DEFAULT_COLOR = "#8b949e"   # an unmapped language
OTHER_COLOR = "#ededed"     # aggregated remainder (kept visually distinct)

THEMES = {
    "light": {
        "file": "languages.svg",
        "bg": "#ffffff",
        "text": "#24292f",
        "muted": "#57606a",
    },
    "dark": {
        "file": "languages.dark.svg",
        "bg": "#0d1117",
        "text": "#c9d1d9",
        "muted": "#8b949e",
    },
}


def api_get(path):
    req = urllib.request.Request(API + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "profile-language-card")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_language_bytes():
    totals = {}
    page = 1
    while True:
        repos = api_get(f"/users/{USER}/repos?type=owner&per_page=100&page={page}")
        for repo in repos:
            if repo.get("fork"):
                continue
            langs = api_get(f"/repos/{USER}/{repo['name']}/languages")
            for lang, nbytes in langs.items():
                totals[lang] = totals.get(lang, 0) + nbytes
        if len(repos) < 100:
            break
        page += 1
    return totals


def esc(text):
    # Drop XML-invalid control chars, then escape markup-significant characters
    # (quotes included so the helper stays safe if ever used in an attribute).
    text = "".join(ch for ch in text if ch >= " " or ch in "\t\n")
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def build_entries(totals):
    """Return [(name, color, pct)] for the top languages + 'Other'.

    Percentages are rounded to one decimal with the largest-remainder method so
    the displayed values sum to exactly 100.0.
    """
    grand = sum(totals.values())
    if grand == 0:
        return []
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    items = [[name, LINGUIST_COLORS.get(name, DEFAULT_COLOR), nbytes]
             for name, nbytes in ranked[:MAX_LANGS]]
    other = sum(b for _, b in ranked[MAX_LANGS:])
    if other:
        items.append(["Other", OTHER_COLOR, other])
    raw = [1000.0 * it[2] / grand for it in items]
    tenths = [int(x) for x in raw]
    leftover = max(0, 1000 - sum(tenths))
    for i in sorted(range(len(items)), key=lambda i: raw[i] - tenths[i], reverse=True)[:leftover]:
        tenths[i] += 1
    return [(items[i][0], items[i][1], tenths[i] / 10.0) for i in range(len(items))]


def render_svg(entries, theme):
    width, pad = 480, 24
    bar_y, bar_h = 58, 10
    bar_w = width - 2 * pad
    legend_y, row_h, col_w = bar_y + bar_h + 24, 24, (width - 2 * pad) // 2
    rows = (len(entries) + 1) // 2
    height = legend_y + rows * row_h + pad - 8

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="Most used languages">',
        f'<rect width="{width}" height="{height}" rx="8" fill="{theme["bg"]}"/>',
        f'<text x="{pad}" y="{pad + 12}" font-family="system-ui,\'Segoe UI\',sans-serif" '
        f'font-size="16" font-weight="600" fill="{theme["text"]}">Most Used Languages</text>',
        '<defs><clipPath id="bar-clip">'
        f'<rect x="{pad}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h / 2:g}"/>'
        '</clipPath></defs>',
        '<g clip-path="url(#bar-clip)">',
    ]
    x = float(pad)
    for name, color, pct in entries:
        seg_w = bar_w * pct / 100.0
        parts.append(
            f'<rect x="{x:.2f}" y="{bar_y}" width="{seg_w:.2f}" height="{bar_h}" fill="{color}">'
            f'<title>{esc(name)} {pct:.1f}%</title></rect>')
        x += seg_w
    parts.append('</g>')

    for i, (name, color, pct) in enumerate(entries):
        cx = pad + (i % 2) * col_w
        cy = legend_y + (i // 2) * row_h
        label = name if len(name) <= 24 else name[:23] + "\u2026"
        parts.append(f'<circle cx="{cx + 5}" cy="{cy + 5}" r="5" fill="{color}"/>')
        parts.append(
            f'<text x="{cx + 17}" y="{cy + 9.5:g}" font-family="system-ui,\'Segoe UI\',sans-serif" '
            f'font-size="12" fill="{theme["text"]}">{esc(label)} '
            f'<tspan fill="{theme["muted"]}">{pct:.1f}%</tspan></text>')

    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def main():
    totals = fetch_language_bytes()
    entries = build_entries(totals)
    if not entries:
        print("No language data found; nothing written.", file=sys.stderr)
        return 1

    print(f"Languages for {USER} ({sum(totals.values())} bytes total):")
    for name, _, pct in entries:
        print(f"  {name}: {pct:.1f}%")

    # Render everything, stage every theme to a temp file, then swap them all in
    # back-to-back. A render/write error thus can't truncate a good committed
    # file or leave a mismatched light/dark pair, and stray temps are cleaned up.
    rendered = [(os.path.join(OUT_DIR, t["file"]), render_svg(entries, t)) for t in THEMES.values()]
    os.makedirs(OUT_DIR, exist_ok=True)
    staged = []
    try:
        for path, content in rendered:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            staged.append((tmp, path))
        for tmp, path in staged:
            os.replace(tmp, path)
            print(f"Wrote {path}")
    finally:
        for tmp, _ in staged:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
