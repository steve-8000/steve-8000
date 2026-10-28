#!/usr/bin/env python3
"""Render assets/activity-{light,dark}.svg from the authenticated user's GitHub contributions.

Requires `gh` and GH_TOKEN of the profile owner. Only aggregate counts are written.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OWNER = "steve-8000"
OUT = Path(__file__).resolve().parent.parent / "assets"
FONT = "Pretendard,-apple-system,BlinkMacSystemFont,'Helvetica Neue','Segoe UI',Arial,sans-serif"
MONO = "'SF Mono',ui-monospace,Menlo,Consolas,monospace"

QUERY = """
query {
  viewer {
    login
    organizations { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        weeks { contributionDays { weekday contributionCount } }
      }
    }
  }
}
"""

THEMES = {
    "light": dict(fg="#0a0a0a", gray="#8a8a8a", line="#e6e6e6", levels=["#f0f0f0", "#cfcfcf", "#9a9a9a", "#5c5c5c", "#0a0a0a"]),
    "dark": dict(fg="#f5f5f5", gray="#8b8b8b", line="#30363d", levels=["#1c1f24", "#3a3d42", "#6e7176", "#a8aaad", "#ffffff"]),
}


def fetch():
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}"], check=True, capture_output=True, text=True).stdout
    viewer = json.loads(out)["data"]["viewer"]
    if viewer["login"] != OWNER:
        sys.exit(f"token belongs to {viewer['login']}, expected {OWNER}")
    return viewer


def level_for(count, cuts):
    if count == 0:
        return 0
    return 1 + sum(count > c for c in cuts)


def render(theme, c, viewer):
    cc = viewer["contributionsCollection"]
    weeks = cc["contributionCalendar"]["weeks"]
    nonzero = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"])
    cuts = [nonzero[len(nonzero) * q // 4] for q in (1, 2, 3)] if nonzero else [0, 0, 0]

    stats = [
        ("COMMITS", cc["totalCommitContributions"], "last 12 months"),
        ("PULL REQUESTS", cc["totalPullRequestContributions"], "last 12 months"),
        ("REPOSITORIES", cc["totalRepositoriesWithContributedCommits"], "committed to"),
        ("ORGANIZATIONS", viewer["organizations"]["totalCount"], "member"),
    ]
    cols = ""
    for i, (label, value, sub) in enumerate(stats):
        x = i * 210
        cols += (
            f'<text x="{x}" y="14" font-family="{MONO}" font-size="11" letter-spacing="1" fill="{c["gray"]}">{label}</text>'
            f'<text x="{x - 2}" y="68" font-family="{FONT}" font-size="48" font-weight="700" letter-spacing="-2" fill="{c["fg"]}">{value:,}</text>'
            f'<text x="{x}" y="90" font-family="{MONO}" font-size="11" fill="{c["gray"]}">{sub}</text>'
        )

    cells = ""
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            lvl = level_for(d["contributionCount"], cuts)
            cells += f'<rect x="{wi * 15}" y="{122 + d["weekday"] * 15}" width="11" height="11" rx="2" fill="{c["levels"][lvl]}"/>'

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="250" viewBox="0 0 840 250" role="img" aria-label="GitHub activity over the last 12 months">
  {cols}
  {cells}
  <text x="0" y="244" font-family="{MONO}" font-size="11" fill="{c["gray"]}">Private repositories included. Aggregate counts only. Updated {updated}.</text>
</svg>
'''


def main():
    viewer = fetch()
    OUT.mkdir(exist_ok=True)
    for theme, colors in THEMES.items():
        (OUT / f"activity-{theme}.svg").write_text(render(theme, colors, viewer))


if __name__ == "__main__":
    main()
