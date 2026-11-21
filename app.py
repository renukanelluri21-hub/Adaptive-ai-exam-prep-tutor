import random
import time
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import simulator
from concept_graph import CONCEPTS, get_prerequisites, show_graph
from database import (create_tables, add_student, get_students, get_mastery, get_revisions,
                      get_attempts_df, get_mastery_history_df, get_or_create_student, reset_student,
                      find_student, delete_student)
from diagnostic import get_diagnostic_questions
from engine import process_answer
from learner_model import (initialize_mastery, get_weakest_concept, get_mastery_level,
                           plan_next_concept)
from misconception import is_specific, llm_available
from question_generator import get_next_question
from teacher_dashboard import show_teacher_dashboard
from ui_helpers import plot, table

PAGES = ["Home", "Diagnostic Test", "Practice Questions", "My Learning Progress",
         "Concept Graph", "Revision Schedule", "Live Demo", "Teacher Dashboard"]
DEMO_STUDENT = "Live Demo Student"

st.set_page_config(page_title="Adaptive AI Tutor", page_icon="🎓", layout="wide")
create_tables()

ss = st.session_state
if "page" not in ss:
    ss["page"] = "Home"


def go_to(page, force=None):
    """Button callback: jump to a page (optionally forcing the practice concept)."""
    ss["page"] = page
    if force:
        ss["force_concept"] = force


# ============================== sidebar ==============================
st.title("🎓 Adaptive AI Exam Prep Tutor")
st.write("Class 10 Physics - Electricity. A tutor that tracks what you actually understand, "
         "finds *why* you go wrong, and decides what to teach next.")

st.sidebar.title("Navigation")
st.sidebar.subheader("Student Registration")
new_name = st.sidebar.text_input("Enter your name")
if st.sidebar.button("Register Student"):
    name = new_name.strip()
    if not name:
        st.sidebar.warning("Please enter your name.")
    elif find_student(name):
        st.sidebar.warning(f"'{name}' is already registered. Pick them from the list below.")
    else:
        add_student(name)
        st.sidebar.success("Student registered!")
        st.rerun()

students = get_students()
if not students:
    st.info("Please register a student to continue.")
    st.stop()

selected_student = st.sidebar.selectbox("Select Student", students, format_func=lambda x: x[1])
student_id, student_name = selected_student
initialize_mastery(student_id)

page = st.sidebar.radio("Choose a section", PAGES, key="page")
st.sidebar.caption("🤖 Claude reasoning analysis: " + ("ON" if llm_available() else "off (rule-based engine active)"))


# ============================== helpers ==============================
def mastery_bar_chart(scores, title=None, height=360):
    rows = [(c, scores.get(c)) for c in CONCEPTS]
    fig = go.Figure(go.Bar(
        x=[s if s is not None else 0 for _, s in rows], y=[c for c, _ in rows], orientation="h",
        marker=dict(color=[s if s is not None else 50 for _, s in rows], colorscale="RdYlGn", cmin=0, cmax=100),
        text=[f"{s:.0f}%" for _, s in rows], textposition="outside"))
    fig.update_layout(title=title, height=height, xaxis=dict(range=[0, 110], title="Mastery %"),
                      yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=40 if title else 10, b=10))
    return fig


def show_detection(res):
    det = res["detection"]
    st.write("**Reasoning analysis**")
    if det["id"] is None:
        st.success("No misconception detected. Your thinking looks sound.")
        if det.get("ai_hint"):
            st.caption(f"🤖 {det['ai_hint']}")
        return
    src = {"ai": "🤖 found by Claude reading your reasoning",
           "reasoning": "🔍 found in your written reasoning",
           "answer": "🎯 inferred from the option you chose"}.get(det["source"], "")
    if det["flawed_reasoning"]:
        st.warning(f"Right answer, but your reasoning shows a misconception: **{det['label']}**  \n{src}")
    elif det["id"] in ("NO_REASONING", "UNKNOWN"):
        st.info(f"**{det['label']}**")
    else:
        st.error(f"**{det['label']}**  \n{src}")
    if det.get("secondary"):
        st.caption(f"Also possible: {det['secondary']}")
    if det.get("ai_hint"):
        st.caption(f"🤖 {det['ai_hint']}")
    st.info(f"📘 {det['recommendation']}")


