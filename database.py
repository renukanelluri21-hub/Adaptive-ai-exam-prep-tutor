"""SQLite data layer. Auto-migrates the old schema, so your existing tutor.db keeps working."""
import os
import sqlite3
from datetime import datetime

import pandas as pd

# TUTOR_DB lets tests / demos use a separate database file.
DB_NAME = os.environ.get(
    "TUTOR_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tutor.db")
)


def connect_db():
    return sqlite3.connect(DB_NAME)


def _add_missing_columns(cursor, table, columns):
    existing = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})")}
    for name, ddl in columns.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def create_tables():
    conn = connect_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS mastery (
        student_id INTEGER, concept TEXT, score REAL DEFAULT 50,
        PRIMARY KEY (student_id, concept))""")
    c.execute("""CREATE TABLE IF NOT EXISTS attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, concept TEXT,
        question TEXT, correct INTEGER, reasoning TEXT, misconception TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS revisions (
        student_id INTEGER, concept TEXT, next_revision TEXT,
        PRIMARY KEY (student_id, concept))""")
    c.execute("""CREATE TABLE IF NOT EXISTS mastery_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, concept TEXT,
        score REAL, ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    # migration: new attempt columns
    _add_missing_columns(c, "attempts", {
        "question_id": "TEXT", "difficulty": "TEXT",
        "selected": "TEXT", "misconception_id": "TEXT",
    })
    conn.commit()
    conn.close()


# ---------- students ----------
def add_student(name):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO students (name) VALUES (?)", (name,))
    sid = cur.lastrowid
    conn.commit()
    conn.close()
    return sid


def get_students():
    conn = connect_db()
    rows = conn.execute("SELECT id, name FROM students ORDER BY id").fetchall()
    conn.close()
    return rows

def find_student(name):
    """Case-insensitive lookup. Returns the student id or None."""
    conn = connect_db()
    row = conn.execute("SELECT id FROM students WHERE LOWER(name) = LOWER(?)",
                       (name.strip(),)).fetchone()
    conn.close()
    return row[0] if row else None


def delete_student(student_id):
    """Remove a student and all of their learning data."""
    conn = connect_db()
    for table in ("attempts", "mastery", "revisions", "mastery_history"):
        conn.execute(f"DELETE FROM {table} WHERE student_id = ?", (student_id,))
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
# ---------- mastery ----------
def get_mastery(student_id):
    conn = connect_db()
    rows = conn.execute(
        "SELECT concept, score FROM mastery WHERE student_id = ?", (student_id,)
    ).fetchall()
    conn.close()
    return rows


def update_mastery(student_id, concept, score):
    conn = connect_db()
    conn.execute("""INSERT INTO mastery (student_id, concept, score) VALUES (?, ?, ?)
        ON CONFLICT(student_id, concept) DO UPDATE SET score = excluded.score""",
                 (student_id, concept, score))
    conn.commit()
    conn.close()


def record_mastery_history(student_id, concept, score, ts=None):
    conn = connect_db()
    conn.execute(
        "INSERT INTO mastery_history (student_id, concept, score, ts) VALUES (?, ?, ?, ?)",
        (student_id, concept, score, ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_mastery_history_df(student_id):
    conn = connect_db()
    df = pd.read_sql_query(
        "SELECT concept, score, ts FROM mastery_history WHERE student_id = ? ORDER BY ts, id",
        conn, params=(student_id,))
    conn.close()
    return df


# ---------- attempts ----------
def save_attempt(student_id, concept, question, correct, reasoning, misconception,
                 question_id=None, difficulty=None, selected=None,
                 misconception_id=None, ts=None):
    conn = connect_db()
    conn.execute("""INSERT INTO attempts
        (student_id, concept, question, correct, reasoning, misconception,
         question_id, difficulty, selected, misconception_id, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 (student_id, concept, question, int(correct), reasoning, misconception,
                  question_id, difficulty, selected, misconception_id,
                  ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_attempts(student_id=None):
    """Backwards-compatible tuple rows: student_id, concept, correct, reasoning, misconception, date."""
    conn = connect_db()
    sql = ("SELECT student_id, concept, correct, reasoning, misconception, date FROM attempts")
    if student_id is None:
        rows = conn.execute(sql).fetchall()
    else:
        rows = conn.execute(sql + " WHERE student_id = ?", (student_id,)).fetchall()
    conn.close()
    return rows


def get_attempts_df(student_id=None):
    conn = connect_db()
    sql = "SELECT * FROM attempts"
    params = ()
    if student_id is not None:
        sql += " WHERE student_id = ?"
        params = (student_id,)
    df = pd.read_sql_query(sql + " ORDER BY date, id", conn, params=params)
    conn.close()
    return df


def get_recent_attempts(student_id, concept=None, limit=5):
    """Most recent first: list of (correct, question_id, concept)."""
    conn = connect_db()
    sql = "SELECT correct, question_id, concept FROM attempts WHERE student_id = ?"
    params = [student_id]
    if concept:
        sql += " AND concept = ?"
        params.append(concept)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_attempt_count(student_id, concept):
    conn = connect_db()
    n = conn.execute("SELECT COUNT(*) FROM attempts WHERE student_id=? AND concept=?",
                     (student_id, concept)).fetchone()[0]
    conn.close()
    return n


# ---------- revisions ----------
def save_revision(student_id, concept, next_revision):
    conn = connect_db()
    conn.execute("""INSERT INTO revisions (student_id, concept, next_revision) VALUES (?, ?, ?)
        ON CONFLICT(student_id, concept) DO UPDATE SET next_revision = excluded.next_revision""",
                 (student_id, concept, next_revision))
    conn.commit()
    conn.close()


def get_revisions(student_id):
    conn = connect_db()
    rows = conn.execute(
        "SELECT concept, next_revision FROM revisions WHERE student_id = ? ORDER BY next_revision",
        (student_id,)).fetchall()
    conn.close()
    return rows


# ---------- dashboard / demo helpers ----------
def get_all_mastery_df():
    conn = connect_db()
    df = pd.read_sql_query(
        "SELECT s.id AS student_id, s.name AS student, m.concept, m.score "
        "FROM mastery m JOIN students s ON s.id = m.student_id", conn)
    conn.close()
    return df


def get_or_create_student(name):
    conn = connect_db()
    row = conn.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row[0] if row else add_student(name)


def reset_student(student_id):
    """Wipe a student's learning data (keeps the student). Used by the live demo."""
    conn = connect_db()
    for table in ("attempts", "mastery", "revisions", "mastery_history"):
        conn.execute(f"DELETE FROM {table} WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()
