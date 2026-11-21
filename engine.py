"""One function the whole app (and the demo simulator) calls whenever a student answers."""
from database import save_attempt
from learner_model import update_student_mastery
from misconception import detect_misconception
from revision_scheduler import schedule_revision
from database import get_mastery


def process_answer(student_id, question, selected, reasoning="", ts=None, today=None,
                   use_llm=True, context="practice"):
    correct = selected == question["answer"]
    det = detect_misconception(question["concept"], reasoning, correct, selected, question, use_llm=use_llm)
    label = det["label"]
    if context == "diagnostic" and det["id"] in ("NO_REASONING", "UNKNOWN"):
        label = "Diagnostic error - needs review"

    old = dict(get_mastery(student_id)).get(question["concept"], 50)
    new = update_student_mastery(student_id, question["concept"], correct, question["difficulty"],
                                 flawed=det["flawed_reasoning"], ts=ts)
    save_attempt(student_id, question["concept"], question["question"], correct,
                 reasoning or ("Diagnostic test response" if context == "diagnostic" else ""),
                 label, question_id=question["id"], difficulty=question["difficulty"],
                 selected=selected, misconception_id=det["id"], ts=ts)
    next_rev = schedule_revision(student_id, question["concept"], new, correct=correct,
                                 flawed=det["flawed_reasoning"], today=today)
    return {"correct": correct, "detection": det, "label": label, "old_mastery": old,
            "new_mastery": new, "delta": round(new - old, 2), "next_revision": next_rev,
            "explanation": question["explanation"], "answer": question["answer"]}
