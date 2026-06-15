#!/usr/bin/env python3
"""
Seed script for local dev. Requires the full docker-compose stack at localhost:8080.

    cd brew-metrics
    docker compose up -d
    python scripts/seed_local.py

For a guaranteed clean slate first:
    docker compose down -v && docker compose up -d
    python scripts/seed_local.py

Brew log entries are additive — re-running on an existing DB will add more brews.
Everything else (survey, team assignment, event scores) is idempotent.
"""

import http.cookiejar
import sys
import urllib.error
import urllib.parse
import urllib.request

import psycopg2

BASE = "http://localhost:8080"
DB_URL = "postgresql://brewadmin:localdev@localhost:5432/brewmetrics"

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SURVEY_PEOPLE = [
    dict(full_name="Mike Davis", nickname="MikeD", expected_arrival_day="Thursday",
         expected_arrival_time="5:00 PM", skill_1="keg race/relay", skill_2="cornhole",
         skill_3="flong/drinking games", brew_drinking_skill_rank=3, notes=""),
    dict(full_name="Jake Thompson", nickname="JT", expected_arrival_day="Thursday",
         expected_arrival_time="7:00 PM", skill_1="billiards", skill_2="trivia",
         skill_3="darts", brew_drinking_skill_rank=2, notes=""),
    dict(full_name="Chris Martin", nickname="", expected_arrival_day="Friday",
         expected_arrival_time="2:00 PM", skill_1="cornhole", skill_2="golf sim",
         skill_3="shuffleboard", brew_drinking_skill_rank=2, notes=""),
    dict(full_name="Ryan Cooper", nickname="Coop", expected_arrival_day="Friday",
         expected_arrival_time="4:00 PM", skill_1="flong/drinking games", skill_2="Brewsby",
         skill_3="arcade games", brew_drinking_skill_rank=3, notes=""),
    dict(full_name="Steve Parker", nickname="", expected_arrival_day="Thursday",
         expected_arrival_time="6:00 PM", skill_1="keg race/relay", skill_2="darts",
         skill_3="billiards", brew_drinking_skill_rank=2, notes=""),
    dict(full_name="Dan Mitchell", nickname="Danny", expected_arrival_day="Friday",
         expected_arrival_time="3:00 PM", skill_1="trivia", skill_2="cornhole",
         skill_3="giant Jenga/Connect 4", brew_drinking_skill_rank=2, notes=""),
    dict(full_name="Matt Wilson", nickname="", expected_arrival_day="Friday",
         expected_arrival_time="5:00 PM", skill_1="golf sim", skill_2="shuffleboard",
         skill_3="arcade games", brew_drinking_skill_rank=1, notes=""),
    dict(full_name="Tom Baker", nickname="TB", expected_arrival_day="Saturday",
         expected_arrival_time="11:00 AM", skill_1="billiards", skill_2="Brewsby",
         skill_3="flong/drinking games", brew_drinking_skill_rank=3, notes=""),
    dict(full_name="Alex Reed", nickname="", expected_arrival_day="Friday",
         expected_arrival_time="3:00 PM", skill_1="cornhole", skill_2="trivia",
         skill_3="billiards", brew_drinking_skill_rank=2, notes=""),
    dict(full_name="Ben Foster", nickname="Benny", expected_arrival_day="Thursday",
         expected_arrival_time="6:00 PM", skill_1="brew drinking", skill_2="flong/drinking games",
         skill_3="darts", brew_drinking_skill_rank=3, notes="Bringing extra cooler"),
]

# name -> team; omitted names stay pre_registered
TEAM_ASSIGNMENTS = {
    "Mike Davis": "Riks",
    "Jake Thompson": "Riks",
    "Chris Martin": "Riks",
    "Ryan Cooper": "Riks",
    "Steve Parker": "Wades",
    "Dan Mitchell": "Wades",
    "Matt Wilson": "Wades",
    "Tom Baker": "Wades",
}

