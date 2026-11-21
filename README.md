# Adaptive AI Exam Prep Tutor - Class 10 Physics (Electricity)

A tutor that tracks what each student actually understands, finds *why* they go wrong, and decides what to teach next.

## Run it
```bash
pip install -r requirements.txt
streamlit run app.py
```
Teacher PIN: `teacher123` (override with the `TEACHER_PIN` environment variable).
existing `tutor.db` is migrated automatically.

## How each requirement is met
| Requirement | Where | What it does |
|---|---|---|
| Diagnostic test | `diagnostic.py` | One question per concept (7), generated once and kept in `st.session_state` |
| Concept graph | `concept_graph.py` | 7 concepts + prerequisites; coloured by the student's mastery; **drives question selection** |
| Learner model | `learner_model.py` | Mastery updates after every answer; weighted by difficulty, confidence-aware learning rate, partial credit for right answer + flawed reasoning |
| Targeted questions + calibration | `question_generator.py`, `question_bank.py` | 41 curated questions (7 concepts x 4 tiers) + numeric generators for endless variants. Planner picks weakest concept, walks down prerequisites, boosts overdue revisions; difficulty rises after 2 correct, falls after 2 misses |
| Misconception detection from reasoning | `misconception.py` | 3 layers: optional Claude classification of the written reasoning -> regex rules with negation handling -> misconception tagged on the wrong option chosen. Also flags **right answer, wrong reasoning** |
| Spaced repetition | `revision_scheduler.py` | 1/2/3/7/14/30-day intervals by mastery; a miss returns tomorrow; shaky reasoning within 2 days |
| Teacher dashboard | `teacher_dashboard.py` | PIN-gated; class heatmap, auto-generated "biggest gap + what to reteach", % below 50 per concept, students needing support, misconceptions, activity, CSV export |

## 3-minute demo script
1. **Problem (20s):** generic tutors answer questions but don't know what you understand.
2. **Live Demo page (60s):** press *Auto-play 10 rounds*. Point at: mastery bars moving, the concept graph recolouring, the detected misconception and its source, "why this question?", difficulty rising after streaks.
3. **Student flow (40s):** Practice page. Pick a wrong answer and type "the bulb uses up current". Show it flag *Thinks current is 'used up'*, then show the same answer with no reasoning being inferred from the option.
4. **Teacher Dashboard (50s):** heatmap, the yellow "Biggest class gap" box, the reteach suggestion.
5. **Close (10s):** prerequisites drive the planner; every answer updates the model.

## Tests
```bash
pip install pytest && pytest -q
```
`test_backend.py` covers the learner model, planner, misconceptions and DB migration. `test_ui_smoke.py` runs every page with a stubbed Streamlit.

## Known limits (be upfront with judges)
- Content covers one chapter (Class 10 Electricity); the bank is hand-written plus parametric numeric generators.
- Mastery update is a hand-tuned heuristic, not a fitted model (e.g. Bayesian Knowledge Tracing).
- Rule-based misconception detection only recognises catalogued misconceptions; the LLM layer is optional.
- There is no real student login, and the teacher PIN is simple.
