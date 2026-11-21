import random, shutil, sqlite3, glob
from datetime import date, timedelta

import pytest

import database, learner_model as lm, question_bank as qb, misconception as mc
from concept_graph import CONCEPTS, get_prerequisites
from engine import process_answer
from question_generator import get_next_question
from diagnostic import get_diagnostic_questions


@pytest.fixture
def sid(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_NAME", str(tmp_path / "t.db"))
    database.create_tables()
    s = database.add_student("Test")
    lm.initialize_mastery(s)
    return s


def test_bank_size_and_tiers():
    qs = qb.load_questions()
    assert len(qs) >= 40
    for c in CONCEPTS:
        assert {q["difficulty"] for q in qs if q["concept"] == c} == set(qb.DIFFICULTIES), c


def test_mastery_direction_and_bounds():
    assert lm.calculate_mastery(50, True, "hard") > 50
    assert lm.calculate_mastery(50, False, "easy") < 50
    assert lm.calculate_mastery(100, True, "easy") <= 100
    assert lm.calculate_mastery(0, False, "easy") >= 0
    assert lm.calculate_mastery(50, True, "hard") > lm.calculate_mastery(50, True, "easy")
    assert lm.calculate_mastery(60, False, "easy") < lm.calculate_mastery(60, False, "advanced")
    assert lm.calculate_mastery(80, True, "medium", flawed=True) < lm.calculate_mastery(80, True, "hard")


def test_difficulty_calibration():
    assert lm.calibrate_difficulty(30) == "easy"
    assert lm.calibrate_difficulty(30, [1, 1]) == "medium"      # streak -> harder
    assert lm.calibrate_difficulty(60, [0, 0]) == "easy"        # struggling -> easier
    assert lm.calibrate_difficulty(95, [1, 1]) == "advanced"    # capped


def test_planner_uses_prerequisites(sid):
    for c, s in [("Electric Charge", 90), ("Potential Difference", 90), ("Resistance", 90),
                 ("Electric Current", 30), ("Ohm's Law", 10), ("Electric Power", 90),
                 ("Series and Parallel Circuits", 90)]:
        database.update_mastery(sid, c, s)
    concept, reason = lm.plan_next_concept(sid)
    assert concept == "Electric Current" and "foundation" in reason


def test_new_student_starts_at_foundations(sid):
    foundations = {c for c in CONCEPTS if not get_prerequisites(c)}
    for seed in range(20):
        assert lm.plan_next_concept(sid, rng=random.Random(seed))[0] in foundations


def test_due_revision_boosts_priority(sid):
    for c in CONCEPTS:
        database.update_mastery(sid, c, 80)
    database.update_mastery(sid, "Electric Power", 78)
    database.save_revision(sid, "Electric Power", (date.today() - timedelta(days=1)).isoformat())
    assert lm.plan_next_concept(sid)[0] == "Electric Power"


def test_options_shuffled_and_answer_present(sid):
    firsts = set()
    for seed in range(40):
        q, _ = get_next_question(sid, force_concept="Ohm's Law", rng=random.Random(seed))
        assert q["answer"] in q["options"]
        firsts.add(q["options"].index(q["answer"]))
    assert len(firsts) > 1


def test_no_immediate_repeats(sid):
    rng, ids = random.Random(7), []
    for _ in range(6):
        q, _ = get_next_question(sid, force_concept="Electric Power", rng=rng)
        wrong = [o for o in q["options"] if o != q["answer"]][0]
        process_answer(sid, q, wrong, "", use_llm=False)
        ids.append(q["id"])
    assert len(set(ids)) == len(ids)


def test_end_to_end_answer_flow(sid):
    q = next(x for x in qb.load_questions() if x["concept"] == "Electric Current" and x["difficulty"] == "hard")
    bad = process_answer(sid, q, "Less than 0.5 A, because the bulb uses up current", "it uses up current", use_llm=False)
    assert not bad["correct"] and bad["detection"]["id"] == "CUR_USED_UP" and bad["delta"] < 0
    assert (date.today() + timedelta(days=1)) == bad["next_revision"]
    good = process_answer(sid, q, q["answer"], "charge is conserved so current is the same", use_llm=False)
    assert good["correct"] and good["delta"] > 0
    df = database.get_attempts_df(sid)
    assert len(df) == 2 and df.iloc[0]["misconception_id"] == "CUR_USED_UP"
    assert len(database.get_mastery_history_df(sid)) > len(CONCEPTS)


def test_right_answer_wrong_reasoning_flagged(sid):
    q = next(x for x in qb.load_questions() if x["concept"] == "Electric Current" and x["difficulty"] == "hard")
    r = process_answer(sid, q, q["answer"], "I guessed, current gets used up a little", use_llm=False)
    assert r["correct"] and r["detection"]["flawed_reasoning"]


def test_diagnostic_covers_every_concept_and_is_stable(sid):
    qs = get_diagnostic_questions(random.Random(1))
    assert [q["concept"] for q in qs] == CONCEPTS
    res = [process_answer(sid, q, q["answer"], context="diagnostic", use_llm=False) for q in qs]
    assert all(r["correct"] for r in res)


def test_migration_from_old_schema(tmp_path, monkeypatch):
    p = str(tmp_path / "old.db")
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, concept TEXT,"
              " question TEXT, correct INTEGER, reasoning TEXT, misconception TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("INSERT INTO attempts (student_id, concept, question, correct, reasoning, misconception) VALUES (1,'Ohm''s Law','q',0,'r','m')")
    c.commit(); c.close()
    monkeypatch.setattr(database, "DB_NAME", p)
    database.create_tables()
    df = database.get_attempts_df()
    assert {"question_id", "difficulty", "selected", "misconception_id"} <= set(df.columns) and len(df) == 1


def test_users_real_database_still_works(tmp_path, monkeypatch):
    src = glob.glob("/mnt/user-data/attachments/*/*tutor.db")
    if not src:
        pytest.skip("real tutor.db not available")
    p = str(tmp_path / "copy.db"); shutil.copy(src[0], p)
    monkeypatch.setattr(database, "DB_NAME", p)
    database.create_tables()
    for s, _ in database.get_students():
        lm.initialize_mastery(s)
        assert len(database.get_mastery(s)) == len(CONCEPTS)
    database.get_attempts_df()


def test_misconception_negation():
    assert mc.detect_misconception("Electric Current", "current is not used up", True, use_llm=False)["id"] is None
    assert mc.detect_misconception("Electric Current", "the bulb uses up current", True, use_llm=False)["flawed_reasoning"]