# name -> brew count to log via /log-brew
BREW_COUNTS = {
    "Mike Davis": 3,
    "Jake Thompson": 2,
    "Chris Martin": 1,
    "Ryan Cooper": 1,
    "Steve Parker": 4,
    "Dan Mitchell": 2,
    "Matt Wilson": 1,
    "Tom Baker": 1,
}

# event name -> (riks_points, wades_points)
EVENT_SCORES = {
    "Cornhole Tournament": (100, 50),
    "Flip Cup": (30, 75),
}

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _make_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPRedirectHandler(),
    )


def _post(opener: urllib.request.OpenerDirector, path: str, form: dict) -> None:
    data = urllib.parse.urlencode({k: str(v) for k, v in form.items()}).encode()
    opener.open(urllib.request.Request(f"{BASE}{path}", data=data))


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def check_server() -> None:
    try:
        urllib.request.urlopen(f"{BASE}/health", timeout=3)
    except (urllib.error.URLError, OSError) as e:
        print(f"ERROR: cannot reach {BASE}/health — {e}")
        print("Make sure `docker compose up -d` is running in brew-metrics/")
        sys.exit(1)


def submit_surveys(opener: urllib.request.OpenerDirector) -> None:
    print("Submitting survey responses...")
    for p in SURVEY_PEOPLE:
        _post(opener, "/survey", p)
        print(f"  {p['full_name']}")


def _fetch_person_ids() -> dict[str, int]:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT full_name, id FROM people")
    result = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return result


def _fetch_event_ids() -> dict[str, int]:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT name, id FROM event_master")
    result = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return result


def admin_login(opener: urllib.request.OpenerDirector) -> None:
    print("Logging in as admin...")
    _post(opener, "/admin/login", {"username": "admin", "password": "admin"})
    print("  ok")


def assign_teams(opener: urllib.request.OpenerDirector, person_ids: dict[str, int]) -> None:
    print("Assigning teams...")
    for name, team in TEAM_ASSIGNMENTS.items():
        pid = person_ids.get(name)
        if pid is None:
            print(f"  SKIP {name} (not found in DB)")
            continue
        _post(opener, "/admin/survey/assign", {"person_id": pid, "team_name": team})
        print(f"  {name} -> {team}")


def finalize_teams(opener: urllib.request.OpenerDirector) -> None:
    print("Finalizing teams...")
    _post(opener, "/admin/survey/finalize", {})
    print("  ok (assigned people marked active)")


def log_brews(person_ids: dict[str, int]) -> None:
    print("Logging brews...")
    plain = _make_opener()
    for name, count in BREW_COUNTS.items():
        pid = person_ids.get(name)
        if pid is None:
            print(f"  SKIP {name} (not found in DB)")
            continue
        for _ in range(count):
            _post(plain, "/log-brew", {"person_id": pid})
        print(f"  {name}: {count} brew(s)")


def score_events(opener: urllib.request.OpenerDirector, event_ids: dict[str, int]) -> None:
    print("Scoring events...")
    for name, (riks_pts, wades_pts) in EVENT_SCORES.items():
        eid = event_ids.get(name)
        if eid is None:
            print(f"  SKIP '{name}' (not found in DB)")
            continue
        _post(opener, "/admin/events/score", {
            "event_id": eid,
            "team_1_points": riks_pts,
            "team_2_points": wades_pts,
        })
        print(f"  {name}: Riks {riks_pts} / Wades {wades_pts}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    check_server()

    opener = _make_opener()

    submit_surveys(opener)
    person_ids = _fetch_person_ids()
    event_ids = _fetch_event_ids()

    admin_login(opener)
    assign_teams(opener, person_ids)
    finalize_teams(opener)
    log_brews(person_ids)
    score_events(opener, event_ids)

    print(f"\nDone. Open {BASE} to verify.")


if __name__ == "__main__":
    main()
