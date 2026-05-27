SKILLS = [
    "brew drinking",
    "flong/drinking games",
    "billiards",
    "cornhole",
    "Brewsby",
    "darts",
    "shuffleboard",
    "golf sim",
    "arcade games",
    "giant Jenga/Connect 4",
    "trivia",
    "keg race/relay",
]

PEOPLE: list[dict] = [
    {"id": 1, "full_name": "Mike Davis", "nickname": "MikeD", "team_name": "Riks", "status": "active"},
    {"id": 2, "full_name": "Jake Thompson", "nickname": "JT", "team_name": "Riks", "status": "active"},
    {"id": 3, "full_name": "Chris Martin", "nickname": None, "team_name": "Riks", "status": "active"},
    {"id": 4, "full_name": "Ryan Cooper", "nickname": "Coop", "team_name": "Riks", "status": "active"},
    {"id": 5, "full_name": "Steve Parker", "nickname": None, "team_name": "Wades", "status": "active"},
    {"id": 6, "full_name": "Dan Mitchell", "nickname": "Danny", "team_name": "Wades", "status": "active"},
    {"id": 7, "full_name": "Matt Wilson", "nickname": None, "team_name": "Wades", "status": "active"},
    {"id": 8, "full_name": "Tom Baker", "nickname": "TB", "team_name": "Wades", "status": "active"},
    {"id": 9, "full_name": "Alex Reed", "nickname": None, "team_name": None, "status": "pre_registered"},
    {"id": 10, "full_name": "Ben Foster", "nickname": "Benny", "team_name": None, "status": "pre_registered"},
]

BREW_LOG: list[dict] = [
    {"id": 1, "person_id": 1, "team_name": "Riks", "source": "keg", "status": "active"},
    {"id": 2, "person_id": 1, "team_name": "Riks", "source": "keg", "status": "active"},
    {"id": 3, "person_id": 1, "team_name": "Riks", "source": "keg", "status": "active"},
    {"id": 4, "person_id": 2, "team_name": "Riks", "source": "keg", "status": "active"},
    {"id": 5, "person_id": 2, "team_name": "Riks", "source": "keg", "status": "active"},
    {"id": 6, "person_id": 3, "team_name": "Riks", "source": "byob", "status": "active"},
    {"id": 7, "person_id": 4, "team_name": "Riks", "source": "keg", "status": "active"},
    {"id": 8, "person_id": 5, "team_name": "Wades", "source": "keg", "status": "active"},
    {"id": 9, "person_id": 5, "team_name": "Wades", "source": "keg", "status": "active"},
    {"id": 10, "person_id": 5, "team_name": "Wades", "source": "keg", "status": "active"},
    {"id": 11, "person_id": 5, "team_name": "Wades", "source": "keg", "status": "active"},
    {"id": 12, "person_id": 6, "team_name": "Wades", "source": "keg", "status": "active"},
    {"id": 13, "person_id": 6, "team_name": "Wades", "source": "byob", "status": "active"},
    {"id": 14, "person_id": 7, "team_name": "Wades", "source": "keg", "status": "active"},
    {"id": 15, "person_id": 8, "team_name": "Wades", "source": "keg", "status": "active"},
]

KEG_STATE: dict = {
    "Riks": {"capacity": 330, "logged_total": 6},
    "Wades": {"capacity": 330, "logged_total": 7},
}

EVENTS: list[dict] = [
    {"id": 1, "name": "Cornhole Tournament", "status": "completed", "points_available": 100, "riks_points": 100, "wades_points": 50},
    {"id": 2, "name": "Flip Cup", "status": "completed", "points_available": 75, "riks_points": 30, "wades_points": 75},
    {"id": 3, "name": "Trivia Night", "status": "in_progress", "points_available": 100, "riks_points": None, "wades_points": None},
    {"id": 4, "name": "Billiards", "status": "pending", "points_available": 75, "riks_points": None, "wades_points": None},
    {"id": 5, "name": "Giant Jenga", "status": "pending", "points_available": 50, "riks_points": None, "wades_points": None},
    {"id": 6, "name": "Brew Cup", "status": "pending", "points_available": 200, "riks_points": None, "wades_points": None},
]

SURVEY_RESPONSES: list[dict] = [
    {
        "person_id": 9,
        "full_name": "Alex Reed",
        "expected_arrival_day": "Friday",
        "expected_arrival_time": "3:00 PM",
        "top_3_skills": ["cornhole", "trivia", "billiards"],
        "brew_drinking_skill_rank": 2,
        "notes": "",
    },
    {
        "person_id": 10,
        "full_name": "Ben Foster",
        "expected_arrival_day": "Thursday",
        "expected_arrival_time": "6:00 PM",
        "top_3_skills": ["brew drinking", "flong/drinking games", "darts"],
        "brew_drinking_skill_rank": 3,
        "notes": "Bringing extra cooler",
    },
]


def get_person(person_id: int) -> dict | None:
    return next((p for p in PEOPLE if p["id"] == person_id), None)


def get_active_people() -> list[dict]:
    return [p for p in PEOPLE if p["status"] == "active"]


def get_person_brews(person_id: int) -> int:
    return sum(1 for b in BREW_LOG if b["person_id"] == person_id and b["status"] == "active")


def get_team_keg_brews(team: str) -> int:
    return sum(
        1 for b in BREW_LOG
        if b["team_name"] == team and b["status"] == "active" and b["source"] == "keg"
    )


def get_team_scores() -> dict:
    scores = {"Riks": 0, "Wades": 0}
    for e in EVENTS:
        if e["riks_points"] is not None:
            scores["Riks"] += e["riks_points"]
        if e["wades_points"] is not None:
            scores["Wades"] += e["wades_points"]
    return scores


def log_brew(person_id: int) -> dict | None:
    person = get_person(person_id)
    if not person or not person["team_name"]:
        return None
    entry = {
        "id": len(BREW_LOG) + 1,
        "person_id": person_id,
        "team_name": person["team_name"],
        "source": "keg",
        "status": "active",
    }
    BREW_LOG.append(entry)
    KEG_STATE[person["team_name"]]["logged_total"] += 1
    return entry


def get_leaderboard() -> list[dict]:
    counts: dict[int, int] = {}
    for b in BREW_LOG:
        if b["status"] == "active":
            counts[b["person_id"]] = counts.get(b["person_id"], 0) + 1
    result = []
    for pid, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        person = get_person(pid)
        if person:
            result.append({"person": person, "count": count})
    return result
