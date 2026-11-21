"""Learner model: per-concept mastery that updates after EVERY answer, plus the planner that decides
what to teach next using the concept graph's prerequisites."""
import math
import random
from datetime import date

from concept_graph import CONCEPTS, get_prerequisites
from database import (get_attempt_count, get_mastery, get_revisions, get_recent_attempts,
                      record_mastery_history, update_mastery)

DIFFICULTIES = ["easy", "medium", "hard", "advanced"]

# How much each outcome says about the student (target the score moves toward)
EVIDENCE_CORRECT = {"easy": 75, "medium": 88, "hard": 96, "advanced": 100}
EVIDENCE_WRONG = {"easy": 10, "medium": 20, "hard": 30, "advanced": 40}
FLAWED_REASONING_EVIDENCE = 55   # right answer, flawed thinking: only partial credit
PREREQ_GATE = 55                 # prerequisites must reach this before a dependent concept is taught


def initialize_mastery(student_id):
    existing = dict(get_mastery(student_id))
    for concept in CONCEPTS:
        if concept not in existing:
            update_mastery(student_id, concept, 50)
            record_mastery_history(student_id, concept, 50)


def learning_rate(n_attempts):
    """Fast while we know little (0.40), settling to 0.15 as evidence accumulates."""
    return 0.15 + 0.25 * math.exp(-n_attempts / 4)


def calculate_mastery(old_score, correct, difficulty="medium", n_attempts=0, flawed=False):
    """Difficulty-weighted, confidence-aware update (a light Elo / knowledge-tracing hybrid).
    - Correct on a hard question moves you up more than correct on an easy one.
    - Wrong on an easy question hurts more than wrong on an advanced one.
    - A correct answer never lowers mastery by more than a rounding slip; a wrong one never raises it."""
    lr = learning_rate(n_attempts)
    if correct and flawed:
        target = FLAWED_REASONING_EVIDENCE
        new = old_score + lr * (target - old_score)
        new = max(new, old_score - 3)        # lucky-right answers shouldn't tank you
    elif correct:
        target = EVIDENCE_CORRECT[difficulty]
        new = old_score + lr * max(target - old_score, 0.15 * (100 - old_score))
    else:
        target = EVIDENCE_WRONG[difficulty]
        new = old_score - lr * max(old_score - target, 0.15 * old_score)
    return max(0.0, min(100.0, new))


def update_student_mastery(student_id, concept, correct, difficulty="medium", flawed=False, ts=None):
    old = dict(get_mastery(student_id)).get(concept, 50)
    n = get_attempt_count(student_id, concept)
    new = round(calculate_mastery(old, correct, difficulty, n, flawed), 2)
    update_mastery(student_id, concept, new)
    record_mastery_history(student_id, concept, new, ts)
    return new


def get_weakest_concept(student_id):
    scores = get_mastery(student_id)
    return min(scores, key=lambda item: item[1]) if scores else None


def get_mastery_level(score):
    if score < 40:
        return "Beginner"
    if score < 70:
        return "Developing"
    if score < 85:
        return "Good"
    return "Mastered"


def get_difficulty(score):
    if score < 40:
        return "easy"
    if score < 70:
        return "medium"
    if score < 85:
        return "hard"
    return "advanced"


def calibrate_difficulty(score, recent_correct=()):
    """Base tier from mastery, then nudged by the last two answers on this concept
    (keeps the student in the zone where questions are challenging but doable).
    `recent_correct` is most-recent-first, e.g. [1, 1]."""
    level = DIFFICULTIES.index(get_difficulty(score))
    last2 = list(recent_correct)[:2]
    if len(last2) == 2 and all(last2):
        level = min(level + 1, len(DIFFICULTIES) - 1)
    elif len(last2) == 2 and not any(last2):
        level = max(level - 1, 0)
    return DIFFICULTIES[level]


def plan_next_concept(student_id, rng=None, today=None):
    """Pick the best concept to practise NOW. Returns (concept, reason).
    Priority = low mastery + overdue for revision. Then walk DOWN the prerequisite graph:
    if the chosen concept sits on a weak foundation, teach the foundation first."""
    rng = rng or random
    today = (today or date.today()).isoformat()
    mastery = dict(get_mastery(student_id))
    due = {c for c, d in get_revisions(student_id) if d <= today}

    def score(c):
        return mastery.get(c, 50)

    def priority(c):
        return (100 - score(c)) + (15 if c in due else 0)

    order = CONCEPTS[:]
    rng.shuffle(order)
    candidate = max(order, key=priority)

    root = candidate
    while True:
        weak = [p for p in get_prerequisites(root) if score(p) < PREREQ_GATE]
        if not weak:
            break
        root = min(weak, key=score)

    if root != candidate:
        reason = (f"{candidate} is a priority ({score(candidate):.0f}%), but it builds on {root} "
                  f"({score(root):.0f}%), so let's strengthen that foundation first.")
    elif candidate in due:
        reason = f"{candidate} is due for spaced revision (mastery {score(candidate):.0f}%)."
    else:
        reason = f"{candidate} is your weakest area right now (mastery {score(candidate):.0f}%)."
    return root, reason


def recent_correct_for(student_id, concept):
    return [r[0] for r in get_recent_attempts(student_id, concept, limit=2)]
