"""Question bank: 37 hand-written questions (7 concepts x 4 difficulty tiers) + numeric generators.

Every wrong option can carry a misconception ID ("traps"), so even a bare wrong answer
tells us WHY the student is probably wrong, not just that they are.
"""
import random

DIFFICULTIES = ["easy", "medium", "hard", "advanced"]

_BANK = []


def _q(concept, difficulty, question, options, answer, explanation, traps=None):
    _BANK.append({
        "id": f"q{len(_BANK) + 1:02d}", "concept": concept, "difficulty": difficulty,
        "question": question, "options": options, "answer": answer,
        "explanation": explanation, "traps": traps or {}, "generated": False,
    })


CH, CU, PD = "Electric Charge", "Electric Current", "Potential Difference"
RS, OH, PW, SP = "Resistance", "Ohm's Law", "Electric Power", "Series and Parallel Circuits"

# ---------------- Electric Charge ----------------
_q(CH, "easy", "What is the SI unit of electric charge?",
   ["Ampere", "Coulomb", "Volt", "Ohm"], "Coulomb",
   "The SI unit of charge is the coulomb (C).", {"Ampere": "UNITS", "Volt": "UNITS", "Ohm": "UNITS"})
_q(CH, "easy", "Two positively charged balls are brought close together. What happens?",
   ["They repel each other", "They attract each other", "Nothing happens", "They become neutral"],
   "They repel each other", "Like charges repel; unlike charges attract.",
   {"They attract each other": "CH_LIKE_ATTRACT"})
_q(CH, "medium", "A glass rod rubbed with silk becomes positively charged. What actually happened?",
   ["Electrons moved from the rod to the silk", "Protons moved from the silk to the rod",
    "New positive charge was created in the rod", "The silk lost its neutrons"],
   "Electrons moved from the rod to the silk",
   "Only electrons are free to move. The rod lost electrons (so it is positive) and the silk gained them. Charge is transferred, never created.",
   {"Protons moved from the silk to the rod": "CH_PROTON_MOVE",
    "New positive charge was created in the rod": "CH_CREATED"})
_q(CH, "medium", "A current of 3 A flows through a wire for 4 s. How much charge passes through?",
   ["12 C", "0.75 C", "7 C", "1.33 C"], "12 C",
   "Q = I × t = 3 × 4 = 12 C.", {"0.75 C": "CH_FORMULA", "1.33 C": "CH_FORMULA", "7 C": "GEN_ARITH"})
_q(CH, "hard", "The charge on one electron is 1.6 × 10⁻¹⁹ C. How many electrons make up 1 C of charge?",
   ["6.25 × 10¹⁸", "1.6 × 10⁻¹⁹", "6.25 × 10⁻¹⁸", "1.6 × 10¹⁹"], "6.25 × 10¹⁸",
   "n = Q / e = 1 / (1.6 × 10⁻¹⁹) = 6.25 × 10¹⁸ electrons.",
   {"1.6 × 10⁻¹⁹": "CH_E_CONFUSE", "6.25 × 10⁻¹⁸": "GEN_ARITH", "1.6 × 10¹⁹": "GEN_ARITH"})
_q(CH, "advanced", "An object has 5 × 10¹² extra electrons. What is its net charge? (e = 1.6 × 10⁻¹⁹ C)",
   ["−8 × 10⁻⁷ C", "+8 × 10⁻⁷ C", "−8 × 10⁷ C", "−3.1 × 10³¹ C"], "−8 × 10⁻⁷ C",
   "Q = n × e = 5 × 10¹² × 1.6 × 10⁻¹⁹ = 8 × 10⁻⁷ C. Extra electrons make the charge negative.",
   {"+8 × 10⁻⁷ C": "CH_SIGN", "−8 × 10⁷ C": "GEN_ARITH", "−3.1 × 10³¹ C": "GEN_ARITH"})

# ---------------- Electric Current ----------------
_q(CU, "easy", "What is the formula for electric current?",
   ["I = Q/t", "I = Q × t", "I = t/Q", "I = V × R"], "I = Q/t",
   "Current is the rate of flow of charge: I = Q/t.",
   {"I = Q × t": "CUR_FORMULA", "I = t/Q": "CUR_FORMULA", "I = V × R": "OHM_FORMULA"})
