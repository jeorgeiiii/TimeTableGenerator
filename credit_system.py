# credit_system.py
# SGSITS B.Tech Choice Based Credit System: per-subject credit categories,
# per-semester / 4-year credit summaries built from curriculum_data.py, and
# the institute's grading rules (grade points, SGPA/CGPA, division).
#
# Sources:
#   - SGSITS Prospectus 2022 (Ordinance 30 "Credit Based Grading System"),
#     sections 4.1 (B.Tech promotion), 4.5 (award of credits & grades,
#     Table 4.2 UG grade bands), 4.9 (Table 4.3 CGPA -> division).
#   - SGSITS EE / EI / E&TC schemes: credit = L + T + P/2 (an L3-P2 subject
#     is "3 1" = 4 credits).
#   - MANIT Bhopal (NIT) 2024 schemes for where SGSITS data was unavailable -
#     see the CURRICULUM_ADDITIONS notes in curriculum_data.py.

import re

from curriculum_data import BRANCHES, build_subject_rows

# Mandatory non-credit audit courses (must be passed, never counted in SGPA).
AUDIT_COURSES = {"environmental science", "constitution of india", "essence of indian knowledge tradition"}

# ============================================================
# CREDIT LIMITS (defaults - admins can change them, stored in the
# credit_policy table). Sources:
#   - SGSITS NEP Scheme 2025 (Information Technology, "Summary of Credits"):
#     20 / 20 / 23 / 22 / 24 / 22 / 16 / 14 for sem I-VIII = 161 credits
#     + 2 (General Proficiency, Professional Practice). Highest semester 24,
#     lowest 14, biggest single item the full-semester internship at 14.
#   - SGSITS scheme ranges across branches: 19-26 credits per regular semester.
#   - AICTE model curriculum: 160 credits is the baseline for a B.Tech degree.
# program_max (170) is this app's own headroom choice above SGSITS IT's 163,
# not a published number - adjust it if your department has an official cap.
# ============================================================
DEFAULT_POLICY = {
    "subject_max_credits": 14,
    "semester_min_credits": 14,
    "semester_max_credits": 26,
    "program_min_credits": 160,
    "program_max_credits": 170,
}
POLICY_LABELS = {
    "subject_max_credits": "Max credits for one subject",
    "semester_min_credits": "Min credits per semester",
    "semester_max_credits": "Max credits per semester",
    "program_min_credits": "Min total credits (4 years)",
    "program_max_credits": "Max total credits (4 years)",
}


def check_policy(policy: dict, semester_totals: dict, subject_credits=None, semesters=None, previous=None):
    """Hard limits that block a save: one subject above subject_max, a
    semester above semester_max, the 4-year total above program_max.
    semesters: only judge these semesters (the ones a change touches), so an
    unrelated semester that is already over doesn't block every edit.
    previous: {semester: total} before the change - a semester or 4-year
    total is only flagged if the change raises it, so lowering credits in an
    over-limit semester is always allowed.
    Returns a list of human-readable violations (empty = OK)."""
    v = []
    if subject_credits is not None:
        if subject_credits < 0:
            v.append("Credits cannot be negative.")
        elif subject_credits > policy["subject_max_credits"]:
            v.append(f"{subject_credits} credits is above the per-subject limit of {policy['subject_max_credits']}.")
    for sem, total in sorted(semester_totals.items()):
        if semesters is not None and sem not in semesters:
            continue
        if total > policy["semester_max_credits"] and (previous is None or total > previous.get(sem, 0)):
            v.append(f"Semester {sem} would have {total} credits (limit {policy['semester_max_credits']}).")
    grand = sum(semester_totals.values())
    if grand > policy["program_max_credits"] and (previous is None or grand > sum(previous.values())):
        v.append(f"4-year total would be {grand} credits (limit {policy['program_max_credits']}).")
    return v