def show_result(res, q, selected):
    if res["correct"]:
        st.success("Correct answer! ✅")
    else:
        st.error(f"Incorrect. You chose: {selected}")
    st.write("**Correct answer:**", res["answer"])
    st.info(res["explanation"])
    show_detection(res)
    c1, c2 = st.columns(2)
    c1.metric(f"{q['concept']} mastery", f"{res['new_mastery']:.1f}%", f"{res['delta']:+.1f}")
    c2.metric("Next revision", res["next_revision"].strftime("%d %b"))


# ============================== HOME ==============================
if page == "Home":
    st.header(f"Welcome, {student_name}!")
    scores = dict(get_mastery(student_id))
    attempts = get_attempts_df(student_id)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Average mastery", f"{sum(scores.values()) / len(scores):.1f}%")
    c2.metric("Concepts mastered", f"{sum(1 for s in scores.values() if s >= 85)}/{len(scores)}")
    c3.metric("Questions answered", len(attempts))
    c4.metric("Accuracy", f"{attempts['correct'].mean() * 100:.0f}%" if len(attempts) else "-")

    if attempts.empty:
        st.info("👋 Start with the **Diagnostic Test** so the tutor can build your learner profile.")
        st.button("Take the diagnostic →", on_click=go_to, args=("Diagnostic Test",))
    else:
        concept, why = plan_next_concept(student_id)
        st.subheader("🎯 Your next best step")
        st.write(why)
        st.button(f"Practise {concept} →", on_click=go_to, args=("Practice Questions", concept))
        plot(mastery_bar_chart(scores, "Where you stand right now"))

    with st.sidebar.expander("Delete this student"):
        st.caption(f"This permanently removes {student_name} and all their progress.")
        confirm = st.checkbox("Yes, I'm sure", key=f"confirm_del_{student_id}")
    if st.button("Delete student", disabled=not confirm):
        delete_student(student_id)
        st.rerun()
# ============================== DIAGNOSTIC ==============================
elif page == "Diagnostic Test":
    st.header("Initial Diagnostic Test")
    st.write("One question per concept, so the tutor can map your starting point across the whole syllabus.")

    def reset_diag():
        ss["diag"] = {"questions": get_diagnostic_questions(), "results": None,
                      "nonce": ss.get("diag", {}).get("nonce", 0) + 1, "owner": student_id}

    # BUG FIX: the question set is created ONCE and stored. Streamlit re-runs this script on every
    # click, so generating questions inline would swap them out from under the student.
    if "diag" not in ss or ss["diag"]["owner"] != student_id:
        reset_diag()
    diag = ss["diag"]
    dkey = lambda q: f"diag_{student_id}_{diag['nonce']}_{q['id']}"

    if diag["results"] is None:
        with st.form(f"diagnostic_form_{diag['nonce']}"):
            for i, q in enumerate(diag["questions"], 1):
                st.subheader(f"{i}. {q['concept']}")
                st.write(q["question"])
                st.radio("Choose your answer", q["options"], index=None, key=dkey(q),
                         label_visibility="collapsed")
            submitted = st.form_submit_button("Submit Diagnostic Test")
        if submitted:
            answers = {q["id"]: ss.get(dkey(q)) for q in diag["questions"]}
            if any(a is None for a in answers.values()):
                st.warning("Please answer every question before submitting.")
            else:
                diag["results"] = [
                    (q, answers[q["id"]], process_answer(student_id, q, answers[q["id"]], context="diagnostic"))
                    for q in diag["questions"]]
                st.rerun()
    else:
        results = diag["results"]
        n_ok = sum(r["correct"] for _, _, r in results)
        st.success("Diagnostic test completed! Your learner profile has been updated.")
        st.metric("Correct answers", f"{n_ok}/{len(results)}")
        rows = []
        for q, sel, r in results:
            rows.append({"Concept": q["concept"], "Result": "✅" if r["correct"] else "❌",
                         "Mastery": round(r["new_mastery"], 1),
                         "Diagnosis": r["label"] if not r["correct"] else "-"})
        table(pd.DataFrame(rows), hide_index=True)
        plot(mastery_bar_chart(dict(get_mastery(student_id)), "Your starting profile"))
        col1, col2 = st.columns(2)
        col1.button("Start practising →", on_click=go_to, args=("Practice Questions",))
        col2.button("Retake diagnostic", on_click=reset_diag)

