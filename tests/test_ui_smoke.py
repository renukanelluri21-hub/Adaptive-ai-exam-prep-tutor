"""UI smoke test with a STUB streamlit/plotly: runs app.py + teacher_dashboard.py against the real
database and backend to catch NameErrors, bad calls, pandas errors and broken flows.
It does not replace one manual look in a real browser (layout/visuals)."""
import os, random, runpy, sys, types
from unittest.mock import MagicMock

import pytest

import database

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


class Rerun(Exception):
    pass


class Ctx:
    proxy = {}          # widget functions shared with the stub module (so col.button(...) behaves like st.button)
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, name):
        if name in Ctx.proxy: return Ctx.proxy[name]
        return lambda *a, **k: Ctx()
    def __iter__(self): return iter(())
    def __call__(self, *a, **k): return Ctx()


class State(dict):
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: raise AttributeError(k)
    def __setattr__(self, k, v): self[k] = v


def make_stub():
    st = types.ModuleType("streamlit")
    st.session_state = State()
    st.cfg = {"buttons": set(), "answer": "first", "reason": ""}
    st.calls = []

    def lab(label, *a, **k): return str(label)
    def pressed(label): return any(b in label for b in st.cfg["buttons"])

    def button(label, *a, **k):
        if pressed(str(label)):
            cb = k.get("on_click")
            if cb:                       # real Streamlit: run callback, then re-run the script
                cb(*(k.get("args") or ()))
                raise Rerun()
            return True
        return False

    def radio(label, options=None, *a, **k):
        key = k.get("key")
        if key == "page": return st.session_state["page"]
        if key in st.session_state: return st.session_state[key]
        if st.cfg["answer"] == "first" and st.cfg["buttons"] and options:   # user picked option 1, then submitted
            if key: st.session_state[key] = options[0]
            return options[0]
        return None

    def selectbox(label, options=None, *a, **k):
        return options[0] if options else None

    def columns(spec, *a, **k):
        return [Ctx() for _ in range(spec if isinstance(spec, int) else len(spec))]

    def rerun(): raise Rerun()

    st.button = button; st.form_submit_button = button
    st.radio = radio; st.selectbox = selectbox; st.columns = columns; st.rerun = rerun
    st.text_input = lambda *a, **k: ""
    st.text_area = lambda *a, **k: st.cfg["reason"]
    st.checkbox = lambda *a, **k: False
    st.stop = lambda: (_ for _ in ()).throw(SystemExit)
    st.plotly_chart = lambda fig, **k: st.calls.append("plotly")
    st.dataframe = lambda df, **k: st.calls.append("table")
    st.sidebar = types.SimpleNamespace(
        title=lambda *a, **k: None, subheader=lambda *a, **k: None, text_input=lambda *a, **k: "",
        button=lambda *a, **k: False, success=lambda *a, **k: None, warning=lambda *a, **k: None,
        selectbox=selectbox, radio=radio, caption=lambda *a, **k: None)
    st.__getattr__ = lambda name: (lambda *a, **k: Ctx())
    st.column_config = Ctx()
    Ctx.proxy = {n: getattr(st, n) for n in ("button", "radio", "selectbox", "text_input", "text_area",
                                             "checkbox", "form_submit_button", "columns", "plotly_chart", "dataframe")}
    return st


@pytest.fixture
def ui(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_NAME", str(tmp_path / "ui.db"))
    st = make_stub()
    monkeypatch.setitem(sys.modules, "streamlit", st)
    for m in ("plotly", "plotly.express", "plotly.graph_objects"):
        monkeypatch.setitem(sys.modules, m, MagicMock())
    for m in ("ui_helpers", "teacher_dashboard"):
        sys.modules.pop(m, None)
    import time; monkeypatch.setattr(time, "sleep", lambda s: None)
    database.create_tables()
    return st


def run(st, page=None, buttons=(), **cfg):
    st.cfg["buttons"] = set(buttons); st.cfg.update(cfg)
    if page: st.session_state["page"] = page
    for _ in range(4):                       # emulate Streamlit's rerun-after-submit
        try:
            runpy.run_path(APP, run_name="__main__")
            return
        except Rerun:
            st.cfg["buttons"] = set()        # buttons are only True for the run they're clicked in


def add_student(name="Asha"):
    from learner_model import initialize_mastery
    sid = database.add_student(name); initialize_mastery(sid); return sid


def test_all_pages_render_for_new_student(ui):
    add_student()
    for page in ["Home", "Diagnostic Test", "Practice Questions", "My Learning Progress",
                 "Concept Graph", "Revision Schedule", "Live Demo"]:
        run(ui, page)


def test_session_state_fix_diagnostic(ui):
    """The question set must NOT change between the render and the submit."""
    sid = add_student()
    run(ui, "Diagnostic Test")
    before = [q["id"] for q in ui.session_state["diag"]["questions"]]
    run(ui, "Diagnostic Test", buttons=["Submit Diagnostic"])
    assert [q["id"] for q in ui.session_state["diag"]["questions"]] == before
    assert ui.session_state["diag"]["results"] is not None
    assert len(database.get_attempts_df(sid)) == 7        # one per concept
    run(ui, "Diagnostic Test")                            # results view
    run(ui, "Diagnostic Test", buttons=["Retake"])


def test_session_state_fix_practice(ui):
    """Submitting must grade the SAME question that was displayed."""
    sid = add_student()
    run(ui, "Practice Questions")
    shown = ui.session_state["practice"]["q"]["question"]
    run(ui, "Practice Questions", buttons=["Submit Answer"], reason="the bulb uses up some current")
    a = database.get_attempts_df(sid)
    assert len(a) == 1 and a.iloc[0]["question"] == shown
    assert ui.session_state["practice"]["result"] is not None
    run(ui, "Practice Questions")                         # result view
    run(ui, "Practice Questions", buttons=["Next question"])
    assert ui.session_state["practice"]["result"] is None


def test_practice_requires_an_answer(ui):
    sid = add_student()
    run(ui, "Practice Questions", buttons=["Submit Answer"], answer=None)
    assert len(database.get_attempts_df(sid)) == 0


def test_revision_practise_now_forces_concept(ui):
    sid = add_student()
    from datetime import date, timedelta
    database.save_revision(sid, "Ohm's Law", (date.today() - timedelta(days=1)).isoformat())
    run(ui, "Revision Schedule", buttons=["Practise now"])
    assert ui.session_state["page"] == "Practice Questions"
    run(ui)
    assert ui.session_state["practice"]["q"]["concept"] == "Ohm's Law"


def test_live_demo_buttons(ui):
    add_student()
    run(ui, "Live Demo", buttons=["Answer correctly"])
    run(ui, "Live Demo", buttons=["Answer with a misconception"])
    run(ui, "Live Demo", buttons=["Auto-play"])
    assert len(ui.session_state["live_log"]) == 12
    run(ui, "Live Demo", buttons=["Reset"])
    assert ui.session_state["live_log"] == []


def test_teacher_dashboard_with_seeded_class(ui):
    import seed_demo_data as sd
    sd.NAMES = sd.NAMES[:5]
    sd.main.__globals__["sys"].argv = ["x"]
    sd.main()
    ui.session_state["teacher_ok"] = True
    run(ui, "Teacher Dashboard")
    assert "plotly" in ui.calls and "table" in ui.calls


def test_teacher_dashboard_gated_and_empty(ui):
    add_student()
    run(ui, "Teacher Dashboard")                          # PIN gate, no crash
    ui.session_state["teacher_ok"] = True
    run(ui, "Teacher Dashboard")                          # no attempts yet
