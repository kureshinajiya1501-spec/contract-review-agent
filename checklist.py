"""
Deterministic contract engine.

NO AI and NO external libraries in this file. Every result comes from
plain Python rules (regex + arithmetic), so the same contract always
gives the same answer. The LLM only decides WHEN to call this and
explains the result in simple words.
"""
import re

# ----------------------------------------------------------------------
# 1. CLAUSE SPLITTER  (split on numbered clauses: "1. Title ...", "2. ...")
# ----------------------------------------------------------------------
CLAUSE_START = re.compile(
    r"(?m)^[ \t]*(?:(?:Section|Article|Clause)[ \t]+)?(\d{1,2})[\.\):]?[ \t]+(?=[A-Z])"
)


def split_clauses(text: str):
    """Return a list of {number, title, text}. Empty list if no numbering found."""
    text = text.replace("\r\n", "\n")
    starts, expected = [], 1
    for m in CLAUSE_START.finditer(text):
        # accept only 1, 2, 3 ... in order, so stray numbers are ignored
        if int(m.group(1)) == expected:
            starts.append((expected, m.start()))
            expected += 1
    if len(starts) < 2:
        return []

    clauses = []
    preamble = text[: starts[0][1]].strip()
    if preamble:
        clauses.append({"number": 0, "title": "Preamble", "text": preamble})

    for i, (num, pos) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        body = text[pos:end].strip()
        no_prefix = CLAUSE_START.sub("", body, count=1).strip()
        title = re.split(r"[.:\n]", no_prefix, maxsplit=1)[0].strip()[:60]
        clauses.append({"number": num, "title": title, "text": body})
    return clauses


# ----------------------------------------------------------------------
# 2. NOTICE PERIOD HELPER
# ----------------------------------------------------------------------
_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
          "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fourteen": 14,
          "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45,
          "sixty": 60, "ninety": 90}
_UNIT = r"(?:calendar |business |working )?(?:day|week|month|year)s?\b"
_WORD_RE = re.compile(
    r"\b(" + "|".join(sorted(_WORDS, key=len, reverse=True)) + r")\b(?:\s*\(\s*\d{1,3}\s*\))?(?=\s*" + _UNIT + ")",
    re.I)
_PAREN_RE = re.compile(r"\(\s*(\d{1,3})\s*\)(?=\s*" + _UNIT + ")", re.I)


def normalize_numbers(text: str) -> str:
    """Turn 'thirty (30) days' and '(30) days' and 'seven days' into '30 days' / '7 days'."""
    text = _WORD_RE.sub(lambda m: str(_WORDS[m.group(1).lower()]), text)
    return _PAREN_RE.sub(r"\1", text)


_UNIT_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}
_NOTICE_1 = re.compile(
    r"(\d{1,3})\s*(?:\(\d{1,3}\)\s*)?(?:calendar |business |working )?(day|week|month)s?['’]?\s*"
    r"(?:prior\s+|advance\s+)?(?:written\s+)?notice",
    re.I,
)
_NOTICE_2 = re.compile(
    r"notice[^.]{0,80}?(\d{1,3})\s*(?:\(\d{1,3}\)\s*)?(day|week|month)s?", re.I
)


def extract_notice_days(text: str):
    """Return notice period in days, or None if no notice period is written."""
    text = normalize_numbers(text)
    m = _NOTICE_1.search(text) or _NOTICE_2.search(text)
    if not m:
        return None
    return int(m.group(1)) * _UNIT_DAYS[m.group(2).lower()]


