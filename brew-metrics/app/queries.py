from psycopg2.extras import RealDictCursor

from app.constants import EVENT_STATUSES


def get_teams(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, name FROM teams ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def get_team_names(conn) -> list[str]:
    return [t["name"] for t in get_teams(conn)]


def get_team_roster(conn) -> dict:
    """Return {team_name: [members]} for each team plus 'Unassigned'."""
    teams = get_team_names(conn)
    roster: dict[str, list[dict]] = {t: [] for t in teams}
    roster["Unassigned"] = []
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, full_name, nickname, team_name, status "
            "FROM people ORDER BY full_name"
        )
        for r in cur.fetchall():
            key = r["team_name"] if r["team_name"] in roster else "Unassigned"
            roster[key].append(dict(r))
    return roster


def get_person(conn, person_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, full_name, nickname, team_name, status FROM people WHERE id = %s",
            (person_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_active_people(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, full_name, nickname, team_name, status "
            "FROM people WHERE status = 'active' ORDER BY full_name"
        )
        return [dict(r) for r in cur.fetchall()]


def get_all_people(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, full_name, nickname, team_name, status "
            "FROM people ORDER BY full_name"
        )
        return [dict(r) for r in cur.fetchall()]


def get_person_brews(conn, person_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM brew_log WHERE person_id = %s AND status = 'active'",
            (person_id,),
        )
        return cur.fetchone()[0]


def get_keg_state(conn) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT ks.team_name, ks.capacity,
                   COALESCE(bl.total, 0) AS logged_total,
                   ks.finished_at
            FROM team_keg_state ks
            LEFT JOIN (
                SELECT team_name, COUNT(*) AS total
                FROM brew_log
                WHERE status = 'active' AND source = 'keg'
                GROUP BY team_name
            ) bl ON ks.team_name = bl.team_name
        """)
        return {row["team_name"]: dict(row) for row in cur.fetchall()}


def log_brew(conn, person_id: int) -> tuple[dict | None, str | None, dict | None]:
    """Log a keg brew. Returns (entry, error, person); person is included so
    callers don't re-fetch it for rendering."""
    person = get_person(conn, person_id)
    if not person or not person["team_name"]:
        return None, "no_team", person
    keg = get_keg_state(conn)
    team_keg = keg.get(person["team_name"], {})
    if team_keg.get("logged_total", 0) >= team_keg.get("capacity", 330):
        return None, "keg_cap", person
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) "
            "VALUES (%s, %s, 'keg') RETURNING *",
            (person_id, person["team_name"]),
        )
        return dict(cur.fetchone()), None, person


def admin_log_brew(conn, person_id: int, source: str = "keg",
                   admin_override: bool = False) -> tuple[dict | None, str | None]:
    person = get_person(conn, person_id)
    if not person or not person["team_name"]:
        return None, "no_team"
    if source == "keg" and not admin_override:
        keg = get_keg_state(conn)
        team_keg = keg.get(person["team_name"], {})
        if team_keg.get("logged_total", 0) >= team_keg.get("capacity", 330):
            return None, "keg_cap"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) "
            "VALUES (%s, %s, %s) RETURNING *",
            (person_id, person["team_name"], source),
        )
        return dict(cur.fetchone()), None


def reverse_brew(conn, entry_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, person_id, team_name, source FROM brew_log "
            "WHERE id = %s AND status = 'active'",
            (entry_id,),
        )
        original = cur.fetchone()
        if not original:
            return False
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source, status, reversal_of_entry_id) "
            "VALUES (%s, %s, %s, 'reversed', %s)",
            (original[1], original[2], original[3], entry_id),
        )
        cur.execute(
            "UPDATE brew_log SET status = 'reversed' WHERE id = %s",
            (entry_id,),
        )
        return True


def create_person(conn, full_name: str, nickname: str | None, team_name: str | None):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO people (full_name, nickname, team_name, status) "
            "VALUES (%s, %s, %s, %s)",
            (full_name, nickname or None, team_name or None,
             "active" if team_name else "pre_registered"),
        )


def _split_team_points(teams: list[str], p1, p2) -> dict:
    """Map the two stored point columns onto the two fixed team names."""
    return {teams[0]: p1, teams[1]: p2}


def _get_brew_cup_scores(conn, teams: list[str]) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT points_available FROM event_master WHERE name = 'Brew Cup'")
        row = cur.fetchone()
        if not row:
            return {t: 0 for t in teams}
        points = row[0]
        cur.execute(
            "SELECT team_name, COUNT(*) FROM brew_log "
            "WHERE status = 'active' GROUP BY team_name"
        )
        totals = {r[0]: r[1] for r in cur.fetchall()}
        leader = max(totals.values()) if totals else 0
        if leader == 0:
            return {t: 0 for t in teams}
        return {t: round((totals.get(t, 0) / leader) * points) for t in teams}


