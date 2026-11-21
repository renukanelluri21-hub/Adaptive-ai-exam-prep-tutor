"""Teacher dashboard: class-wide gaps, who needs help, and which misconceptions to reteach."""
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from concept_graph import CONCEPTS
from database import get_all_mastery_df, get_attempts_df, get_students
from misconception import CATALOG, is_specific
from ui_helpers import plot, table

AT_RISK_AVG = 50       # class-average below this = needs support
GAP_THRESHOLD = 50     # a concept "gap" = mastery below this


def _pin_ok():
    """Simple access control so students can't open the teacher view. Set TEACHER_PIN in the environment."""
    pin = os.environ.get("TEACHER_PIN", "teacher123")
    if st.session_state.get("teacher_ok"):
        return True
    st.info("🔒 Teacher access. Enter the teacher PIN to continue.")
    entered = st.text_input("Teacher PIN", type="password", key="teacher_pin_input")
    if entered:
        if entered == pin:
            st.session_state["teacher_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect PIN.")
    return False


def _load():
    mastery = get_all_mastery_df()
    attempts = get_attempts_df()
    if not attempts.empty:
        assessed = attempts.groupby(["student_id", "concept"]).size().reset_index(name="n_attempts")
        mastery = mastery.merge(assessed, on=["student_id", "concept"], how="left")
    else:
        mastery["n_attempts"] = 0
    mastery["n_attempts"] = mastery["n_attempts"].fillna(0).astype(int)
    # untouched concepts still sit at the default 50: don't let them pollute class statistics
    mastery["assessed"] = mastery["n_attempts"] > 0
    return mastery, attempts