def policy_status(policy: dict, semester_totals: dict):
    """Soft view for dashboards: per-semester and total status vs. every limit
    (minimums only warn - a branch whose curriculum isn't fully loaded yet is
    naturally under them)."""
    sems = {}
    for sem in range(1, 9):
        t = semester_totals.get(sem, 0)
        status = "over" if t > policy["semester_max_credits"] else ("under" if t < policy["semester_min_credits"] else "ok")
        sems[sem] = {"total": t, "status": status}
    grand = sum(semester_totals.values())
    status = "over" if grand > policy["program_max_credits"] else ("under" if grand < policy["program_min_credits"] else "ok")
    return {"semesters": sems, "total": grand, "total_status": status}


# ============================================================
# L-T-P <-> CREDITS
# ============================================================
_LTP = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*$")


def parse_ltp(ltp: str):
    m = _LTP.match(ltp or "")
    if not m:
        raise ValueError("L-T-P must look like 3-1-2 (lecture-tutorial-practical hours per week)")
    return tuple(int(x) for x in m.groups())


def credits_from_ltp(ltp: str) -> int:
    """SGSITS rule: L and T hours count 1 credit each, every 2 P hours count 1."""
    l, t, p = parse_ltp(ltp)
    return l + t + p // 2


# ============================================================
# SGSITS CREDIT PRESETS - used to pre-assign credits to a subject by name.
# Taken from SGSITS's NEP Scheme 2025 (IT, all 8 semesters) and the common
# first-year scheme in the same document. First match wins, so specific
# patterns come before generic ones. (pattern, applies_to_lab, credits, L-T-P)
# applies_to_lab: True = lab rows only, False = theory rows only, None = both.
# ============================================================
SGSITS_PRESETS = [
    (r"constitution of india|environmental science|indian knowledge tradition", None, 0, "2-0-0"),
    (r"co-?curricular", None, 1, "0-0-2"),
    (r"skill lab", None, 2, "0-1-2"),
    (r"major project.*(phase\s*-?\s*(i|1)\b(?!i))", None, 4, "0-0-8"),
    (r"major project", None, 8, "0-0-16"),
    (r"minor project|mini project", None, 4, "0-0-8"),
    (r"industrial training|internship", None, 2, "0-0-4"),
    (r"engineering graphics", True, 2, "0-0-4"),
    (r"engineering graphics", False, 2, "2-0-0"),
    (r"manufacturing practices|engineering workshop", True, 2, "0-0-4"),
    (r"^mathematics\s*-?\s*(i|ii|1|2)\b(?!i)", False, 4, "3-1-0"),
    (r"^mathematics", False, 3, "3-0-0"),
    (r"^physics$|^applied physics$", False, 3, "3-0-0"),
    (r"^chemistry$", False, 3, "3-0-0"),
    (r"fundamentals of (electrical|civil)", False, 3, "2-1-0"),
    (r"programming for problem solving|computer programming", False, 3, "2-1-0"),
    (r"basic electronics", False, 2, "2-0-0"),
    (r"technical english|communication skills", False, 2, "2-0-0"),
    (r"values,? human", False, 2, "2-0-0"),
    (r"economics for engineers", False, 3, "3-0-0"),
    (r"^data structures|design and analysis of algorithms|\(daa\)|discrete structures|"
     r"database management|theory of computation", False, 4, "3-1-0"),
    (r"computer networks|operating systems?|software engineering|compiler design|machine learning|"
     r"cloud computing|information security|object oriented programming|computer organi[sz]ation|"
     r"digital system design|data communication", False, 3, "3-0-0"),
    (r"open elective", False, 4, "3-1-0"),
    (r"elective", False, 3, "3-0-0"),
]