_q(CU, "easy", "What is the SI unit of electric current?",
   ["Volt", "Ohm", "Ampere", "Coulomb"], "Ampere",
   "Current is measured in amperes (1 A = 1 C/s).", {"Volt": "UNITS", "Ohm": "UNITS", "Coulomb": "UNITS"})
_q(CU, "medium", "10 C of charge flows through a wire in 2 s. What is the current?",
   ["5 A", "20 A", "0.2 A", "12 A"], "5 A", "I = Q/t = 10/2 = 5 A.",
   {"20 A": "CUR_FORMULA", "0.2 A": "CUR_FORMULA", "12 A": "GEN_ARITH"})
_q(CU, "hard", "In a simple circuit, an ammeter placed before a bulb reads 0.5 A. What will an identical ammeter placed after the bulb read?",
   ["0.5 A", "Less than 0.5 A, because the bulb uses up current", "0 A", "More than 0.5 A"], "0.5 A",
   "Charge is conserved. The bulb converts energy, not charge, so the current is the same everywhere in a series loop.",
   {"Less than 0.5 A, because the bulb uses up current": "CUR_USED_UP"})
_q(CU, "advanced", "Electrons flow through a wire from point A to point B. What is the direction of conventional current?",
   ["From B to A", "From A to B", "It has no direction", "It depends on the wire's resistance"], "From B to A",
   "Conventional current is defined as the direction positive charge would move, opposite to electron flow.",
   {"From A to B": "CUR_DIRECTION"})

# ---------------- Potential Difference ----------------
_q(PD, "easy", "What is the SI unit of potential difference?",
   ["Coulomb", "Volt", "Ampere", "Joule"], "Volt", "Potential difference is measured in volts (1 V = 1 J/C).",
   {"Coulomb": "UNITS", "Ampere": "UNITS", "Joule": "UNITS"})
_q(PD, "easy", "Potential difference between two points is the…",
   ["work done per unit charge", "charge flowing per unit time", "work done per unit time", "force per unit charge"],
   "work done per unit charge", "V = W/Q.",
   {"charge flowing per unit time": "PD_CONFUSE", "work done per unit time": "PD_CONFUSE"})
_q(PD, "medium", "12 J of work is done to move 3 C of charge between two points. What is the potential difference?",
   ["4 V", "36 V", "0.25 V", "9 V"], "4 V", "V = W/Q = 12/3 = 4 V.",
   {"36 V": "PD_FORMULA", "0.25 V": "PD_FORMULA", "9 V": "GEN_ARITH"})
_q(PD, "hard", "How should a voltmeter be connected to measure the potential difference across a resistor?",
   ["In parallel with the resistor", "In series with the resistor", "In series with the battery", "Position doesn't matter"],
   "In parallel with the resistor",
   "A voltmeter has very high resistance and must be connected across (in parallel with) the component.",
   {"In series with the resistor": "PD_METER", "In series with the battery": "PD_METER"})
_q(PD, "advanced", "A 9 V battery moves 2 C of charge around a circuit. How much energy does the battery supply?",
   ["18 J", "4.5 J", "11 J", "7 J"], "18 J", "W = V × Q = 9 × 2 = 18 J.",
   {"4.5 J": "PD_FORMULA", "11 J": "GEN_ARITH", "7 J": "GEN_ARITH"})

# ---------------- Resistance ----------------
_q(RS, "easy", "What is the SI unit of resistance?",
   ["Volt", "Ampere", "Ohm", "Joule"], "Ohm", "Resistance is measured in ohms (Ω).",
   {"Volt": "UNITS", "Ampere": "UNITS", "Joule": "UNITS"})
_q(RS, "easy", "Two wires have the same material and thickness. One is 1 m long, the other 2 m long. Which has more resistance?",
   ["The 2 m wire", "The 1 m wire", "Both are equal", "It depends on the current"], "The 2 m wire",
   "R = ρL/A, so resistance increases with length.", {"The 1 m wire": "RES_LENGTH"})
