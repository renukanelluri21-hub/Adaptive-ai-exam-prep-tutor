"""Misconception detection from the student's REASONING, not only their final answer.

Three layers, strongest first:
  1. (optional) LLM classification of the written reasoning  - set ANTHROPIC_API_KEY
  2. rule-based analysis of the reasoning text (regex, with negation handling)
  3. the misconception tagged on the wrong option the student picked ("distractor tag")

It also catches RIGHT answer + WRONG reasoning (a lucky guess or a flawed mental model).
"""
import json
import os
import re

# id -> label, recommendation, concept ("any" or a concept name),
#       patterns (searched in lower-cased reasoning), unless (veto regex), requires (must also match)
CATALOG = {
    "UNITS": dict(label="Mixes up SI units of electrical quantities", concept="any",
                  rec="Make a one-line table of quantity -> symbol -> unit (C, A, V, Ω, W, J) and quiz yourself."),
    "GEN_ARITH": dict(label="Right idea, calculation slip", concept="any",
                      rec="Write each step with units and re-check the arithmetic before choosing."),
    "CH_LIKE_ATTRACT": dict(label="Thinks like charges attract", concept="Electric Charge",
                            rec="Remember: like charges repel, unlike charges attract. Try the balloon/rod examples.",
                            patterns=[r"(same|like|similar) charges? attract", r"opposite charges? repel"]),
    "CH_PROTON_MOVE": dict(label="Thinks protons move during charging", concept="Electric Charge",
                           rec="Protons are locked in the nucleus. Only electrons transfer when objects are rubbed.",
                           patterns=[r"protons? (move|moved|transfer\w*|flow\w*|jump\w*)"]),
    "CH_CREATED": dict(label="Thinks charge is created by friction", concept="Electric Charge",
                       rec="Charge is conserved: friction only transfers electrons from one object to another.",
                       patterns=[r"charges? (is |was |gets? )?(created|produced|generated)",
                                 r"(creates?|produces?|makes?) (new |extra )?charges?"]),
    "CH_FORMULA": dict(label="Rearranges Q = It incorrectly", concept="Electric Charge",
                       rec="Q = I × t. Check with units: A × s = C.", patterns=[r"q\s*=\s*i\s*/\s*t", r"q\s*=\s*t\s*/\s*i"]),
    "CH_E_CONFUSE": dict(label="Confuses the charge of one electron with the number of electrons", concept="Electric Charge",
                         rec="Number of electrons n = Q / e. e = 1.6 × 10⁻¹⁹ C is the charge of ONE electron."),
    "CH_SIGN": dict(label="Gets the sign of charge wrong (extra electrons = negative)", concept="Electric Charge",
                    rec="Electrons are negative: extra electrons -> negative charge, missing electrons -> positive.",
                    patterns=[r"(extra|excess|more|gain\w*) electrons?.{0,30}positive"]),
    "CUR_FORMULA": dict(label="Uses the wrong formula for current (I = Q/t)", concept="any",
                        rec="Current is charge per unit time: I = Q/t. Check with units: C/s = A.",
                        patterns=[r"i\s*=\s*q\s*[*x×]\s*t", r"i\s*=\s*t\s*/\s*q",
                                  r"multipl\w+ (the )?charge (by|and|with) (the )?time"]),
    "CUR_USED_UP": dict(label="Thinks current is 'used up' by components", concept="any",
                        rec="Charge is conserved. Components transfer energy, not charge, so the same current returns to the battery.",
                        patterns=[r"(used up|use up|uses up|consum\w+|gets? (used|lost|reduced)|loses? (the )?current|current (is )?(lost|finished)|less current (after|at the end))"]),
    "CUR_DIRECTION": dict(label="Confuses conventional current with electron flow", concept="Electric Current",
                          rec="Conventional current: + to −. Electrons actually drift − to +, the opposite way.",
                          patterns=[r"current (flows?|moves?|goes) from (the )?(negative|-|−) (terminal )?to (the )?(positive|\+)"]),
    "PD_CONFUSE": dict(label="Confuses potential difference with current or power", concept="Potential Difference",
                       rec="Potential difference = work per unit CHARGE (V = W/Q). It is not a flow and not a rate.",
                       patterns=[r"voltage (flows?|moves?|travels?)", r"flow of (voltage|potential difference)"]),
    "PD_FORMULA": dict(label="Uses the wrong formula for potential difference/energy (V = W/Q)", concept="any",
                       rec="V = W/Q, so W = V × Q. Check units: J/C = V.",
                       patterns=[r"v\s*=\s*q\s*/\s*w", r"v\s*=\s*w\s*[*x×]\s*q"]),
    "PD_METER": dict(label="Connects ammeter/voltmeter the wrong way", concept="any",
                     rec="Ammeter in SERIES (low resistance). Voltmeter in PARALLEL (high resistance).",
                     patterns=[r"voltmeter.{0,25}series", r"ammeter.{0,25}parallel"]),
    "RES_LENGTH": dict(label="Thinks resistance falls as length increases", concept="any",
                       rec="R = ρL/A: longer wire -> more collisions -> more resistance.",
                       patterns=[r"(longer|more length).{0,30}(less|lower|smaller) resistance",
                                 r"(shorter).{0,30}(more|higher|greater) resistance"]),
    "RES_AREA": dict(label="Thinks a thicker wire has more resistance", concept="Resistance",
                     rec="R = ρL/A: a wider wire gives charges more room, so LOWER resistance (like a wide pipe).",
                     patterns=[r"(thicker|wider|bigger area|larger area).{0,30}(more|higher|greater) resistance",
                               r"thinner.{0,30}(less|lower) resistance"]),
    "RES_TEMP": dict(label="Thinks heating lowers a metal's resistance", concept="Resistance",
                     rec="In metals, hotter -> ions vibrate more -> more collisions -> HIGHER resistance.",
                     patterns=[r"(temperature|heat)\w*\s+(goes |is )?(increas|rais|rise)\w*.{0,25}resistance\s+(decreas|drops|falls|reduc)\w*",
                               r"resistance.{0,15}(decreas|fall|drop)\w*.{0,30}(temperature|heat)\w*\s+(increas|rise|go)"]),
    "RES_FACTORS": dict(label="Looks at only length OR only area when comparing resistance", concept="Resistance",
                        rec="Use R = ρL/A and substitute BOTH changes before comparing.",
                        patterns=[r"only (the )?(length|area|thickness) (matters|affects|changes)"]),
    "RES_STRETCH": dict(label="Forgets that stretching a wire also thins it", concept="Resistance",
                        rec="Volume stays constant: double the length -> half the area -> R becomes 4×.",
                        patterns=[r"(area|thickness|cross.section\w*).{0,25}(stays|remains|same|unchanged|does not change|doesn't change)"]),
    "OHM_FORMULA": dict(label="Uses the wrong form of Ohm's Law", concept="any",
                        rec="Ohm's Law: V = IR, so I = V/R and R = V/I. Use the V-I-R triangle.",
                        patterns=[r"v\s*=\s*i\s*/\s*r", r"r\s*=\s*v\s*[*x×]\s*i", r"i\s*=\s*v\s*[*x×]\s*r", r"v\s*=\s*r\s*/\s*i"]),
    "OHM_DIRECT_R": dict(label="Thinks current increases with resistance (confuses direct & inverse proportion)", concept="any",
                         rec="At constant voltage, MORE resistance means LESS current (I = V/R).",
                         patterns=[r"current.{0,25}(increase|rise|go up)s?.{0,40}resistance (increase|rise|goes up)",
                                   r"(more|higher) resistance.{0,20}(more|higher|greater) current",
                                   r"current is directly proportional to resistance",
                                   r"resistance is directly proportional to current"]),
    "OHM_GRAPH": dict(label="Misreads the V–I graph", concept="Ohm's Law",
                      rec="For V on the y-axis, slope = ΔV/ΔI = R. Straight line through the origin = ohmic."),
    "OHM_R_DEPENDS": dict(label="Thinks resistance changes when voltage or current changes", concept="Ohm's Law",
                          rec="Resistance depends on the conductor (material, length, area, temperature), not on V or I.",
                          patterns=[r"resistance (changes|increases|decreases|doubles|depends).{0,25}(voltage|current)",
                                    r"resistance depends on (the )?(voltage|current)"]),
    "PWR_FORMULA": dict(label="Uses the wrong formula for power (P = VI)", concept="any",
                        rec="P = VI. Check units: V × A = W. Also P = I²R = V²/R.",
                        patterns=[r"p\s*=\s*v\s*/\s*i", r"p\s*=\s*i\s*/\s*v"]),
    "PWR_ENERGY": dict(label="Confuses power with energy", concept="Electric Power",
                       rec="Power = energy per second (W = J/s). Energy = power × time (J or kWh).",
                       patterns=[r"energy and power are (the )?same", r"(power|watt)s? (is|are|means) (the same as )?(energy|joules?)"]),
    "PWR_KWH": dict(label="Mishandles watt -> kilowatt-hour conversion", concept="Electric Power",
                    rec="Convert W to kW (÷1000) first, then multiply by hours: E(kWh) = P(kW) × t(h)."),
    "PWR_I2R": dict(label="Thinks power is proportional to current (instead of current²)", concept="Electric Power",
                    rec="P = I²R: double the current -> 4× the power; triple -> 9×.",
                    patterns=[r"proportional to (the )?current(?! ?(\^2|²|squared|square))", r"power (also )?(doubles|is doubled)"]),
    "SP_MIX": dict(label="Mixes up the series and parallel resistance rules", concept="Series and Parallel Circuits",
                   rec="Series: R = R₁ + R₂. Parallel: 1/R = 1/R₁ + 1/R₂ (always LESS than the smallest branch)."),
    "SP_SERIES_CURRENT": dict(label="Thinks current splits up in a series circuit", concept="Series and Parallel Circuits",
                              rec="Series = one path = the same current everywhere. Current only splits at a parallel junction.",
                              patterns=[r"current (is )?(divid|split|shar)\w*.{0,25}series", r"series.{0,30}current.{0,15}(divid|split|shar)\w*"]),
    "SP_PARALLEL_ADD": dict(label="Adds resistances directly (or averages them) in parallel", concept="Series and Parallel Circuits",
                            rec="In parallel use 1/R = 1/R₁ + 1/R₂, or R = R₁R₂/(R₁+R₂). The result is smaller than either resistor.",
                            patterns=[r"(add|adds|added|adding|sum|total)\b.{0,25}parallel", r"parallel.{0,30}(add|adding|sum)"],
                            unless=r"reciprocal|1\s*/\s*r|inverse|1/"),
    "SP_BRANCH_ONLY": dict(label="Considers only one branch of a parallel circuit", concept="Series and Parallel Circuits",
                           rec="The battery supplies the SUM of all branch currents (or use the equivalent resistance)."),
    "SP_PARALLEL_INCREASE": dict(label="Thinks adding a parallel path increases resistance", concept="Series and Parallel Circuits",
                                 rec="Each parallel path gives charge another route, so total resistance DECREASES.",
                                 patterns=[r"(more|extra|adding|another).{0,20}(bulb|resistor|branch|path).{0,30}(increase|more|higher)\w*.{0,15}resistance"]),
    "SP_SERIES_VOLTAGE": dict(label="Thinks every series component gets the full battery voltage", concept="Series and Parallel Circuits",
                              rec="In series the voltage is SHARED (V = V₁ + V₂). In parallel each branch gets the full voltage.",
                              patterns=[r"(each|every) (bulb|resistor|component).{0,25}(gets?|has|receives) (the )?(full|same|whole) voltage"],
                              requires=r"series"),
}

