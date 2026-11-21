"""Spaced repetition: the weaker the concept (or the last answer), the sooner it comes back."""
from datetime import date, timedelta

from database import save_revision


def interval_days(mastery):
    if mastery < 40:
        return 1
    if mastery < 55:
        return 2
    if mastery < 70:
        return 3
    if mastery < 85:
        return 7
    if mastery < 95:
        return 14
    return 30


def schedule_revision(student_id, concept, mastery, correct=True, flawed=False, today=None):
    days = interval_days(mastery)
    if not correct:
        days = 1                      # a miss comes back tomorrow
    elif flawed:
        days = min(days, 2)           # right answer, shaky reasoning: revisit soon
    next_date = (today or date.today()) + timedelta(days=days)
    save_revision(student_id, concept, next_date.isoformat())
    return next_date
