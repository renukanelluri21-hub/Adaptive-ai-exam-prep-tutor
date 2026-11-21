"""Targeted question selection with difficulty calibration.
Pipeline: planner (weak concept + prerequisites + due revisions) -> calibrated difficulty ->
question from the bank (never one seen recently) or a freshly generated numeric variant."""
import random

import question_bank
from database import get_recent_attempts
from learner_model import (DIFFICULTIES, calibrate_difficulty, plan_next_concept,
                           recent_correct_for)
from database import get_mastery

load_questions = question_bank.load_questions


def prepare(question, rng=None):
    """Return a copy with shuffled options (so the right answer isn't always in the same slot)."""
    q = dict(question, options=list(question["options"]))
    (rng or random).shuffle(q["options"])
    return q


def get_next_question(student_id, force_concept=None, rng=None):
    """Return (question, reason). `reason` is shown to the student ('why this question?')."""
    rng = rng or random.Random()
    if force_concept:
        concept, why = force_concept, f"You chose to practise {force_concept}."
    else:
        concept, why = plan_next_concept(student_id, rng=rng)

    score = dict(get_mastery(student_id)).get(concept, 50)
    difficulty = calibrate_difficulty(score, recent_correct_for(student_id, concept))
    seen = {r[1] for r in get_recent_attempts(student_id, limit=8) if r[1]}

    bank = question_bank.load_questions()
    pool = [q for q in bank if q["concept"] == concept and q["id"] not in seen]

    def tier(d):
        return [q for q in pool if q["difficulty"] == d]

    question = None
    # 50%: a freshly generated numeric variant (endless practice); otherwise a bank question
    if question_bank.GENERATORS.get(concept) and (not tier(difficulty) or rng.random() < 0.5):
        question = question_bank.generate_question(concept, difficulty, rng)
    if question is None and tier(difficulty):
        question = rng.choice(tier(difficulty))
    if question is None:  # nearest difficulty
        idx = DIFFICULTIES.index(difficulty)
        for step in (1, -1, 2, -2, 3, -3):
            j = idx + step
            if 0 <= j < len(DIFFICULTIES) and tier(DIFFICULTIES[j]):
                question = rng.choice(tier(DIFFICULTIES[j]))
                break
    if question is None:
        same = [q for q in bank if q["concept"] == concept] or bank
        question = rng.choice(same)

    why += f" Difficulty set to **{question['difficulty']}** based on your recent answers."
    return prepare(question, rng), why