NO_MISCONCEPTION = "No misconception detected"
NO_REASONING = "Reasoning not provided - needs review"
UNKNOWN = "Incorrect response - misconception needs further investigation"

_NEGATION = re.compile(r"\b(not|never|no|isn't|doesn't|don't|won't|cannot|can't|wouldn't)\b|n't")


def _regex_match(concept, text):
    """Return the first catalog id whose reasoning pattern matches (and isn't negated)."""
    if not text:
        return None
    for mid, entry in CATALOG.items():
        if entry["concept"] not in ("any", concept):
            continue
        if entry.get("requires") and not re.search(entry["requires"], text):
            continue
        if entry.get("unless") and re.search(entry["unless"], text):
            continue
        for pat in entry.get("patterns", []):
            for m in re.finditer(pat, text):
                window = text[max(0, m.start() - 20): m.end()]
                if not _NEGATION.search(window):
                    return mid
    return None


# ---------------- optional LLM layer ----------------
def llm_available():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except Exception:
        return False


def llm_classify(concept, question, selected, correct_answer, reasoning):
    """Ask Claude which known misconception (if any) the written reasoning shows.
    Returns {"id": <catalog id or 'NONE'>, "hint": <one sentence>} or None on any failure."""
    if not llm_available():
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(timeout=10.0)
        options = [f"{k}: {v['label']}" for k, v in CATALOG.items() if v["concept"] in ("any", concept)]
        prompt = (
            "You are a physics teacher diagnosing a Class 10 student's reasoning.\n"
            f"Concept: {concept}\nQuestion: {question}\nStudent chose: {selected}\n"
            f"Correct answer: {correct_answer}\nStudent's reasoning: \"{reasoning}\"\n\n"
            "Known misconceptions:\n" + "\n".join(options) + "\n\n"
            'Reply with ONLY JSON: {"id": "<one id above or NONE>", "hint": "<one friendly sentence of targeted advice>"}. '
            "Use NONE if the reasoning is sound. Judge the reasoning, not just the final answer."
        )
        msg = client.messages.create(model=os.environ.get("TUTOR_LLM_MODEL", "claude-haiku-5-5"),
                                     max_tokens=200, messages=[{"role": "user", "content": prompt}])
        data = json.loads(re.search(r"\{.*\}", msg.content[0].text, re.S).group(0))
        mid = str(data.get("id", "NONE")).strip()
        if mid != "NONE" and mid not in CATALOG:
            return None
        return {"id": mid, "hint": str(data.get("hint", ""))[:300]}
    except Exception:
        return None


