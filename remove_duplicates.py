import sqlite3

conn = sqlite3.connect("tutor.db")
TABLES = ("attempts", "mastery", "revisions", "mastery_history")

students = conn.execute("SELECT id, name FROM students ORDER BY id").fetchall()

# group ids by lower-cased name
groups = {}
for sid, name in students:
    groups.setdefault(name.strip().lower(), []).append(sid)

removed = 0
for name, ids in groups.items():
    if len(ids) < 2:
        continue
    # keep the copy with the most attempts (lowest id if tied), delete the rest
    def n_attempts(sid):
        return conn.execute("SELECT COUNT(*) FROM attempts WHERE student_id=?", (sid,)).fetchone()[0]
    keep = max(ids, key=lambda s: (n_attempts(s), -s))
    for sid in ids:
        if sid != keep:
            for t in TABLES:
                conn.execute(f"DELETE FROM {t} WHERE student_id = ?", (sid,))
            conn.execute("DELETE FROM students WHERE id = ?", (sid,))
            removed += 1
            print(f"deleted duplicate '{name}' (id {sid}), kept id {keep}")

conn.commit()
conn.close()
print(f"Done. Removed {removed} duplicate(s).")