_q(RS, "medium", "Compared with a thin wire, a thick wire of the same length and material has…",
   ["lower resistance", "higher resistance", "the same resistance", "zero resistance"], "lower resistance",
   "R = ρL/A. A larger cross-sectional area gives lower resistance, like a wider pipe.",
   {"higher resistance": "RES_AREA"})
_q(RS, "medium", "When the temperature of a metallic conductor increases, its resistance…",
   ["increases", "decreases", "stays the same", "becomes zero"], "increases",
   "Ions vibrate more and collide with electrons more often, so resistance rises.", {"decreases": "RES_TEMP"})
_q(RS, "hard", "A wire of length L and area A has resistance R. A wire of the same material has length 2L and area 2A. What is its resistance?",
   ["R", "2R", "4R", "R/4"], "R",
   "R' = ρ(2L)/(2A) = ρL/A = R. The two doublings cancel.", {"2R": "RES_FACTORS", "4R": "RES_FACTORS", "R/4": "RES_FACTORS"})
_q(RS, "advanced", "A wire of resistance 8 Ω is stretched to twice its length (volume stays constant). What is the new resistance?",
   ["32 Ω", "16 Ω", "8 Ω", "4 Ω"], "32 Ω",
   "Doubling length halves the area, so R' = ρ(2L)/(A/2) = 4R = 32 Ω.",
   {"16 Ω": "RES_STRETCH", "8 Ω": "RES_STRETCH", "4 Ω": "RES_LENGTH"})

# ---------------- Ohm's Law ----------------
_q(OH, "easy", "Which is the correct form of Ohm's Law?",
   ["V = IR", "V = I/R", "R = VI", "I = VR"], "V = IR", "Voltage = current × resistance.",
   {"V = I/R": "OHM_FORMULA", "R = VI": "OHM_FORMULA", "I = VR": "OHM_FORMULA"})
_q(OH, "easy", "If resistance is constant, what happens to current when voltage is doubled?",
   ["It doubles", "It halves", "It stays the same", "It becomes four times"], "It doubles",
   "I = V/R, so current is directly proportional to voltage.", {"It halves": "OHM_DIRECT_R"})
_q(OH, "medium", "A resistor has resistance 5 Ω and carries current 2 A. Find the voltage across it.",
   ["10 V", "2.5 V", "7 V", "0.4 V"], "10 V", "V = IR = 2 × 5 = 10 V.",
   {"2.5 V": "OHM_FORMULA", "0.4 V": "OHM_FORMULA", "7 V": "GEN_ARITH"})
_q(OH, "medium", "If voltage stays constant and resistance increases, what happens to the current?",
   ["Current decreases", "Current increases", "Current stays the same", "Current becomes zero always"],
   "Current decreases", "I = V/R: current is inversely proportional to resistance at constant voltage.",
   {"Current increases": "OHM_DIRECT_R"})
_q(OH, "hard", "A graph of V (y-axis) against I (x-axis) for an ohmic conductor is a straight line through the origin. What does its slope represent?",
   ["Resistance", "Power", "Charge", "Conductance (1/R)"], "Resistance",
   "V = IR, so the slope ΔV/ΔI is R.", {"Conductance (1/R)": "OHM_GRAPH", "Power": "OHM_GRAPH"})
_q(OH, "advanced", "A resistor draws 2 A at 10 V. The voltage is raised to 20 V at constant temperature. What are its new resistance and current?",
   ["R = 5 Ω, I = 4 A", "R = 10 Ω, I = 2 A", "R = 5 Ω, I = 2 A", "R = 2.5 Ω, I = 4 A"], "R = 5 Ω, I = 4 A",
   "Resistance is a property of the conductor, so R = 5 Ω does not change. I = V/R = 20/5 = 4 A.",
   {"R = 10 Ω, I = 2 A": "OHM_R_DEPENDS", "R = 2.5 Ω, I = 4 A": "OHM_R_DEPENDS",
    "R = 5 Ω, I = 2 A": "OHM_DIRECT_R"})