# ---------------- public API ----------------
def _result(mid, source, flawed=False, hint=None, secondary=None):
    if mid is None:
        return {"id": None, "label": NO_MISCONCEPTION, "source": "none",
                "recommendation": "Great! Try a harder question.", "flawed_reasoning": False,
                "ai_hint": hint, "secondary": None}
    e = CATALOG[mid]
    return {"id": mid, "label": e["label"], "source": source, "recommendation": e["rec"],
            "flawed_reasoning": flawed, "ai_hint": hint,
            "secondary": CATALOG[secondary]["label"] if secondary in CATALOG else None}


def detect_misconception(concept, reasoning, correct, selected=None, question=None, use_llm=True):
    """Return a dict: id, label, source ('ai'|'reasoning'|'answer'|'none'|'unknown'),
    recommendation, flawed_reasoning (right answer, wrong thinking), ai_hint, secondary."""
    text = (reasoning or "").lower().strip()
    tag = (question or {}).get("traps", {}).get(selected) if not correct else None
    rule_id = _regex_match(concept, text)

    # Layer 1: LLM (only when there is real reasoning to read)
    if use_llm and len(text) >= 12:
        ai = llm_classify(concept, (question or {}).get("question", ""), selected,
                          (question or {}).get("answer", ""), reasoning)
        if ai:
            if ai["id"] != "NONE":
                return _result(ai["id"], "ai", flawed=bool(correct), hint=ai["hint"], secondary=tag)
            if correct:
                return _result(None, "none", hint=ai["hint"])

    if correct:  # Layer 2 only: right answer - is the thinking sound?
        if rule_id:
            return _result(rule_id, "reasoning", flawed=True)
        return _result(None, "none")

    if rule_id:  # reasoning is the strongest evidence
        return _result(rule_id, "reasoning", secondary=tag if tag != rule_id else None)
    if tag:      # Layer 3: the wrong option reveals the likely misconception
        return _result(tag, "answer")
    if not text:
        return {"id": "NO_REASONING", "label": NO_REASONING, "source": "unknown",
                "recommendation": "Next time, explain your reasoning - it lets the tutor find what went wrong.",
                "flawed_reasoning": False, "ai_hint": None, "secondary": None}
    return {"id": "UNKNOWN", "label": UNKNOWN, "source": "unknown",
            "recommendation": "Review the concept and answer another practice question.",
            "flawed_reasoning": False, "ai_hint": None, "secondary": None}


def is_specific(label):
    """True for real, named misconceptions (used by the teacher dashboard)."""
    return (label not in (NO_MISCONCEPTION, NO_REASONING, UNKNOWN, CATALOG["GEN_ARITH"]["label"])
            and "Diagnostic" not in label)


def get_recommendation(misconception):
    """Backward-compatible helper: accepts a result dict or a label string."""
    if isinstance(misconception, dict):
        return misconception["recommendation"]
    for e in CATALOG.values():
        if e["label"] == misconception:
            return e["rec"]
    return "Review the concept and answer another practice question."
