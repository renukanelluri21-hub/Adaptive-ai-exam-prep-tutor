import random

import question_bank
from question_generator import prepare
from concept_graph import CONCEPTS


def get_diagnostic_questions(rng=None):
    """One question per concept (full syllabus coverage), mostly medium difficulty,
    in dependency order. Call ONCE and keep the result in st.session_state."""
    rng = rng or random.Random()
    bank = question_bank.load_questions()
    picked = []
    for concept in CONCEPTS:
        pool = [q for q in bank if q["concept"] == concept and q["difficulty"] == "medium"] \
            or [q for q in bank if q["concept"] == concept]
        picked.append(prepare(rng.choice(pool), rng))
    return picked