def get_events(conn, teams: list[str] | None = None,
               brew_cup: dict | None = None) -> list[dict]:
    teams = teams or get_team_names(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT em.id, em.name, em.status, em.points_available,
                   er.team_1_points, er.team_2_points, er.entered_by
            FROM event_master em
            LEFT JOIN event_results er ON em.id = er.event_id
            ORDER BY em.id
        """)
        events = []
        for r in cur.fetchall():
            e = dict(r)
            e["scores"] = _split_team_points(
                teams, e.pop("team_1_points"), e.pop("team_2_points")
            )
            events.append(e)
    if brew_cup is None:
        brew_cup = _get_brew_cup_scores(conn, teams)
    for e in events:
        if e["name"] == "Brew Cup":
            e["scores"] = brew_cup
    return events


def get_team_scores(conn, teams: list[str] | None = None,
                    brew_cup: dict | None = None) -> dict:
    teams = teams or get_team_names(conn)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(er.team_1_points), 0),
                   COALESCE(SUM(er.team_2_points), 0)
            FROM event_results er
            JOIN event_master em ON er.event_id = em.id
            WHERE em.name != 'Brew Cup'
        """)
        row = cur.fetchone()
    scores = _split_team_points(teams, row[0], row[1])
    if brew_cup is None:
        brew_cup = _get_brew_cup_scores(conn, teams)
    return {t: scores[t] + brew_cup[t] for t in teams}


def get_dashboard_context(conn) -> dict:
    """Shared render context for the /dashboard and /tv pages. Computes the
    team list and Brew Cup scores once and threads them through, so the
    proportional formula runs a single time per page load."""
    teams = get_team_names(conn)
    brew_cup = _get_brew_cup_scores(conn, teams)
    return {
        "teams": teams,
        "scores": get_team_scores(conn, teams, brew_cup),
        "events": get_events(conn, teams, brew_cup),
        "keg_state": get_keg_state(conn),
        "leaderboard": get_leaderboard(conn),
    }


def get_leaderboard(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT p.id, p.full_name, p.nickname, p.team_name, COUNT(*) AS count
            FROM brew_log bl
            JOIN people p ON bl.person_id = p.id
            WHERE bl.status = 'active'
            GROUP BY p.id, p.full_name, p.nickname, p.team_name
            ORDER BY count DESC
        """)
        return [
            {"person": {"full_name": r["full_name"], "nickname": r["nickname"],
                         "team_name": r["team_name"]}, "count": r["count"]}
            for r in cur.fetchall()
        ]


def get_brew_log(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT bl.id, bl.person_id, bl.team_name, bl.source, bl.status,
                   COALESCE(p.nickname, p.full_name) AS person_name
            FROM brew_log bl
            JOIN people p ON bl.person_id = p.id
            ORDER BY bl.id DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def create_survey_submission(conn, full_name, nickname, arrival_day, arrival_time,
                             skill_1, skill_2, skill_3, brew_rank, notes):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO people (full_name, nickname) VALUES (%s, %s) "
            "ON CONFLICT (full_name) DO UPDATE SET "
            "nickname = EXCLUDED.nickname, updated_at = NOW() "
            "RETURNING id",
            (full_name, nickname or None),
        )
        person_id = cur.fetchone()["id"]

        cur.execute(
            "INSERT INTO team_survey_responses "
            "(person_id, expected_arrival_day, expected_arrival_time, "
            "skill_1, skill_2, skill_3, brew_drinking_skill_rank, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (person_id) DO UPDATE SET "
            "expected_arrival_day = EXCLUDED.expected_arrival_day, "
            "expected_arrival_time = EXCLUDED.expected_arrival_time, "
            "skill_1 = EXCLUDED.skill_1, skill_2 = EXCLUDED.skill_2, "
            "skill_3 = EXCLUDED.skill_3, "
            "brew_drinking_skill_rank = EXCLUDED.brew_drinking_skill_rank, "
            "notes = EXCLUDED.notes, updated_at = NOW()",
            (person_id, arrival_day, arrival_time or None,
             skill_1 or None, skill_2 or None, skill_3 or None, brew_rank, notes or None),
        )
        return person_id


def assign_team(conn, person_id: int, team_name: str | None):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE people SET team_name = %s, updated_at = NOW() WHERE id = %s",
            (team_name or None, person_id),
        )


def finalize_teams(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE people SET status = 'active', updated_at = NOW() "
            "WHERE team_name IS NOT NULL AND status = 'pre_registered'"
        )
        return cur.rowcount


def save_event_score(conn, event_id: int, team_1_points: int, team_2_points: int,
                     entered_by: str | None = None):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO event_results (event_id, team_1_points, team_2_points, entered_by) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (event_id) DO UPDATE SET "
            "team_1_points = EXCLUDED.team_1_points, team_2_points = EXCLUDED.team_2_points, "
            "entered_by = EXCLUDED.entered_by, updated_at = NOW()",
            (event_id, team_1_points, team_2_points, entered_by),
        )
        cur.execute(
            "UPDATE event_master SET status = 'completed', updated_at = NOW() WHERE id = %s",
            (event_id,),
        )


def set_event_status(conn, event_id: int, status: str) -> bool:
    """Admin override of an event's lifecycle status. Returns False (no write)
    for an unrecognized status or unknown event."""
    if status not in EVENT_STATUSES:
        return False
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE event_master SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, event_id),
        )
        return cur.rowcount > 0


def get_survey_responses(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT p.full_name, tsr.expected_arrival_day, tsr.expected_arrival_time,
                   tsr.skill_1, tsr.skill_2, tsr.skill_3,
                   tsr.brew_drinking_skill_rank, tsr.notes
            FROM team_survey_responses tsr
            JOIN people p ON tsr.person_id = p.id
            ORDER BY p.full_name
        """)
        result = []
        for row in cur.fetchall():
            r = dict(row)
            skills = [s for s in [r.pop("skill_1"), r.pop("skill_2"), r.pop("skill_3")] if s]
            r["top_3_skills"] = skills
            result.append(r)
        return result