# ============================== PRACTICE ==============================
elif page == "Practice Questions":
    st.header("Personalized Practice")

    def new_practice(force=None):
        q, why = get_next_question(student_id, force_concept=force)
        ss["practice"] = {"q": q, "why": why, "result": None, "selected": None,
                          "nonce": ss.get("practice", {}).get("nonce", 0) + 1, "owner": student_id}

    force = ss.pop("force_concept", None)
    # BUG FIX: the current question lives in session_state, so submitting the form grades the SAME
    # question the student saw (before, a new random question was drawn on every rerun).
    if force or "practice" not in ss or ss["practice"]["owner"] != student_id:
        new_practice(force)
    p = ss["practice"]
    q = p["q"]

    top1, top2 = st.columns([3, 1])
    top1.write(f"**Concept:** {q['concept']}  ·  **Difficulty:** {q['difficulty'].title()}")
    if q.get("generated"):
        top2.caption("✨ freshly generated")
    st.caption(f"🎯 Why this question? {p['why']}")
    st.subheader(q["question"])

    if p["result"] is None:
        with st.form(f"practice_form_{p['nonce']}"):
            answer = st.radio("Select your answer", q["options"], index=None, key=f"ans_{p['nonce']}")
            reasoning = st.text_area("Explain why you chose this answer",
                                     placeholder="Write your reasoning here - the tutor reads it to find what's going wrong...",
                                     key=f"why_{p['nonce']}")
            submitted = st.form_submit_button("Submit Answer")
        if submitted:
            if answer is None:
                st.warning("Please select an answer first.")
            else:
                p["selected"] = answer
                p["result"] = process_answer(student_id, q, answer, reasoning)
                st.rerun()
    else:
        show_result(p["result"], q, p["selected"])
        st.button("Next question →", on_click=new_practice, type="primary")

# ============================== PROGRESS ==============================
elif page == "My Learning Progress":
    st.header("My Learning Progress")
    scores = dict(get_mastery(student_id))
    left, right = st.columns(2)
    with left:
        radar = go.Figure(go.Scatterpolar(r=[scores.get(c, 0) for c in CONCEPTS] + [scores.get(CONCEPTS[0], 0)],
                                          theta=CONCEPTS + [CONCEPTS[0]], fill="toself"))
        radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), title="Mastery map", showlegend=False)
        plot(radar)
    with right:
        for concept in CONCEPTS:
            s = scores.get(concept, 50)
            st.write(f"**{concept}** - {s:.1f}% · {get_mastery_level(s)}")
            st.progress(int(max(0, min(100, s))))

    hist = get_mastery_history_df(student_id)
    if len(hist) > len(CONCEPTS):
        st.subheader("Mastery over time")
        hist["ts"] = pd.to_datetime(hist["ts"], errors="coerce")
        hist["step"] = hist.groupby("concept").cumcount()
        plot(px.line(hist, x="step", y="score", color="concept", range_y=[0, 100],
                     labels={"step": "Updates", "score": "Mastery %"}))

    attempts = get_attempts_df(student_id)
    spec = attempts[attempts["misconception"].map(is_specific)] if len(attempts) else attempts
    if len(spec):
        st.subheader("Misconceptions to work on")
        counts = spec.groupby(["misconception", "concept"]).size().reset_index(name="times") \
                     .sort_values("times", ascending=False)
        table(counts, hide_index=True)
    elif not len(attempts):
        st.info("Take the diagnostic test first.")

# ============================== CONCEPT GRAPH ==============================
elif page == "Concept Graph":
    st.header("Physics Concept Graph")
    st.write("Arrows mean *'understand this first'*. Colours show **your** mastery: red = needs work, green = strong.")
    scores = dict(get_mastery(student_id))
    plot(show_graph(scores))
    concept, why = plan_next_concept(student_id)
    st.info(f"🎯 **Next on your path:** {concept}. {why}")
    st.subheader("Prerequisites")
    for c in CONCEPTS:
        pre = get_prerequisites(c)
        if pre:
            st.write(f"**{c}** ← " + ", ".join(f"{p} ({scores.get(p, 50):.0f}%)" for p in pre))

