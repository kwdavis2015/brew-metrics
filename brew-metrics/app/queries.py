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
            SELECT ks.team_name,
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


def log_brew(conn, person_id: int, source: str = "keg") -> tuple[dict | None, str | None, dict | None]:
    """Log a brew. Returns (entry, error, person); person is included so
    callers don't re-fetch it for rendering."""
    person = get_person(conn, person_id)
    if not person or not person["team_name"]:
        return None, "no_team", person
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) "
            "VALUES (%s, %s, %s) RETURNING *",
            (person_id, person["team_name"], source),
        )
        return dict(cur.fetchone()), None, person


def admin_log_brew(conn, person_id: int, source: str = "keg") -> tuple[dict | None, str | None]:
    person = get_person(conn, person_id)
    if not person or not person["team_name"]:
        return None, "no_team"
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


def _get_beers_drank_scores(conn, teams: list[str]) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT team_name, COUNT(*) FROM brew_log "
            "WHERE status = 'active' GROUP BY team_name"
        )
        totals = {r[0]: r[1] for r in cur.fetchall()}
    return {t: round(totals.get(t, 0) * 0.4) for t in teams}


def get_events(conn, teams: list[str] | None = None,
               beers_drank: dict | None = None) -> list[dict]:
    teams = teams or get_team_names(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT em.id, em.name, em.status, em.points_available,
                   em.event_type, em.category,
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

    b3_ids = [e["id"] for e in events if e.get("event_type") == "best_of_3"]
    if b3_ids:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT event_id, round_number, winner_team FROM event_round_results "
                "WHERE event_id = ANY(%s) ORDER BY event_id, round_number",
                (b3_ids,)
            )
            rounds_by_event: dict[int, dict[int, str]] = {}
            for r in cur.fetchall():
                rounds_by_event.setdefault(r["event_id"], {})[r["round_number"]] = r["winner_team"]
    else:
        rounds_by_event = {}

    if beers_drank is None:
        beers_drank = _get_beers_drank_scores(conn, teams)
    for e in events:
        if e["name"] == "Beers Drank":
            e["scores"] = beers_drank
        if e.get("event_type") == "best_of_3":
            rnd_map = rounds_by_event.get(e["id"], {})
            e["rounds"] = rnd_map
            win_counts: dict[str, int] = {}
            for w in rnd_map.values():
                win_counts[w] = win_counts.get(w, 0) + 1
            e["round_wins"] = win_counts
    return events


def get_adjustment_totals(conn, teams: list[str]) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT team_name, COALESCE(SUM(amount), 0) FROM admin_adjustments "
            "WHERE team_name IS NOT NULL GROUP BY team_name"
        )
        totals = {r[0]: r[1] for r in cur.fetchall()}
    return {t: totals.get(t, 0) for t in teams}


def get_admin_adjustments(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, adjustment_type, team_name, amount, reason, entered_by, created_at "
            "FROM admin_adjustments ORDER BY created_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]


def add_cheat_deduction(conn, team_name: str, points: int, reason: str, entered_by: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO admin_adjustments "
            "(adjustment_type, team_name, amount, reason, entered_by) "
            "VALUES ('cheat_deduction', %s, %s, %s, %s)",
            (team_name, -abs(points), reason, entered_by),
        )


def get_team_scores(conn, teams: list[str] | None = None,
                    beers_drank: dict | None = None) -> dict:
    teams = teams or get_team_names(conn)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(er.team_1_points), 0),
                   COALESCE(SUM(er.team_2_points), 0)
            FROM event_results er
            JOIN event_master em ON er.event_id = em.id
            WHERE em.name != 'Beers Drank'
        """)
        row = cur.fetchone()
    scores = _split_team_points(teams, row[0], row[1])
    if beers_drank is None:
        beers_drank = _get_beers_drank_scores(conn, teams)
    adjustments = get_adjustment_totals(conn, teams)
    return {t: scores[t] + beers_drank[t] + adjustments[t] for t in teams}


def get_team_beer_totals(conn, teams: list[str]) -> dict:
    """Total active brew_log rows per team (keg + byob combined)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT team_name, COUNT(*) FROM brew_log WHERE status = 'active' GROUP BY team_name"
        )
        totals = {r[0]: r[1] for r in cur.fetchall()}
    return {t: totals.get(t, 0) for t in teams}