# ---------------- Electric Power ----------------
_q(PW, "easy", "What is the formula for electric power?",
   ["P = VI", "P = V/I", "P = IR", "P = I/V"], "P = VI", "Power = voltage × current.",
   {"P = V/I": "PWR_FORMULA", "P = IR": "PWR_FORMULA", "P = I/V": "PWR_FORMULA"})
_q(PW, "easy", "What is the SI unit of electric power?",
   ["Watt", "Joule", "Kilowatt-hour", "Volt"], "Watt", "Power is measured in watts (1 W = 1 J/s).",
   {"Joule": "PWR_ENERGY", "Kilowatt-hour": "PWR_ENERGY", "Volt": "UNITS"})
_q(PW, "medium", "A device uses 10 V and 2 A. Find its power.",
   ["20 W", "5 W", "12 W", "0.2 W"], "20 W", "P = VI = 10 × 2 = 20 W.",
   {"5 W": "PWR_FORMULA", "0.2 W": "PWR_FORMULA", "12 W": "GEN_ARITH"})
_q(PW, "hard", "A 100 W bulb is used for 5 hours. How much energy does it consume?",
   ["0.5 kWh", "500 kWh", "20 kWh", "5 kWh"], "0.5 kWh",
   "E = P × t = 0.1 kW × 5 h = 0.5 kWh.", {"500 kWh": "PWR_KWH", "20 kWh": "PWR_KWH", "5 kWh": "PWR_KWH"})
_q(PW, "advanced", "The current through a fixed resistor is doubled. What happens to the power it dissipates?",
   ["It becomes 4 times", "It doubles", "It halves", "It stays the same"], "It becomes 4 times",
   "P = I²R, so doubling I multiplies P by 2² = 4.", {"It doubles": "PWR_I2R", "It halves": "PWR_I2R"})

# ---------------- Series and Parallel Circuits ----------------
_q(SP, "easy", "Resistors of 3 Ω and 6 Ω are connected in series. What is the equivalent resistance?",
   ["9 Ω", "2 Ω", "18 Ω", "4.5 Ω"], "9 Ω", "In series, R = R₁ + R₂ = 9 Ω.",
   {"2 Ω": "SP_MIX", "18 Ω": "GEN_ARITH", "4.5 Ω": "SP_MIX"})
_q(SP, "easy", "In a series circuit, the current through each resistor is…",
   ["the same", "different, and shared between them", "zero in the second resistor", "largest in the smallest resistor"],
   "the same", "There is only one path, so the same current flows through every component.",
   {"different, and shared between them": "SP_SERIES_CURRENT"})
_q(SP, "medium", "Resistors of 3 Ω and 6 Ω are connected in parallel. What is the equivalent resistance?",
   ["2 Ω", "9 Ω", "4.5 Ω", "18 Ω"], "2 Ω", "1/R = 1/3 + 1/6 = 1/2, so R = 2 Ω.",
   {"9 Ω": "SP_PARALLEL_ADD", "4.5 Ω": "SP_PARALLEL_ADD", "18 Ω": "SP_PARALLEL_ADD"})
_q(SP, "hard", "A 12 V battery is connected across 4 Ω and 12 Ω resistors in parallel. What current does the battery supply?",
   ["4 A", "0.75 A", "3 A", "1 A"], "4 A",
   "R = (4 × 12)/(4 + 12) = 3 Ω, so I = 12/3 = 4 A. (Or 3 A + 1 A through the two branches.)",
   {"0.75 A": "SP_PARALLEL_ADD", "3 A": "SP_BRANCH_ONLY", "1 A": "SP_BRANCH_ONLY"})
_q(SP, "advanced", "A second identical bulb is connected in parallel with a glowing bulb (ideal battery). What happens to the total resistance of the circuit?",
   ["It decreases", "It increases", "It stays the same", "It doubles"], "It decreases",
   "Adding a parallel branch gives current another path, so total resistance drops.",
   {"It increases": "SP_PARALLEL_INCREASE", "It doubles": "SP_PARALLEL_INCREASE"})
