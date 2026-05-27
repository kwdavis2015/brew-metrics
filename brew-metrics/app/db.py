import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2 import pool

_pool: pool.SimpleConnectionPool | None = None


def init_pool():
    global _pool
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return
    _pool = pool.SimpleConnectionPool(1, 5, db_url)


def close_pool():
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None


def has_db() -> bool:
    return _pool is not None


@contextmanager
def get_db():
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def get_db_conn():
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def apply_schema():
    if not _pool:
        return
    schema_path = Path(__file__).parent / "schema.sql"
    sql = schema_path.read_text()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
