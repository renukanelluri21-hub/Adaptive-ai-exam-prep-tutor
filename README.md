# Adaptive AI Exam Prep Tutor

An intelligent, adaptive learning platform that tracks what each student actually understands, identifies why they make mistakes, and determines what they should learn next.

## Problem

Traditional AI tutors answer questions but often fail to track a student's understanding at the individual concept level.

Our solution creates a personalized learning experience using concept mastery tracking, reasoning-based misconception detection, adaptive question selection, and spaced repetition.

## Key Features

- **Diagnostic Assessment:** Evaluates initial student knowledge across seven Physics concepts.
- **Concept Knowledge Graph:** Represents concepts and their prerequisites, with mastery-based visualizations.
- **Learner Model:** Updates individual concept mastery after every answer.
- **Adaptive Question Generation:** Selects targeted questions based on weaknesses, prerequisites, and difficulty.
- **Misconception Detection:** Analyses student reasoning, identifies known misconceptions, and flags correct answers supported by flawed reasoning.
- **Spaced Repetition:** Schedules personalized revision sessions.
- **Teacher Dashboard:** Displays class-wide learning gaps, mastery heatmaps, misconceptions, and student performance.

## Technology Stack

- Python
- Streamlit
- SQLite
- Pandas
- Plotly
- NetworkX

## Installation and Setup

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd adaptive-ai-exam-prep-tutor
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

## Teacher Access

Default development PIN: `teacher123`.

For deployment, configure a secure `TEACHER_PIN` environment variable and replace the default PIN. Do not use the development PIN in a public deployment.

## How the Requirements Are Implemented

| Requirement | Implementation | Description |
|---|---|---|
| Diagnostic test | `diagnostic.py` | Seven concept-based questions |
| Concept graph | `concept_graph.py` | Prerequisite relationships and mastery visualization |
| Learner model | `learner_model.py` | Confidence-aware mastery updates |
| Adaptive questions | `question_generator.py`, `question_bank.py` | Targeted questions and difficulty calibration |
| Misconception detection | `misconception.py` | Reasoning analysis, rule-based detection and optional LLM classification |
| Spaced repetition | `revision_scheduler.py` | Personalized revision intervals |
| Teacher dashboard | `teacher_dashboard.py` | Class analytics, heatmaps and CSV export |

## Running Tests

Install pytest:

```bash
pip install pytest
```

Run the test suite:

```bash
pytest -q
```


## Current Scope and Limitations

- Currently focuses on Class 10 Physics – Electricity.
- The question bank combines curated questions and parameterized numerical question generators.
- Mastery calculation uses a heuristic rather than a trained knowledge-tracing model.
- Misconception detection recognizes catalogued patterns; optional LLM analysis extends this capability.
- Full student authentication is not yet implemented.
- The teacher PIN is a basic demonstration-level access control, not production-grade security.

## Future Improvements

- Expand to additional subjects and chapters.
- Implement Bayesian Knowledge Tracing.
- Improve misconception detection using more advanced AI models.
- Introduce secure student authentication.
- Improve long-term cloud database persistence.
- Add personalized learning recommendations.

## Project Goal

To move beyond ordinary AI tutoring and build a system that understands student learning patterns, identifies knowledge gaps, and continuously adapts the learning experience.
