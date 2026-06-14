"""
FIFA World Cup 2026 — dynamic topic & context generator.

Reads the local JSON data files in 2026/ and produces:
  - A specific topic_hint  (e.g. "USA 4-1 Paraguay recap")
  - A rich context_block   (live standings, scorers, fixtures)

Both get injected into the Groq prompt so every Short is timely and specific.

Content angles (chosen automatically based on today's date):
  recap           — yesterday's / today's completed match breakdown
  shock_analysis  — surprising result or draw that needs explaining
  player_spotlight— a goal scorer or standout player deep-dive
  preview         — tactical/stat preview of a match today or tomorrow
  prediction      — bold prediction for an upcoming fixture
  standings       — which teams are through, who is in danger
  group_analysis  — full group narrative with elimination pressure
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "2026"


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_matches() -> list[dict]:
    with open(DATA_DIR / "worldcup.json", encoding="utf-8") as f:
        return json.load(f)["matches"]


def _load_groups() -> list[dict]:
    with open(DATA_DIR / "worldcup.groups.json", encoding="utf-8") as f:
        return json.load(f)["groups"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _match_date(m: dict) -> datetime | None:
    ds = m.get("date")
    if not ds:
        return None
    try:
        return datetime.strptime(ds, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _fmt_goals(goals: list[dict]) -> str:
    if not goals:
        return "—"
    parts = []
    for g in goals:
        extra = " (OG)" if g.get("owngoal") else (" (pen)" if g.get("penalty") else "")
        parts.append(f"{g['name']} {g['minute']}'{extra}")
    return ", ".join(parts)


def _fmt_score(m: dict) -> str:
    s = m.get("score", {}).get("ft")
    return f"{s[0]}-{s[1]}" if s else "vs"


def _is_completed(m: dict) -> bool:
    return bool(m.get("score", {}).get("ft"))


# ── Standings calculator ──────────────────────────────────────────────────────

def _compute_standings(matches: list[dict], groups: list[dict]) -> dict[str, dict]:
    """Return per-team stats dict keyed by team name."""
    stats: dict[str, dict] = {}
    for group in groups:
        for team in group["teams"]:
            stats[team] = {
                "group": group["name"],
                "played": 0, "won": 0, "drawn": 0, "lost": 0,
                "gf": 0, "ga": 0, "pts": 0,
            }

    for m in matches:
        if not _is_completed(m):
            continue
        t1, t2 = m["team1"], m["team2"]
        g1, g2 = m["score"]["ft"]
        if t1 not in stats or t2 not in stats:
            continue

        for t, gf, ga in [(t1, g1, g2), (t2, g2, g1)]:
            stats[t]["played"] += 1
            stats[t]["gf"] += gf
            stats[t]["ga"] += ga

        if g1 > g2:
            stats[t1]["won"] += 1
            stats[t1]["pts"] += 3
            stats[t2]["lost"] += 1
        elif g2 > g1:
            stats[t2]["won"] += 1
            stats[t2]["pts"] += 3
            stats[t1]["lost"] += 1
        else:
            stats[t1]["drawn"] += 1
            stats[t2]["drawn"] += 1
            stats[t1]["pts"] += 1
            stats[t2]["pts"] += 1

    return stats


def _standings_text(groups: list[dict], standings: dict[str, dict]) -> str:
    lines = []
    for group in groups:
        teams = group["teams"]
        ranked = sorted(
            teams,
            key=lambda t: (
                -standings.get(t, {}).get("pts", 0),
                -(standings.get(t, {}).get("gf", 0) - standings.get(t, {}).get("ga", 0)),
            ),
        )
        row = " | ".join(
            f"{t} {standings.get(t, {}).get('pts', 0)}pts "
            f"(P{standings.get(t, {}).get('played', 0)} "
            f"W{standings.get(t, {}).get('won', 0)} "
            f"D{standings.get(t, {}).get('drawn', 0)} "
            f"L{standings.get(t, {}).get('lost', 0)} "
            f"GD{standings.get(t, {}).get('gf', 0) - standings.get(t, {}).get('ga', 0)})"
            for t in ranked
        )
        lines.append(f"{group['name']}: {row}")
    return "\n".join(lines)


# ── Main public function ──────────────────────────────────────────────────────

def pick_fifa_topic() -> tuple[str, str]:
    """
    Returns:
        topic_hint   : short string describing what this video covers
        context_block: multi-line string of live FIFA 2026 data for Groq

    Called by run_short.py when preset topic_rotation == "fifa_2026".
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    yesterday = (now - timedelta(days=1)).date()
    tomorrow = (now + timedelta(days=1)).date()
    day_after = (now + timedelta(days=2)).date()

    matches = _load_matches()
    groups = _load_groups()
    standings = _compute_standings(matches, groups)

    # Categorise matches
    recent: list[dict] = []          # completed in last 72h
    upcoming_today: list[dict] = []  # today, not yet started
    upcoming_soon: list[dict] = []   # tomorrow or day after

    for m in matches:
        d = _match_date(m)
        if not d:
            continue
        md = d.date()
        if _is_completed(m) and md >= yesterday:
            recent.append(m)
        elif not _is_completed(m):
            if md == today:
                upcoming_today.append(m)
            elif md in (tomorrow, day_after):
                upcoming_soon.append(m)

    # ── Build context sections ────────────────────────────────────────────────

    # Recent results block
    if recent:
        result_lines = []
        for m in recent[-8:]:
            score = _fmt_score(m)
            g1 = _fmt_goals(m.get("goals1", []))
            g2 = _fmt_goals(m.get("goals2", []))
            result_lines.append(
                f"  • {m['team1']} {score} {m['team2']}  "
                f"[{m.get('group', '')} | {m['date']} | {m.get('ground', '')}]\n"
                f"    Scorers — {m['team1']}: {g1}  |  {m['team2']}: {g2}"
            )
        results_text = "\n".join(result_lines)
    else:
        results_text = "  No completed matches in the last 72 hours."

    # Upcoming fixtures block
    all_upcoming = upcoming_today + upcoming_soon
    if all_upcoming:
        fix_lines = [
            f"  • {m['team1']} vs {m['team2']}  "
            f"[{m.get('group', '')} | {m['date']} | {m.get('ground', '')} | {m.get('time', '')}]"
            for m in all_upcoming[:8]
        ]
        fixtures_text = "\n".join(fix_lines)
    else:
        fixtures_text = "  No fixtures in the next 48 hours (knockout stage or rest day)."

    # Standings block (only groups with at least 1 game played)
    active_groups = [
        g for g in groups
        if any(standings.get(t, {}).get("played", 0) > 0 for t in g["teams"])
    ]
    standings_text = _standings_text(active_groups, standings) if active_groups else "Group stage not yet started."

    # ── Build angle pool ─────────────────────────────────────────────────────
    # Collect all scorers from recent matches with goal counts
    scorer_tally: dict[str, dict] = {}  # name → {goals, match_info}
    for m in recent:
        for side in ("goals1", "goals2"):
            for g in m.get(side, []):
                name = g["name"]
                if name not in scorer_tally:
                    scorer_tally[name] = {"goals": 0, "match": m, "minutes": []}
                scorer_tally[name]["goals"] += 1
                scorer_tally[name]["minutes"].append(g["minute"])

    angle_pool: list[str] = []
    if recent:
        angle_pool += ["recap", "recap", "shock_analysis"]
        if scorer_tally:
            # More weight for player spotlight if someone scored 2+ goals
            multi_goal_scorers = [n for n, d in scorer_tally.items() if d["goals"] >= 2]
            angle_pool += ["player_spotlight", "player_spotlight"]
            if multi_goal_scorers:
                angle_pool += ["player_spotlight", "goal_stats"]  # extra weight
        angle_pool += ["goal_stats"]  # always eligible if matches played
    if upcoming_today:
        angle_pool += ["preview", "preview", "prediction", "prediction"]
    if upcoming_soon:
        angle_pool += ["preview", "prediction"]
    if active_groups:
        angle_pool += ["standings", "group_analysis"]

    if not angle_pool:
        angle_pool = ["standings"]

    angle = random.choice(angle_pool)

    # ── Build topic_hint per angle ────────────────────────────────────────────
    topic_hint: str

    if angle == "recap" and recent:
        m = random.choice(recent[-5:])
        score = _fmt_score(m)
        topic_hint = (
            f"FIFA World Cup 2026 Recap: {m['team1']} {score} {m['team2']} — "
            f"goals, highlights & what it means for {m.get('group', 'the group')}"
        )

    elif angle == "shock_analysis" and recent:
        draws = [m for m in recent if m.get("score", {}).get("ft", [-1, -1])[0] == m.get("score", {}).get("ft", [-1, -1])[1]]
        m = random.choice(draws if draws else recent[-4:])
        score = _fmt_score(m)
        topic_hint = (
            f"FIFA 2026 Shock: {m['team1']} {score} {m['team2']} — "
            f"biggest surprise of the tournament so far and what happens next"
        )

    elif angle == "player_spotlight" and scorer_tally:
        # Prioritize: 2+ goal scorers first, then any scorer
        multi = {n: d for n, d in scorer_tally.items() if d["goals"] >= 2}
        chosen_pool = multi if multi else scorer_tally
        # Weight by goals scored — a hat-trick scorer gets 3x the chance
        weighted = []
        for name, data in chosen_pool.items():
            weighted.extend([name] * data["goals"])
        name = random.choice(weighted)
        data = scorer_tally[name]
        m = data["match"]
        goals_str = f"{data['goals']} goal{'s' if data['goals'] > 1 else ''}"
        mins_str = " & ".join(f"{mn}'" for mn in data["minutes"])
        topic_hint = (
            f"FIFA 2026 Player Spotlight: {name} scored {goals_str} ({mins_str}) — "
            f"who is he, his career, and why he could define this World Cup"
        )

    elif angle == "goal_stats" and scorer_tally:
        # Top scorers so far across all 2026 WC matches
        top = sorted(scorer_tally.items(), key=lambda x: -x[1]["goals"])[:5]
        top_str = ", ".join(f"{n} ({d['goals']})" for n, d in top)
        topic_hint = (
            f"FIFA 2026 Top Scorers So Far: {top_str} — "
            f"goal stats, standout performances and who leads the Golden Boot race"
        )

    elif angle == "preview" and all_upcoming:
        m = random.choice(upcoming_today if upcoming_today else upcoming_soon)
        topic_hint = (
            f"FIFA 2026 Match Preview: {m['team1']} vs {m['team2']} — "
            f"key players, head-to-head stats, and prediction ({m.get('group', '')})"
        )

    elif angle == "prediction" and all_upcoming:
        m = random.choice(upcoming_today if upcoming_today else upcoming_soon)
        topic_hint = (
            f"FIFA 2026 Prediction: {m['team1']} vs {m['team2']} — "
            f"who wins and why? Stats, form, and bold prediction"
        )

    elif angle == "standings" and active_groups:
        g = random.choice(active_groups)
        gname = g["name"]
        teams = g["teams"]
        ranked = sorted(teams, key=lambda t: -standings.get(t, {}).get("pts", 0))
        topic_hint = (
            f"FIFA 2026 {gname} Standings Update: {ranked[0]} leads — "
            f"who qualifies, who's in danger, and what each team needs"
        )

    elif angle == "group_analysis" and active_groups:
        g = random.choice(active_groups)
        gname = g["name"]
        topic_hint = (
            f"FIFA 2026 {gname} Analysis — the most unpredictable group, "
            f"shock results, and who we think goes through to the knockouts"
        )

    else:
        topic_hint = (
            f"FIFA World Cup 2026 Latest: results, standings update, and "
            f"the matches you cannot miss this week"
        )

    # ── Assemble full context block ───────────────────────────────────────────
    context_block = (
        f"\n"
        f"══ FIFA WORLD CUP 2026 LIVE DATA (as of {today}) ══\n"
        f"\n"
        f"RECENT MATCH RESULTS (last 72 hours):\n{results_text}\n"
        f"\n"
        f"UPCOMING FIXTURES (today & next 48 hours):\n{fixtures_text}\n"
        f"\n"
        f"CURRENT GROUP STANDINGS:\n{standings_text}\n"
        f"\n"
        f"CHOSEN CONTENT ANGLE: {angle.upper().replace('_', ' ')}\n"
        f"Use the above data to create the video. Be specific — name the teams, "
        f"the scorers, the minutes, the stadiums. Fans want DETAIL not generalities.\n"
    )

    return topic_hint, context_block