def get_byob_totals(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT team_name, COUNT(*) FROM brew_log "
            "WHERE status = 'active' AND source = 'byob' GROUP BY team_name"
        )
        return {r[0]: r[1] for r in cur.fetchall()}


def get_dashboard_context(conn) -> dict:
    """Shared render context for the /dashboard and /tv pages. Computes the
    team list and Brew Cup scores once and threads them through, so the
    proportional formula runs a single time per page load."""
    teams = get_team_names(conn)
    beers_drank = _get_beers_drank_scores(conn, teams)
    team_beer_totals = get_team_beer_totals(conn, teams)
    return {
        "teams": teams,
        "scores": get_team_scores(conn, teams, beers_drank),
        "events": get_events(conn, teams, beers_drank),
        "keg_state": get_keg_state(conn),
        "byob_totals": get_byob_totals(conn),
        "team_beer_totals": team_beer_totals,
        "total_beers": sum(team_beer_totals.values()),
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


def create_survey_submission(
    conn, full_name, nickname, arrival_day, arrival_time,
    skill_1, skill_2, skill_3, brew_drinking_level, notes,
    beers_pledged, score_prediction_red, score_prediction_blue,
    first_to_puke, first_to_tap_out,
):
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
            "skill_1, skill_2, skill_3, brew_drinking_level, notes, "
            "beers_pledged, score_prediction_red, score_prediction_blue, "
            "first_to_puke, first_to_tap_out) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (person_id) DO UPDATE SET "
            "expected_arrival_day = EXCLUDED.expected_arrival_day, "
            "expected_arrival_time = EXCLUDED.expected_arrival_time, "
            "skill_1 = EXCLUDED.skill_1, skill_2 = EXCLUDED.skill_2, "
            "skill_3 = EXCLUDED.skill_3, "
            "brew_drinking_level = EXCLUDED.brew_drinking_level, "
            "notes = EXCLUDED.notes, "
            "beers_pledged = EXCLUDED.beers_pledged, "
            "score_prediction_red = EXCLUDED.score_prediction_red, "
            "score_prediction_blue = EXCLUDED.score_prediction_blue, "
            "first_to_puke = EXCLUDED.first_to_puke, "
            "first_to_tap_out = EXCLUDED.first_to_tap_out, "
            "updated_at = NOW()",
            (person_id, arrival_day, arrival_time or None,
             skill_1 or None, skill_2 or None, skill_3 or None,
             brew_drinking_level or None, notes or None,
             beers_pledged or None, score_prediction_red or None, score_prediction_blue or None,
             first_to_puke or None, first_to_tap_out or None),
        )

        return person_id


def assign_team(conn, person_id: int, team_name: str | None):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE people SET team_name = %s, updated_at = NOW() WHERE id = %s",
            (team_name or None, person_id),
        )