def show_teacher_dashboard():
    st.title("👩‍🏫 Teacher Dashboard")
    if not _pin_ok():
        return

    students = get_students()
    if not students:
        st.info("No students registered yet.")
        return

    mastery, attempts = _load()
    seen = mastery[mastery["assessed"]]
    if seen.empty:
        st.info("No learning data available yet. Students need to take the diagnostic first "
                "(or run `python seed_demo_data.py` for a demo class).")
        return

    attempts = attempts.copy()
    attempts["day"] = pd.to_datetime(attempts["date"], errors="coerce").dt.date
    specific = attempts[attempts["misconception"].map(is_specific)]

    # ---------- class-level numbers ----------
    concept_stats = (seen.groupby("concept")
                     .agg(avg=("score", "mean"), students=("student_id", "nunique"),
                          below=("score", lambda s: (s < GAP_THRESHOLD).mean() * 100))
                     .reindex([c for c in CONCEPTS if c in seen["concept"].unique()])
                     .reset_index())
    student_stats = (seen.groupby(["student_id", "student"])
                     .agg(avg=("score", "mean"), weakest_score=("score", "min"))
                     .reset_index())
    weakest_concept = (seen.sort_values("score").groupby("student_id").first()["concept"]
                       .rename("weakest_concept"))
    student_stats = student_stats.merge(weakest_concept, left_on="student_id", right_index=True)
    acc = attempts.groupby("student_id")["correct"].mean().mul(100).rename("accuracy")
    last = attempts.groupby("student_id")["day"].max().rename("last_active")
    student_stats = student_stats.merge(acc, left_on="student_id", right_index=True, how="left") \
                                 .merge(last, left_on="student_id", right_index=True, how="left")
    if not specific.empty:
        top_m = (specific.groupby(["student_id", "misconception"]).size().reset_index(name="n")
                 .sort_values("n", ascending=False).groupby("student_id").first()["misconception"]
                 .rename("top_misconception"))
        student_stats = student_stats.merge(top_m, left_on="student_id", right_index=True, how="left")
    else:
        student_stats["top_misconception"] = None
    at_risk = student_stats[student_stats["avg"] < AT_RISK_AVG]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Students", len(students))
    c2.metric("Class mastery", f"{seen['score'].mean():.1f}%")
    c3.metric("Class accuracy", f"{attempts['correct'].mean() * 100:.0f}%")
    c4.metric("Students at risk", len(at_risk))
    c5.metric("Questions answered", len(attempts))

    # ---------- the one-line insight a teacher actually needs ----------
    worst = concept_stats.sort_values("avg").iloc[0]
    msg = (f"**Biggest class gap: {worst['concept']}** - class average {worst['avg']:.0f}%, "
           f"{worst['below']:.0f}% of students below {GAP_THRESHOLD}%.")
    in_concept = specific[specific["concept"] == worst["concept"]]
    if not in_concept.empty:
        top_label = in_concept["misconception"].value_counts().index[0]
        n_students = in_concept[in_concept["misconception"] == top_label]["student_id"].nunique()
        rec = next((e["rec"] for e in CATALOG.values() if e["label"] == top_label), "")
        msg += (f"\n\n**Most common misconception there:** {top_label} "
                f"({n_students} students).\n\n💡 *Suggested reteach:* {rec}")
    st.warning(msg, icon="🎯")

    # ---------- heatmap ----------
    st.subheader("Class heatmap: who is struggling with what")
    heat = seen.pivot_table(index="student", columns="concept", values="score")
    heat = heat.reindex(columns=[c for c in CONCEPTS if c in heat.columns])
    heat = heat.loc[heat.mean(axis=1).sort_values().index]   # weakest students on top
    fig = px.imshow(heat, color_continuous_scale="RdYlGn", zmin=0, zmax=100, aspect="auto",
                    labels=dict(color="Mastery %"), text_auto=".0f")
    fig.update_xaxes(side="top", tickangle=-25)
    fig.update_layout(height=max(320, 34 * len(heat) + 120), margin=dict(l=10, r=10, t=90, b=10))
    plot(fig)
    st.caption("Grey cells = concept not attempted yet. Rows sorted weakest to strongest.")

    # ---------- concept-wise ----------
    st.subheader("Concept-wise class performance")
    left, right = st.columns(2)
    bar = px.bar(concept_stats.sort_values("avg"), x="concept", y="avg", color="avg",
                 color_continuous_scale="RdYlGn", range_color=[0, 100], range_y=[0, 100],
                 labels={"avg": "Average mastery %", "concept": ""}, title="Average mastery by concept")
    bar.update_layout(coloraxis_showscale=False, xaxis_tickangle=-25)
    with left:
        plot(bar)
    gap = px.bar(concept_stats.sort_values("below", ascending=False), x="concept", y="below",
                 range_y=[0, 100], labels={"below": f"% of students below {GAP_THRESHOLD}", "concept": ""},
                 title=f"Share of class below {GAP_THRESHOLD}% mastery", color_discrete_sequence=["#d1495b"])
    gap.update_layout(xaxis_tickangle=-25)
    with right:
        plot(gap)

    # ---------- students needing support ----------
    st.subheader("Students requiring support")
    support = student_stats.sort_values("avg")[
        ["student", "avg", "weakest_concept", "accuracy", "top_misconception", "last_active"]]
    support.columns = ["Student", "Avg mastery", "Weakest concept", "Accuracy %", "Top misconception", "Last active"]
    table(support, hide_index=True, column_config={
        "Avg mastery": st.column_config.ProgressColumn("Avg mastery", min_value=0, max_value=100, format="%.0f%%"),
        "Accuracy %": st.column_config.NumberColumn("Accuracy %", format="%.0f"),
    })
    st.download_button("⬇ Download class report (CSV)", support.to_csv(index=False).encode(),
                       "class_report.csv", "text/csv")

    # ---------- misconceptions ----------
    st.subheader("Common misconceptions")
    if specific.empty:
        st.info("No misconceptions recorded yet.")
    else:
        mc = (specific.groupby(["misconception", "concept"])
              .agg(times=("id", "count"), students=("student_id", "nunique")).reset_index()
              .sort_values("times", ascending=False).head(10))
        mfig = px.bar(mc.sort_values("times"), x="times", y="misconception", color="concept",
                      orientation="h", hover_data=["students"],
                      labels={"times": "Times observed", "misconception": ""})
        mfig.update_layout(height=420, legend_title_text="Concept")
        plot(mfig)
        with st.expander("What to reteach (top 5)"):
            for _, row in mc.head(5).iterrows():
                rec = next((e["rec"] for e in CATALOG.values() if e["label"] == row["misconception"]), "")
                st.markdown(f"**{row['misconception']}** · {row['concept']} · "
                            f"{row['students']} students, {row['times']} times  \n> {rec}")

    # ---------- activity ----------
    st.subheader("Class activity")
    daily = attempts.groupby("day").agg(questions=("id", "count"), accuracy=("correct", "mean")).reset_index()
    daily["accuracy"] *= 100
    if len(daily) > 1:
        a1, a2 = st.columns(2)
        with a1:
            plot(px.bar(daily, x="day", y="questions", title="Questions answered per day"))
        with a2:
            plot(px.line(daily, x="day", y="accuracy", markers=True, range_y=[0, 100],
                         title="Class accuracy per day (%)"))

    # ---------- drill-down ----------
    st.subheader("Student drill-down")
    names = student_stats["student"].tolist()
    pick = st.selectbox("Choose a student", names, key="teacher_pick_student")
    sub = mastery[mastery["student"] == pick].set_index("concept").reindex(CONCEPTS).reset_index()
    sub["score"] = sub["score"].where(sub["assessed"])
    dfig = px.bar(sub, x="score", y="concept", orientation="h", range_x=[0, 100], color="score",
                  color_continuous_scale="RdYlGn", range_color=[0, 100], labels={"score": "Mastery %", "concept": ""})
    dfig.update_layout(coloraxis_showscale=False, height=360, yaxis=dict(autorange="reversed"))
    plot(dfig)
    pick_id = int(student_stats.loc[student_stats["student"] == pick, "student_id"].iloc[0])
    their = specific[specific["student_id"] == pick_id]
    if not their.empty:
        st.write("**Misconceptions shown by this student:**")
        st.write(their["misconception"].value_counts().rename("times").to_frame())