# ----------------------------------------------------------------------
# 3. COMPLIANCE RULES  (weights add up to 100)
# ----------------------------------------------------------------------
RULES = [
    {"id": "confidentiality", "name": "Confidentiality obligation", "weight": 15,
     "hint": r"obligation|non-?disclosure|confidentiality",
     "patterns": [r"confidential", r"non-?disclosure"]},
    {"id": "term", "name": "Duration / term of agreement", "weight": 10,
     "hint": r"\bterm\b|duration|validity",
     "patterns": [r"remains? in (full )?(force|effect)", r"remains? valid", r"valid and binding",
                  r"period of (?:\w+\s*)?\(?\d+\)?\s*(?:day|week|month|year)", r"\bterm of\b",
                  r"effective date"]},
    {"id": "termination", "name": "Termination and notice period", "weight": 15,
     "patterns": [r"terminat"]},
    {"id": "governing_law", "name": "Governing law", "weight": 10,
     "hint": r"governing|applicable law",
     "patterns": [r"governed by", r"governing law", r"laws of"]},
    {"id": "dispute", "name": "Dispute resolution", "weight": 10,
     "hint": r"dispute|arbitration|jurisdiction|governing",
     "patterns": [r"arbitrat", r"mediation", r"jurisdiction", r"courts? (of|at|in)"]},
    {"id": "liability", "name": "Limitation of liability (cap)", "weight": 15,
     "patterns": [r"limitation of liability",
                  r"liabilit\w*.{0,80}(shall not exceed|limited to|capped)",
                  r"in no event.{0,100}liab"]},
    {"id": "indemnity", "name": "Indemnification", "weight": 10,
     "patterns": [r"indemnif", r"hold harmless"]},
    {"id": "return", "name": "Return or destruction of information", "weight": 10,
     "patterns": [r"return(ed)?\b.{0,80}\bdestr", r"destroy", r"destruction"]},
    {"id": "remedies", "name": "Remedies / injunctive relief", "weight": 5,
     "patterns": [r"injunct", r"equitable relief", r"specific performance"]},
]

# (regex, explanation, penalty points). Total flag penalty is capped at 20.
RED_FLAGS = [
    (r"sole discretion", "One-sided power: 'sole discretion'", 5),
    (r"perpetual|in perpetuity", "Perpetual obligation with no end date", 5),
    (r"unlimited liability|without (?:any )?limit(?!ation)\b", "Unlimited liability", 8),
    (r"irrevocabl", "Irrevocable commitment", 4),
    (r"automatic(ally)? renew", "Automatic renewal", 4),
    (r"non-?compete", "Non-compete restriction", 5),
    (r"waives?\s+(?:any|all|its|their|the)\b[^.]{0,40}\b(?:right|claim|defen[cs]e)s?", "Waiver of rights", 3),
]

MIN_SAFE_NOTICE_DAYS = 15


def _snippet(text: str, m: re.Match, width: int = 70) -> str:
    a, b = max(0, m.start() - width), min(len(text), m.end() + width)
    chunk = text[a:b]
    cut_left = a > 0 and not text[a - 1].isspace()
    cut_right = b < len(text) and not text[b].isspace()
    if cut_left:
        chunk = re.sub(r"^\S+\s+", "", chunk, count=1)
    if cut_right:
        chunk = re.sub(r"\s+\S+$", "", chunk, count=1)
    chunk = " ".join(chunk.split())
    return ("..." if a > 0 else "") + chunk + ("..." if b < len(text) else "")


