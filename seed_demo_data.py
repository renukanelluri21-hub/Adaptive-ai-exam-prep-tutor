"""Create a realistic demo class so the teacher dashboard has something to show.

    python seed_demo_data.py            # add demo students (skips if already present)
    python seed_demo_data.py --reset    # wipe tutor.db first
"""
import os
import random
import sys

import database
from database import add_student, create_tables, get_students
from learner_model import initialize_mastery
from simulator import simulate_student

NAMES = [("Aarav", 0.85), ("Diya", 0.78), ("Rohan", 0.62), ("Ananya", 0.88), ("Kabir", 0.45),
         ("Meera", 0.70), ("Arjun", 0.35), ("Ishita", 0.80), ("Vikram", 0.55), ("Sneha", 0.66),
         ("Rahul", 0.40), ("Priya", 0.75)]


def main():
    if "--reset" in sys.argv and os.path.exists(database.DB_NAME):
        os.remove(database.DB_NAME)
    create_tables()
    if any("(demo)" in n for _, n in get_students()):
        print("Demo students already exist (use --reset to rebuild).")
        return
    rng = random.Random(42)
    for name, ability in NAMES:
        sid = add_student(f"{name} (demo)")
        initialize_mastery(sid)
        simulate_student(sid, ability, rng.randint(24, 40), rng)
        print(f"seeded {name}")
    print("Done. Run: streamlit run app.py")


if __name__ == "__main__":
    main()