_q(SP, "advanced", "Two identical bulbs are connected in series to a 6 V battery. What is the voltage across each bulb?",
   ["3 V", "6 V", "12 V", "1.5 V"], "3 V",
   "In series the battery voltage is shared: 6 V / 2 = 3 V each.",
   {"6 V": "SP_SERIES_VOLTAGE", "12 V": "GEN_ARITH", "1.5 V": "GEN_ARITH"})

_q(CU, "medium", "How must an ammeter be connected to measure the current through a bulb?",
   ["In series with the bulb", "In parallel with the bulb", "Across the battery only", "Either way gives the same reading"],
   "In series with the bulb",
   "An ammeter has very low resistance and must be in series so the whole current passes through it.",
   {"In parallel with the bulb": "PD_METER", "Either way gives the same reading": "PD_METER"})
_q(PW, "medium", "An 1100 W heater runs on a 220 V supply. What current does it draw?",
   ["5 A", "0.2 A", "880 A", "242000 A"], "5 A", "P = VI, so I = P/V = 1100/220 = 5 A.",
   {"0.2 A": "PWR_FORMULA", "242000 A": "PWR_FORMULA", "880 A": "GEN_ARITH"})


def load_questions():
    return [dict(q, options=list(q["options"])) for q in _BANK]


# ===================== parametric generators =====================
def _numeric(concept, difficulty, question, correct, wrongs, unit, explanation, rng, tag):
    """Build a question from a correct value + [(wrong_value, misconception_id)]."""
    def fmt(v):
        v = round(v, 2)
        s = f"{v:g}"
        return f"{s} {unit}".strip()

    answer = fmt(correct)
    traps, options = {}, [answer]
    for val, mid in wrongs:
        label = fmt(val)
        if label not in options:
            options.append(label)
            traps[label] = mid
    fill = 1
    while len(options) < 4:  # pad with arithmetic slips
        label = fmt(correct + fill * max(1, correct * 0.2))
        if label not in options:
            options.append(label)
            traps[label] = "GEN_ARITH"
        fill += 1
    options = options[:4]
    rng.shuffle(options)
    return {"id": f"gen-{tag}-{rng.randrange(10**6):06d}", "concept": concept, "difficulty": difficulty,
            "question": question, "options": options, "answer": answer, "explanation": explanation,
            "traps": {k: v for k, v in traps.items() if k in options}, "generated": True}


def _gen_charge(d, rng):
    i, t = rng.choice([2, 3, 4, 5, 6]), rng.choice([2, 3, 4, 5, 10])
    return _numeric(CH, d, f"A current of {i} A flows for {t} s. How much charge passes?", i * t,
                    [(i / t, "CH_FORMULA"), (i + t, "GEN_ARITH"), (t / i, "CH_FORMULA")], "C",
                    f"Q = I × t = {i} × {t} = {i * t} C.", rng, "charge")


def _gen_current(d, rng):
    t = rng.choice([2, 4, 5, 10])
    i = rng.choice([2, 3, 4, 5])
    q = i * t
    return _numeric(CU, d, f"{q} C of charge passes a point in {t} s. What is the current?", i,
                    [(q * t, "CUR_FORMULA"), (t / q, "CUR_FORMULA"), (q - t, "GEN_ARITH")], "A",
                    f"I = Q/t = {q}/{t} = {i} A.", rng, "current")


def _gen_pd(d, rng):
    q = rng.choice([2, 3, 4, 5])
    v = rng.choice([3, 6, 9, 12])
    w = v * q
    return _numeric(PD, d, f"{w} J of work moves {q} C of charge between two points. What is the potential difference?",
                    v, [(w * q, "PD_FORMULA"), (q / w, "PD_FORMULA"), (w - q, "GEN_ARITH")], "V",
                    f"V = W/Q = {w}/{q} = {v} V.", rng, "pd")


def _gen_resistance(d, rng):
    r = rng.choice([4, 6, 8, 10])
    k = rng.choice([2, 3])
    return _numeric(RS, d, f"A wire of resistance {r} Ω is cut into {k} equal pieces. What is the resistance of each piece?",
                    r / k, [(r * k, "RES_LENGTH"), (r, "GEN_ARITH"), (r - k, "GEN_ARITH")], "Ω",
                    f"Resistance is proportional to length, so each piece has R/{k} = {r / k:g} Ω.", rng, "res")