def _sentence(text: str, m: re.Match, cap: int = 340) -> str:
    """The whole sentence around a match (falls back to a window if too long)."""
    start = max(text.rfind(". ", 0, m.start()), text.rfind("; ", 0, m.start()))
    start = 0 if start == -1 else start + 2
    end = text.find(". ", m.end())
    end = len(text) if end == -1 else end + 1
    sent = text[start:end].strip()
    return sent if len(sent) <= cap else _snippet(text, m, cap // 2)


def _find(patterns, clauses):
    """First (clause, match). Patterns are tried strongest first, across all
    numbered clauses; the preamble (clause 0) is only a last resort."""
    numbered = [c for c in clauses if c["number"] != 0]
    preamble = [c for c in clauses if c["number"] == 0]
    for group in (numbered, preamble):
        for p in patterns:
            for c in group:
                m = re.search(p, c["text"], re.I | re.S)
                if m:
                    return c, m
    return None, None


def run_checklist(clauses):
    """Check every rule. Returns dict with results, flags, score, level."""
    results, penalty = [], 0.0

    for rule in RULES:
        status, note, clause, evidence = "MISSING", "Not found in this contract", None, ""

        if rule["id"] == "termination":
            # prefer clauses titled 'Termination', else any clause mentioning it
            titled = [c for c in clauses if "terminat" in c["title"].lower()]
            cands = titled or [c for c in clauses if "terminat" in c["text"].lower()]
            if cands:
                with_notice = [c for c in cands if extract_notice_days(c["text"]) is not None]
                clause = (with_notice or cands)[0]
                days = extract_notice_days(clause["text"])
                evidence = " ".join(clause["text"].split())[:160]
                if days is None and not titled:
                    status = "MISSING"
                    note = "No termination clause or notice period (only a passing mention)"
                elif days is None:
                    status, note = "FAIL", "Termination exists but NO notice period is written"
                elif days < MIN_SAFE_NOTICE_DAYS:
                    status = "FAIL"
                    note = f"Notice period is only {days} days (under {MIN_SAFE_NOTICE_DAYS} is unusually short)"
                else:
                    status, note = "PASS", f"Notice period: {days} days"
        else:
            clause, m = None, None
            if rule.get("hint"):
                titled_cl = [c for c in clauses if re.search(rule["hint"], c["title"], re.I)]
                clause, m = _find(rule["patterns"], titled_cl)
            if not clause:
                clause, m = _find(rule["patterns"], clauses)
            if clause:
                status, note = "PASS", "Clause found"
                evidence = _snippet(clause["text"], m)

        if status == "MISSING":
            penalty += rule["weight"]
        elif status == "FAIL":
            penalty += rule["weight"] * 0.5

        results.append({
            "rule": rule["name"], "status": status, "note": note,
            "clause": (f"Clause {clause['number']}" if clause else "-"),
            "evidence": evidence,
        })

    # red flags
    flags, flag_points = [], 0
    for pattern, label, pts in RED_FLAGS:
        for c in clauses:
            m = re.search(pattern, c["text"], re.I)
            if m:
                flags.append({"flag": label, "clause": f"Clause {c['number']}",
                              "evidence": _snippet(c["text"], m, 50)})
                flag_points += pts
                break
    penalty += min(flag_points, 20)

    score = int(min(100, round(penalty)))
    level = "LOW" if score < 25 else "MEDIUM" if score < 55 else "HIGH"
    return {"results": results, "flags": flags, "score": score, "level": level}


# ----------------------------------------------------------------------
# 4. DEADLINE / DATE EXTRACTOR
# ----------------------------------------------------------------------
_MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
_DATE = re.compile(
    rf"\b(?:\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTHS},?\s+\d{{4}}|{_MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", re.I)
_DURATION = re.compile(
    r"\b(\d{1,3})\s*(?:\(\d{1,3}\)\s*)?((?:business |calendar |working )?(?:day|week|month|year)s?)\b", re.I)


def extract_deadlines(clauses):
    """Find dates and time periods (notice, payment, term) with clause number, title and sentence."""
    found = []
    for c in clauses:
        text = " ".join(normalize_numbers(c["text"]).split())
        for m in _DATE.finditer(text):
            found.append({"clause": c["number"], "title": c["title"], "kind": "date",
                          "value": m.group(0), "context": _sentence(text, m)})
        for m in _DURATION.finditer(text):
            found.append({"clause": c["number"], "title": c["title"], "kind": "period",
                          "value": f"{m.group(1)} {m.group(2)}", "context": _sentence(text, m)})
    return found


# ----------------------------------------------------------------------
# 5. FORMATTERS (used by the tool output and the UI table)
# ----------------------------------------------------------------------
EMOJI = {"PASS": "PASS", "FAIL": "FAIL", "MISSING": "MISSING"}


def format_report(report) -> str:
    lines = [f"RISK SCORE: {report['score']}/100 ({report['level']} RISK)", "", "CHECKLIST:"]
    for r in report["results"]:
        lines.append(f"- {r['rule']}: {r['status']} ({r['clause']}) | {r['note']}")
    if report["flags"]:
        lines += ["", "RED FLAGS:"]
        for f in report["flags"]:
            lines.append(f"- {f['flag']} in {f['clause']}: \"{f['evidence']}\"")
    return "\n".join(lines)


def format_deadlines(items) -> str:
    if not items:
        return "No dates or time periods found in this contract."
    return "\n".join(
        f"- Clause {d['clause']} ({d['title']}) | {d['kind']}: {d['value']}\n    Sentence: \"{d['context']}\""
        for d in items
    )


def report_rows(report):
    """Rows for the Gradio table."""
    return [[r["rule"], r["status"], r["clause"], r["note"]] for r in report["results"]]


def notice_period_check(clauses) -> str:
    """Code-based answer to: what is the termination notice period?"""
    hits = []
    for c in clauses:
        days = extract_notice_days(c["text"])
        if days is not None and "terminat" in c["text"].lower():
            hits.append(f"Clause {c['number']}: {days} days")
    if hits:
        return "NOTICE PERIOD CHECK (done by code): " + "; ".join(hits)
    return ("NOTICE PERIOD CHECK (done by code): NO termination notice period (a number of days of "
            "warning before ending the contract) is written anywhere in this contract. "
            "The contract duration (term) is NOT a notice period.")
