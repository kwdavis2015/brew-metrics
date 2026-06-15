import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2 import pool

logger = logging.getLogger(__name__)

_pool: pool.SimpleConnectionPool | None = None


def init_pool(retries: int = 5, delay: float = 2.0):
    global _pool
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL not set — running without database")
        return
    for attempt in range(1, retries + 1):
        try:
            _pool = pool.SimpleConnectionPool(1, 5, db_url)
            logger.info("Database pool initialized")
            return
        except psycopg2.OperationalError as e:
            if attempt == retries:
                logger.error("Database unreachable after %d attempts: %s", retries, e)
                raise
            logger.warning(
                "Database not ready (attempt %d/%d): %s — retrying in %.0fs",
                attempt, retries, e, delay,
            )
            time.sleep(delay)


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
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        logger.info("Schema applied successfully")
    except psycopg2.Error as e:
        logger.error("Schema apply failed: %s", e.pgerror or str(e))
        raise