# ============================== REVISION ==============================
elif page == "Revision Schedule":
    st.header("Spaced Repetition Schedule")
    revisions = get_revisions(student_id)
    if revisions:
        today = date.today().isoformat()
        due = [r for r in revisions if r[1] <= today]
        upcoming = [r for r in revisions if r[1] > today]
        st.subheader("Due for revision")
        if due:
            for concept, d in due:
                a, b = st.columns([4, 1])
                a.warning(f"{concept} - due {d}")
                b.button("Practise now", key=f"rev_{concept}", on_click=go_to, args=("Practice Questions", concept))
        else:
            st.success("No revisions due today!")
        st.subheader("Upcoming revisions")
        for concept, d in upcoming:
            st.write(f"📅 {concept} - {d}")
    else:
        st.info("Complete a test or practice question to create a revision schedule.")

# ============================== LIVE DEMO ==============================
elif page == "Live Demo":
    st.header("🎬 Live Demo: watch the learner model update")
    st.write("A fresh simulated student answers questions. Watch **mastery**, the **concept graph**, the "
             "**misconception detector** and the **next-question choice** change after every answer.")

    demo_id = get_or_create_student(DEMO_STUDENT)
    initialize_mastery(demo_id)
    rng = ss.setdefault("live_rng", random.Random(11))
    ss.setdefault("live_log", [])
    use_llm = st.checkbox("Use Claude to read the reasoning", value=False) if llm_available() else False

    b1, b2, b3, b4 = st.columns(4)
    do_ok = b1.button("✅ Answer correctly")
    do_bad = b2.button("❌ Answer with a misconception")
    do_auto = b3.button("▶ Auto-play 10 rounds", type="primary")
    do_reset = b4.button("↺ Reset student")

    left, right = st.columns(2)
    with left:
        metric_ph = st.empty()
        bars_ph = st.empty()
    with right:
        graph_ph = st.empty()
    log_ph = st.empty()

    def render(prev_avg=None):
        scores = dict(get_mastery(demo_id))
        avg = sum(scores.values()) / len(scores)
        ss["live_render"] = ss.get("live_render", 0) + 1
        n = ss["live_render"]
        delta = None if prev_avg is None else f"{avg - prev_avg:+.1f}"
        metric_ph.metric("Average mastery", f"{avg:.1f}%", delta)
        with bars_ph.container():
            plot(mastery_bar_chart(scores, "Mastery by concept", 380), key=f"live_bars_{n}")
        with graph_ph.container():
            plot(show_graph(scores), key=f"live_graph_{n}")
        with log_ph.container():
            st.subheader("What the tutor just did")
            for e in ss["live_log"][:5]:
                r, q = e["result"], e["question"]
                st.markdown(f"**{'✅' if r['correct'] else '❌'} {q['concept']}** · {q['difficulty']} · "
                            f"mastery {r['old_mastery']:.0f}% → **{r['new_mastery']:.0f}%** ({r['delta']:+.1f})")
                st.caption(f"Q: {q['question']}")
                st.caption(f"Student answered: {e['selected']}" + (f' - "{e["reasoning"]}"' if e["reasoning"] else ""))
                if r["detection"]["id"]:
                    st.caption(f"🧠 Detected: {r['detection']['label']} (via {r['detection']['source']})")
                st.caption(f"🎯 {e['why']}")
                st.divider()
        return avg

    def avg_now():
        s = dict(get_mastery(demo_id))
        return sum(s.values()) / len(s)

    if do_reset:
        reset_student(demo_id)
        initialize_mastery(demo_id)
        ss["live_log"] = []
        ss["live_rng"] = rng = random.Random(11)
    prev = avg_now()
    if do_ok or do_bad:
        out = simulator.step(demo_id, "correct" if do_ok else "misconception", rng, use_llm=use_llm)
        ss["live_log"].insert(0, out)
    render(prev if (do_ok or do_bad) else None)
    if do_auto:
        for i in range(10):
            prev = avg_now()
            out = simulator.step(demo_id, "skill", rng, p_correct=0.2 + 0.07 * i, use_llm=use_llm)
            ss["live_log"].insert(0, out)
            render(prev)
            time.sleep(0.9)

# ============================== TEACHER ==============================
elif page == "Teacher Dashboard":
    show_teacher_dashboard()
