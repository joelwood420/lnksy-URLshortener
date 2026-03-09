import sys
import os
import threading
import sqlite3
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app
from app import app as flask_app
import db as db_module




SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema.sql')


def make_temp_db():
    """
    Create a real temporary file-based SQLite DB pre-loaded with the schema.
    Returns (db_path, tmp_dir) – caller must clean up tmp_dir when done.
    SQLite file DBs (unlike :memory:) support safe concurrent access from
    multiple connections across threads.
    """
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, 'test.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.close()
    return db_path, tmp_dir


def make_thread_conn(db_path):
    """Open a fresh per-thread connection to the shared file DB."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn



# Test 1 – Concurrent shortcode inserts never produce a duplicate short_code
#
# Simulates the race condition: N threads all try to shorten a *different* URL
# at the same time. Each must end up with a unique shortcode in the DB.

def test_concurrent_shorten_unique_shortcodes():
    """No two concurrent shorten operations should produce the same shortcode."""
    NUM_THREADS = 20
    db_path, tmp_dir = make_temp_db()
    flask_app.secret_key = 'test-secret-key'

    def shorten_one(index):
        url = f"https://example{index}.com"
        with flask_app.app_context():
            from flask import g
            g.db = make_thread_conn(db_path)
            try:
                while True:
                    shortcode = app.generate_shortcode()
                    try:
                        app.save_url(url, shortcode, None, f"Example {index}")
                        break
                    except sqlite3.IntegrityError:
                        continue
            finally:
                g.db.close()

    threads = [threading.Thread(target=shorten_one, args=(i,)) for i in range(NUM_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Inspect results with a fresh connection
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    shortcodes = [row["short_code"] for row in conn.execute("SELECT short_code FROM urls").fetchall()]
    conn.close()
    shutil.rmtree(tmp_dir)

    assert len(shortcodes) == len(set(shortcodes)), (
        f"Duplicate shortcodes found: {shortcodes}"
    )
    assert len(shortcodes) == NUM_THREADS, (
        f"Expected {NUM_THREADS} rows, got {len(shortcodes)}"
    )



# Test 2 – Concurrent click-count increments are not lost
#
# Simulates many redirects hitting the same shortcode simultaneously.
# The final click_count must equal the number of threads that incremented it.

def test_concurrent_click_count_increments():
    """Concurrent click increments must all be recorded (no lost updates)."""
    NUM_CLICKS = 50
    db_path, tmp_dir = make_temp_db()
    flask_app.secret_key = 'test-secret-key'


    with flask_app.app_context():
        from flask import g
        g.db = make_thread_conn(db_path)
        app.save_url("https://click-test.com", "clk", None, "Click Test")
        g.db.close()

    def do_increment():
        with flask_app.app_context():
            from flask import g
            g.db = make_thread_conn(db_path)
            try:
                app.increment_click_count("clk")
            finally:
                g.db.close()

    threads = [threading.Thread(target=do_increment) for _ in range(NUM_CLICKS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    final_count = conn.execute(
        "SELECT click_count FROM urls WHERE short_code = ?", ("clk",)
    ).fetchone()["click_count"]
    conn.close()
    shutil.rmtree(tmp_dir)

    assert final_count == NUM_CLICKS, (
        f"Expected {NUM_CLICKS} clicks, got {final_count}. "
        f"{NUM_CLICKS - final_count} increments were lost."
    )



# Test 3 – WAL mode and busy_timeout are configured on every new connection
#
# Verifies that get_db_connection() applies the pragmas that prevent
# "database is locked" errors under concurrent write load.

def test_db_connection_wal_and_busy_timeout():
    """Each new DB connection must have WAL journal mode and a busy timeout set."""
    from db import get_db_connection

    with flask_app.app_context():
        flask_app.config['TESTING'] = True
        flask_app.secret_key = 'test-secret-key'

        conn = get_db_connection()

        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]

    assert journal_mode == "wal", (
        f"Expected journal_mode=wal, got '{journal_mode}'"
    )
    assert busy_timeout >= 1000, (
        f"Expected busy_timeout >= 1000 ms, got {busy_timeout}"
    )