def delete_person(conn, person_id: int) -> bool:
    """Fully purge a person and every row that references them.

    No FK uses ON DELETE CASCADE, so children are removed in dependency order
    inside a single transaction. Returns False if the person does not exist.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM people WHERE id = %s", (person_id,))
        if cur.fetchone() is None:
            return False

        # admin_adjustments references both people and brew_log entries.
        cur.execute(
            "DELETE FROM admin_adjustments "
            "WHERE person_id = %s "
            "OR related_entry_id IN (SELECT id FROM brew_log WHERE person_id = %s)",
            (person_id, person_id),
        )
        # Reversal rows self-reference brew_log; drop them before originals.
        cur.execute(
            "DELETE FROM brew_log "
            "WHERE reversal_of_entry_id IN (SELECT id FROM brew_log WHERE person_id = %s)",
            (person_id,),
        )
        cur.execute("DELETE FROM brew_log WHERE person_id = %s", (person_id,))
        cur.execute("DELETE FROM team_survey_responses WHERE person_id = %s", (person_id,))
        cur.execute("DELETE FROM people WHERE id = %s", (person_id,))
        return True


def finalize_teams(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE people SET status = 'active', updated_at = NOW() "
            "WHERE team_name IS NOT NULL AND status = 'pre_registered'"
        )
        return cur.rowcount


def save_event_winner(conn, event_id: int, winner_team: str,
                      entered_by: str | None = None) -> bool:
    teams = get_team_names(conn)
    if winner_team not in teams:
        return False
    with conn.cursor() as cur:
        cur.execute("SELECT points_available FROM event_master WHERE id = %s", (event_id,))
        row = cur.fetchone()
        if not row:
            return False
        pts = row[0]
    t1_pts = pts if teams[0] == winner_team else 0
    t2_pts = pts if teams[1] == winner_team else 0
    save_event_score(conn, event_id, t1_pts, t2_pts, entered_by)
    return True


def save_round_result(conn, event_id: int, round_number: int, winner_team: str,
                      entered_by: str | None = None) -> bool:
    teams = get_team_names(conn)
    if winner_team not in teams or round_number not in (1, 2, 3):
        return False
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO event_round_results (event_id, round_number, winner_team, entered_by) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (event_id, round_number) DO UPDATE SET "
            "winner_team = EXCLUDED.winner_team, entered_by = EXCLUDED.entered_by",
            (event_id, round_number, winner_team, entered_by),
        )
        cur.execute(
            "SELECT winner_team, COUNT(*) FROM event_round_results "
            "WHERE event_id = %s GROUP BY winner_team",
            (event_id,),
        )
        win_counts = {r[0]: r[1] for r in cur.fetchall()}
    for team in teams:
        if win_counts.get(team, 0) >= 2:
            save_event_winner(conn, event_id, team, entered_by)
            return True
    set_event_status(conn, event_id, "in_progress")
    return True


def reset_event(conn, event_id: int):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM event_round_results WHERE event_id = %s", (event_id,))
        cur.execute("DELETE FROM event_results WHERE event_id = %s", (event_id,))
        cur.execute(
            "UPDATE event_master SET status = 'pending', updated_at = NOW() WHERE id = %s",
            (event_id,),
        )


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


def _fmt_bucket(bucket, scale: str) -> str:
    if scale == "weekend":
        return bucket.strftime("%a %-d")
    h = bucket.hour
    ampm = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    if scale == "day":
        return f"{h12}{ampm}"
    return f"{h12}:{bucket.minute:02d}{ampm}"


def get_brew_timeseries(conn, scale: str = "day") -> dict:
    bucket_exprs = {
        "weekend": "DATE(created_at)",
        "day": "DATE_TRUNC('hour', created_at)",
        "hour": (
            "DATE_TRUNC('hour', created_at) + "
            "INTERVAL '1 minute' * (EXTRACT(minute FROM created_at)::int / 15 * 15)"
        ),
    }
    bucket_expr = bucket_exprs.get(scale, bucket_exprs["day"])

    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {bucket_expr} AS bucket, team_name, COUNT(*) AS cnt "
            "FROM brew_log WHERE status = 'active' "
            "GROUP BY bucket, team_name ORDER BY bucket"
        )
        team_rows = cur.fetchall()

    if not team_rows:
        return {"labels": [], "total": [], "by_team": {}, "by_person": []}

    all_buckets = sorted({r[0] for r in team_rows})
    team_counts: dict = {}
    for bucket, team, cnt in team_rows:
        team_counts.setdefault(bucket, {})[team] = cnt

    teams = ["Red", "Blue"]
    labels = [_fmt_bucket(b, scale) for b in all_buckets]
    total = [sum(team_counts[b].get(t, 0) for t in teams) for b in all_buckets]
    by_team = {t: [team_counts[b].get(t, 0) for b in all_buckets] for t in teams}

    # Rebuild bucket_expr with explicit table alias to avoid ambiguous created_at
    bucket_exprs_aliased = {
        "weekend": "DATE(bl.created_at)",
        "day": "DATE_TRUNC('hour', bl.created_at)",
        "hour": (
            "DATE_TRUNC('hour', bl.created_at) + "
            "INTERVAL '1 minute' * (EXTRACT(minute FROM bl.created_at)::int / 15 * 15)"
        ),
    }
    bucket_expr_aliased = bucket_exprs_aliased.get(scale, bucket_exprs_aliased["day"])
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {bucket_expr_aliased} AS bucket, "
            "COALESCE(p.nickname, p.full_name) AS name, COUNT(*) AS cnt "
            "FROM brew_log bl JOIN people p ON bl.person_id = p.id "
            "WHERE bl.status = 'active' "
            "GROUP BY bucket, p.id, p.nickname, p.full_name ORDER BY bucket"
        )
        person_rows = cur.fetchall()

    person_totals: dict[str, int] = {}
    person_data: dict[str, dict] = {}
    for bucket, name, cnt in person_rows:
        person_totals[name] = person_totals.get(name, 0) + cnt
        person_data.setdefault(name, {})[bucket] = cnt

    top5 = sorted(person_totals, key=lambda n: -person_totals[n])[:5]
    by_person = [
        {"label": name, "data": [person_data[name].get(b, 0) for b in all_buckets], "total": person_totals[name]}
        for name in top5
    ]

    return {"labels": labels, "total": total, "by_team": by_team, "by_person": by_person}


def get_weekend_started(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM app_settings WHERE key = 'weekend_started'")
        row = cur.fetchone()
        return row is not None and row[0] == 'true'


def set_weekend_started(conn, value: bool) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE app_settings SET value = %s WHERE key = 'weekend_started'",
            ('true' if value else 'false',),
        )


def reset_weekend_data(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE admin_adjustments, event_results, event_round_results, brew_log RESTART IDENTITY"
        )
        cur.execute("UPDATE event_master SET status = 'pending', updated_at = NOW()")
        cur.execute("UPDATE team_keg_state SET finished_at = NULL")
        cur.execute(
            "UPDATE app_settings SET value = 'false' WHERE key = 'weekend_started'"
        )


def get_survey_responses(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT p.id, p.full_name, tsr.expected_arrival_day, tsr.expected_arrival_time,
                   tsr.skill_1, tsr.skill_2, tsr.skill_3,
                   tsr.brew_drinking_level, tsr.notes,
                   tsr.beers_pledged, tsr.score_prediction_red, tsr.score_prediction_blue,
                   tsr.first_to_puke, tsr.first_to_tap_out
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


def get_brew_log_export(conn) -> list[dict]:
    """Full brew log for CSV download: timestamp + true full name (not nickname)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT bl.created_at, p.full_name, bl.team_name, bl.source,
                   bl.status, bl.reversal_of_entry_id
            FROM brew_log bl
            JOIN people p ON bl.person_id = p.id
            ORDER BY bl.created_at
        """)
        return [dict(r) for r in cur.fetchall()]


def get_survey_export(conn) -> list[dict]:
    """Full survey for CSV download, keyed by full name and timestamp."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT p.full_name, tsr.created_at,
                   tsr.expected_arrival_day, tsr.expected_arrival_time,
                   tsr.skill_1, tsr.skill_2, tsr.skill_3,
                   tsr.brew_drinking_level, tsr.beers_pledged,
                   tsr.score_prediction_red, tsr.score_prediction_blue,
                   tsr.first_to_puke, tsr.first_to_tap_out, tsr.notes
            FROM team_survey_responses tsr
            JOIN people p ON tsr.person_id = p.id
            ORDER BY p.full_name
        """)
        return [dict(r) for r in cur.fetchall()]