def sgsits_preset(name: str, is_lab: bool, hours_per_week: int = None):
    """Best SGSITS credit value for a subject: a named rule from the official
    scheme if one matches, else the L + T + P/2 rule applied to its weekly
    hours (labs: P/2, theory: 1 per hour), else None when hours are unknown."""
    n = (name or "").strip().lower()
    for pattern, lab_only, credits, ltp in SGSITS_PRESETS:
        if lab_only is not None and lab_only != bool(is_lab):
            continue
        if re.search(pattern, n):
            return {"credits": credits, "ltp": ltp, "source": "SGSITS NEP Scheme 2025"}
    if hours_per_week:
        if is_lab:
            return {"credits": max(1, hours_per_week // 2), "ltp": f"0-0-{hours_per_week}",
                    "source": "SGSITS rule: 2 practical hours = 1 credit"}
        return {"credits": hours_per_week, "ltp": f"{hours_per_week}-0-0",
                "source": "SGSITS rule: 1 lecture hour = 1 credit"}
    return None


_CURRICULUM_CREDITS = None


def curriculum_default(code: str, name: str):
    """The credits curriculum_data.py gives this exact subject (code AND name
    must match), or None for a manually added subject."""
    global _CURRICULUM_CREDITS
    if _CURRICULUM_CREDITS is None:
        _CURRICULUM_CREDITS = {(r[0], r[1].strip().lower()): r[5] for r in build_subject_rows()}
    return _CURRICULUM_CREDITS.get((code, (name or "").strip().lower()))

# Table 4.2 - UG grade bands on absolute marks.
GRADES = [
    # (grade, min_marks, max_marks, grade_point, description)
    ("A+", 91, 100, 10, "Outstanding"),
    ("A", 81, 90, 9, "Excellent"),
    ("B+", 71, 80, 8, "Very Good"),
    ("B", 61, 70, 7, "Good"),
    ("C+", 51, 60, 6, "Average"),
    ("C", 41, 50, 5, "Satisfactory"),
    ("D", 31, 40, 4, "Marginal"),
    ("F", 0, 30, 0, "Fail"),
]
GRADE_POINTS = {g[0]: g[3] for g in GRADES}
GRADE_POINTS["I"] = 0  # Incomplete

# Table 4.3 - CGPA -> division (awarded after the final semester).
DIVISIONS = [
    (7.5, "First Division with Honours"),
    (6.5, "First Division"),
    (5.0, "Second Division"),
]

MIN_CGPA_FOR_DEGREE = 5.0

ASSESSMENT = {
    "theory": {"class_work": 30, "end_semester": 70},
    "practical": {"sessional": 40, "end_semester": 60},
}

# Theory marks breakdown and pass marks, as given by the SGSITS user for this
# app (the 2022 prospectus splits class work differently - quizzes 10,
# attendance 5, mid-term 15 - so this is the department's current rule).
MARKS_SCHEME = {
    "theory_total": 100,
    "end_semester_exam": 70,
    "internal": 30,
    "internal_parts": [
        {"name": "MST (best of MST-1 and MST-2)", "marks": 10},
        {"name": "Attendance", "marks": 10},
        {"name": "Assignment", "marks": 10},
    ],
    "pass_theory": 23,
    "pass_total": 30,
}
PASSING_RULES = [
    "Theory exam (end-semester): 70 marks.",
    "Remaining 30 marks: MST (best of MST-1 and MST-2) 10 + Attendance 10 + Assignment 10.",
    "To pass: at least 23 marks in theory.",
    "And at least 30 marks in total (theory + practical).",
]

RULES = [
    "1 hour/week of Lecture (L) or Tutorial (T) = 1 credit; 2 hours/week of Practical (P) = 1 credit.",
    "Theory and practical parts of a subject are separate subjects for passing (grade D or better in each).",
    "Audit courses (Environmental Science, Constitution of India) must be passed but carry 0 credits.",
    "A minimum CGPA of 5.0 is required for the award of the degree.",
    "Failing (below grade D) more than five subjects in a year blocks admission to the next year.",
    "Sem V and above need the first year fully passed with CGPA >= 5.0; Sem VII and above need years 1-2 passed.",
]

CATEGORY_LABELS = {
    "BSC": "Basic Science",
    "ESC": "Engineering Science",
    "HSMC": "Humanities & Management",
    "PCC": "Professional Core",
    "PEC": "Professional Elective",
    "OEC": "Open Elective",
    "LAB": "Laboratory",
    "PROJ": "Project / Internship",
    "MC": "Mandatory Audit (0 credit)",
}

_BSC = ("mathematics", "physics", "chemistry", "probability", "numerical methods")
_ESC = ("fundamentals of", "engineering graphics", "manufacturing practices", "computer programming",
        "basic electronics", "engineering workshop")
_HSMC = ("english", "communication skills", "economics for engineers", "values, human", "constitution", "production management")
_PROJ = ("project", "internship", "industrial training", "seminar", "viva")


def categorize(name: str, year: int, is_lab: bool, is_elective: bool) -> str:
    n = name.strip().lower()
    if n in AUDIT_COURSES:
        return "MC"
    if any(k in n for k in _PROJ):
        return "PROJ"
    if "open elective" in n:
        return "OEC"
    if is_elective or "elective" in n:
        return "PEC"
    if is_lab or n.endswith(" lab") or " lab " in n:
        return "LAB" if year > 1 else "ESC"
    if any(k in n for k in _BSC):
        return "BSC"
    if any(k in n for k in _HSMC):
        return "HSMC"
    if year == 1 and any(k in n for k in _ESC):
        return "ESC"
    return "PCC"


def credit_scheme(branch: str):
    """Every semester (1-8) of one branch with its subjects, credits and totals."""
    semesters = {}
    for code, name, b, y, sem, credits, hours, is_lab, is_elective in build_subject_rows(branch):
        s = semesters.setdefault(sem, {"semester": sem, "year": y, "subjects": [], "total_credits": 0,
                                       "theory_credits": 0, "lab_credits": 0, "contact_hours": 0})
        category = categorize(name, y, bool(is_lab), bool(is_elective))
        if category == "MC":
            credits = 0
        s["subjects"].append({
            "code": code, "name": name, "credits": credits, "hours_per_week": hours,
            "is_lab": bool(is_lab), "is_elective": bool(is_elective), "category": category,
        })
        s["total_credits"] += credits
        s["contact_hours"] += hours
        s["lab_credits" if is_lab else "theory_credits"] += credits
    ordered = [semesters[k] for k in sorted(semesters)]
    total = sum(s["total_credits"] for s in ordered)
    by_category = {}
    for s in ordered:
        for subj in s["subjects"]:
            by_category[subj["category"]] = by_category.get(subj["category"], 0) + subj["credits"]
    peak = max(ordered, key=lambda s: s["total_credits"]) if ordered else None
    return {
        "branch": branch,
        "semesters": ordered,
        "total_credits": total,
        "credits_by_category": by_category,
        "peak_semester": peak["semester"] if peak else None,
        "peak_credits": peak["total_credits"] if peak else 0,
    }


def branch_overview():
    """Per-branch semester totals, for comparing branches side by side."""
    out = []
    for b in BRANCHES:
        scheme = credit_scheme(b)
        out.append({
            "branch": b,
            "semester_credits": {s["semester"]: s["total_credits"] for s in scheme["semesters"]},
            "total_credits": scheme["total_credits"],
            "peak_semester": scheme["peak_semester"],
        })
    return out


def grade_for_marks(marks: float) -> str:
    for grade, lo, hi, _gp, _desc in GRADES:
        if lo <= marks <= hi:
            return grade
    return "F"


def division_for(cgpa: float) -> str:
    for threshold, label in DIVISIONS:
        if cgpa >= threshold:
            return label
    return "Not eligible for degree (CGPA below 5.0)"


def sgpa(entries):
    """entries: [{"credits": int, "grade": "A+"}] -> (SGPA, credits registered, credits earned).
    SGPA = sum(credits x grade point) / sum(credits). Zero-credit (audit)
    entries are ignored; an F/I still counts in the denominator."""
    weighted, registered, earned = 0, 0, 0
    for e in entries:
        c = int(e.get("credits") or 0)
        if c <= 0:
            continue
        grade = str(e.get("grade", "")).strip().upper()
        if grade not in GRADE_POINTS:
            raise ValueError(f"Unknown grade '{e.get('grade')}'")
        gp = GRADE_POINTS[grade]
        weighted += c * gp
        registered += c
        if gp > 0:
            earned += c
    return (round(weighted / registered, 2) if registered else 0.0), registered, earned


def cgpa(semesters):
    """semesters: [[entries...], ...] -> CGPA weighted by credits across all semesters."""
    weighted, registered = 0, 0
    for entries in semesters:
        value, reg, _earned = sgpa(entries)
        weighted += value * reg
        registered += reg
    return round(weighted / registered, 2) if registered else 0.0
