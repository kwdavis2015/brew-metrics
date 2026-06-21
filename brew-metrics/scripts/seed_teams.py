#!/usr/bin/env python3
"""
Seed real participant data directly into the database.

Usage:
    # Local (docker compose postgres must be running):
    docker compose up -d db
    python scripts/seed_teams.py --target local

    # RDS (requires AWS credentials + network access to the RDS endpoint):
    python scripts/seed_teams.py --target rds [--secret brew-metrics/db-credentials]

Network note for RDS:
    The RDS instance is in a private subnet (publicly_accessible = false).
    You need one of:
      - SSM port-forwarding through an ECS task
      - Temporarily set publicly_accessible = true in terraform, run this script, revert
    The script will fail with a connection error if the endpoint is unreachable.

Re-running is safe — all inserts are ON CONFLICT DO UPDATE.
"""

import argparse
import json
import sys
from pathlib import Path

import psycopg2

LOCAL_DB_URL = "postgresql://brewadmin:localdev@localhost:5432/brewmetrics"
SCHEMA_PATH = Path(__file__).parent.parent / "app" / "schema.sql"

TEAMS: dict[str, list[str]] = {
    "Riks": [
        "Erik Wade",
        "Alex Amos",
        "Scott Laurion",
        "Dane Morison",
        "Keith Curry",
        "Alex Oliver",
        "Lukas Senczyszyn",
        "Gunnar Johnson",
        "Avery Schmidt",
        "Clark Reisch",
        "Nathan Ackerman",
    ],
    "Wades": [
        "Matt LeMay",
        "Kevin Davis",
        "Jon Toma",
        "Kyle Pinozek",
        "Mike Bieke",
        "Jeremy Davis",
        "Neal Nordstrom",
        "Braeton Ardell",
        "Dylan Tantalo",
        "Evan Tumey",
        "Austin Gongos",
    ],
}


def get_rds_url(secret_name: str) -> str:
    try:
        import boto3
    except ImportError:
        print("ERROR: boto3 is required for --target rds. Install it with: pip install boto3")
        sys.exit(1)

    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        print(f"ERROR: could not fetch secret '{secret_name}': {e}")
        sys.exit(1)

    secret = json.loads(response["SecretString"])
    return secret["url"]


def apply_schema(conn) -> None:
    print("Applying schema...")
    sql = SCHEMA_PATH.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("  ok")


def seed_people(conn) -> None:
    print("Seeding participants...")
    with conn.cursor() as cur:
        for team, members in TEAMS.items():
            for full_name in members:
                cur.execute(
                    """
                    INSERT INTO people (full_name, team_name, status)
                    VALUES (%s, %s, 'active')
                    ON CONFLICT (full_name) DO UPDATE
                        SET team_name = EXCLUDED.team_name,
                            status    = 'active',
                            updated_at = NOW()
                    """,
                    (full_name, team),
                )
                print(f"  {full_name} -> {team}")
    conn.commit()


def verify(conn) -> None:
    print("\nVerification:")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT team_name, COUNT(*) FROM people WHERE status = 'active' GROUP BY team_name ORDER BY team_name"
        )
        for team, count in cur.fetchall():
            print(f"  {team}: {count} members")
        cur.execute("SELECT COUNT(*) FROM people WHERE status = 'active'")
        total = cur.fetchone()[0]
    print(f"  Total active: {total}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed participant data into brew-metrics DB")
    parser.add_argument(
        "--target",
        choices=["local", "rds"],
        required=True,
        help="local = docker compose postgres; rds = AWS RDS via Secrets Manager",
    )
    parser.add_argument(
        "--secret",
        default="brew-metrics/db-credentials",
        help="Secrets Manager secret name (rds target only)",
    )
    args = parser.parse_args()

    if args.target == "local":
        db_url = LOCAL_DB_URL
        print(f"Target: local ({db_url})")
    else:
        print(f"Target: RDS (fetching credentials from '{args.secret}')")
        db_url = get_rds_url(args.secret)

    try:
        conn = psycopg2.connect(db_url)
    except psycopg2.OperationalError as e:
        print(f"ERROR: could not connect to database: {e}")
        if args.target == "rds":
            print("Hint: RDS is in a private subnet — ensure you have network access (see script header).")
        sys.exit(1)

    try:
        apply_schema(conn)
        seed_people(conn)
        verify(conn)
    finally:
        conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