def _gen_ohm(d, rng):
    i, r = rng.choice([1, 2, 3, 4, 5]), rng.choice([2, 4, 5, 6, 10])
    v = i * r
    kind = rng.choice(["V", "I", "R"])
    if kind == "V":
        return _numeric(OH, d, f"A {r} Ω resistor carries {i} A. What is the voltage across it?", v,
                        [(r / i, "OHM_FORMULA"), (i / r, "OHM_FORMULA"), (i + r, "GEN_ARITH")], "V",
                        f"V = IR = {i} × {r} = {v} V.", rng, "ohmv")
    if kind == "I":
        return _numeric(OH, d, f"A {v} V supply is connected across a {r} Ω resistor. What current flows?", i,
                        [(v * r, "OHM_FORMULA"), (r / v, "OHM_FORMULA"), (v - r, "GEN_ARITH")], "A",
                        f"I = V/R = {v}/{r} = {i} A.", rng, "ohmi")
    return _numeric(OH, d, f"A potential difference of {v} V drives {i} A through a conductor. What is its resistance?", r,
                    [(v * i, "OHM_FORMULA"), (i / v, "OHM_FORMULA"), (v - i, "GEN_ARITH")], "Ω",
                    f"R = V/I = {v}/{i} = {r} Ω.", rng, "ohmr")


def _gen_power(d, rng):
    v, i = rng.choice([6, 9, 12, 20, 220]), rng.choice([0.5, 1, 2, 3, 5])
    if rng.random() < 0.5:
        return _numeric(PW, d, f"A device runs on {v} V and draws {i:g} A. What is its power?", v * i,
                        [(v / i, "PWR_FORMULA"), (i / v, "PWR_FORMULA"), (v + i, "GEN_ARITH")], "W",
                        f"P = VI = {v} × {i:g} = {v * i:g} W.", rng, "pwr")
    r = rng.choice([2, 4, 5, 10])
    i = rng.choice([1, 2, 3])
    return _numeric(PW, d, f"A {r} Ω heater carries {i} A. What power does it dissipate?", i * i * r,
                    [(i * r, "PWR_I2R"), (i * r * 2, "PWR_I2R"), (i + r, "GEN_ARITH")], "W",
                    f"P = I²R = {i}² × {r} = {i * i * r} W.", rng, "pwri2r")


def _gen_sp(d, rng):
    r1, r2 = rng.choice([(3, 6), (4, 12), (6, 12), (10, 15), (20, 30), (12, 24), (5, 20), (15, 30)])
    par = r1 * r2 / (r1 + r2)
    if rng.random() < 0.5:
        return _numeric(SP, d, f"Resistors of {r1} Ω and {r2} Ω are connected in parallel. What is the equivalent resistance?",
                        par, [(r1 + r2, "SP_PARALLEL_ADD"), ((r1 + r2) / 2, "SP_PARALLEL_ADD"), (r1 * r2, "SP_PARALLEL_ADD")], "Ω",
                        f"1/R = 1/{r1} + 1/{r2}, so R = {par:g} Ω.", rng, "par")
    v = rng.choice([6, 12, 24])
    return _numeric(SP, d, f"{r1} Ω and {r2} Ω resistors in series are connected to a {v} V battery. What current flows?",
                    v / (r1 + r2), [(v / r1, "SP_BRANCH_ONLY"), (v / par, "SP_MIX"), (v / r2, "SP_BRANCH_ONLY")], "A",
                    f"R = {r1} + {r2} = {r1 + r2} Ω, so I = {v}/{r1 + r2} = {v / (r1 + r2):.2f} A.", rng, "ser")


GENERATORS = {
    CH: _gen_charge, CU: _gen_current, PD: _gen_pd, RS: _gen_resistance,
    OH: _gen_ohm, PW: _gen_power, SP: _gen_sp,
}


def generate_question(concept, difficulty, rng=None):
    """Fresh numeric question for a concept, or None if the concept has no generator."""
    gen = GENERATORS.get(concept)
    return gen(difficulty, rng or random.Random()) if gen else None
