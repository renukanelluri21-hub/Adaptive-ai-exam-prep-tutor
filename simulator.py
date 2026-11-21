"""Simulated students: used to seed a realistic class for the teacher dashboard and to drive the
'Live Demo' page. Goes through exactly the same engine as a real student."""
import random
from datetime import datetime, timedelta

from engine import process_answer
from question_generator import get_next_question

# Typical sentences a student with each misconception would write (tests the reasoning detector).
REASONING_SAMPLES = {
    "CUR_USED_UP": "The bulb uses up some of the current so less comes out.",
    "OHM_DIRECT_R": "More resistance means more current flows through it.",
    "OHM_FORMULA": "I used V = I / R for this.",
    "PWR_FORMULA": "Power is p = v / i so I divided.",
    "PWR_I2R": "Power is proportional to current so it doubles.",
    "SP_PARALLEL_ADD": "In parallel you just add the resistances together.",
    "SP_PARALLEL_INCREASE": "Adding another bulb adds more resistance so total resistance increases.",
    "CH_CREATED": "Rubbing creates new charge on the rod.",
    "CH_PROTON_MOVE": "Protons move from the silk to the rod when rubbed.",
    "RES_AREA": "A thicker wire has more resistance because there is more material.",
    "RES_LENGTH": "A longer wire has less resistance.",
    "RES_TEMP": "When temperature increases resistance decreases.",
    "CUR_FORMULA": "I multiplied charge by time to get current.",
    "PD_METER": "The voltmeter goes in series with the resistor.",
    "CUR_DIRECTION": "Current flows from negative to positive terminal.",
}

# misconceptions that are 'class-wide' in the seeded class -> the dashboard tells a clear story
CLASS_WIDE = {"SP_PARALLEL_ADD", "OHM_DIRECT_R", "CUR_USED_UP", "PWR_I2R", "SP_PARALLEL_INCREASE"}


def choose_answer(question, mode, rng, p_correct=0.5):
    """Return (selected_option, reasoning). mode: 'correct' | 'misconception' | 'skill'."""
    wrong_opts = [o for o in question["options"] if o != question["answer"]]
    traps = {o: question["traps"].get(o) for o in wrong_opts}
    if mode == "correct" or (mode == "skill" and rng.random() < p_correct):
        return question["answer"], rng.choice(["", "I worked it out step by step.", "I used the formula and checked units."])
    tagged = [o for o in wrong_opts if traps[o]]
    pool = tagged or wrong_opts
    weights = [8 if traps.get(o) in CLASS_WIDE else 1 for o in pool]
    selected = rng.choices(pool, weights=weights)[0]
    mid = traps.get(selected)
    sample = REASONING_SAMPLES.get(mid, "")
    return selected, (sample if (mode == "misconception" or rng.random() < 0.6) else "")


def step(student_id, mode, rng, p_correct=0.5, ts=None, today=None, use_llm=False):
    """One tutoring round. Returns dict(question, why, selected, reasoning, result)."""
    q, why = get_next_question(student_id, rng=rng)
    selected, reasoning = choose_answer(q, mode, rng, p_correct)
    res = process_answer(student_id, q, selected, reasoning, ts=ts, today=today, use_llm=use_llm)
    return {"question": q, "why": why, "selected": selected, "reasoning": reasoning, "result": res}


# concept -> ability offset for the seeded class (class struggles with series/parallel and Ohm's law)
CLASS_OFFSET = {"Series and Parallel Circuits": -0.38, "Ohm's Law": -0.22, "Electric Power": -0.10,
                "Electric Current": -0.04, "Potential Difference": 0.04, "Resistance": 0.0, "Electric Charge": 0.08}


def simulate_student(student_id, ability, n_steps, rng, days=14):
    from diagnostic import get_diagnostic_questions
    now = datetime.now()
    # every real student starts with the diagnostic (one question per concept)
    for q in get_diagnostic_questions(rng):
        p = max(0.05, min(0.95, ability + CLASS_OFFSET.get(q["concept"], 0) + rng.uniform(-0.1, 0.1)))
        selected, _ = choose_answer(q, "skill", rng, p)
        when = now - timedelta(days=days + 0.5)
        process_answer(student_id, q, selected, "", ts=when.strftime("%Y-%m-%d %H:%M:%S"),
                       today=when.date(), use_llm=False, context="diagnostic")
    for k in range(n_steps):
        when = now - timedelta(days=days * (1 - k / n_steps), hours=rng.uniform(0, 5))
        # peek at the concept the tutor will choose to pick the right p_correct
        q, why = get_next_question(student_id, rng=rng)
        p = ability + CLASS_OFFSET.get(q["concept"], 0) - 0.10 * ["easy", "medium", "hard", "advanced"].index(q["difficulty"])
        p = max(0.05, min(0.95, p + rng.uniform(-0.08, 0.08)))
        selected, reasoning = choose_answer(q, "skill", rng, p)
        process_answer(student_id, q, selected, reasoning, ts=when.strftime("%Y-%m-%d %H:%M:%S"),
                       today=when.date(), use_llm=False)
