from langchain_core.tools import tool

from checklist import (run_checklist, extract_deadlines, format_report, format_deadlines,
                       notice_period_check)
from legal_rag import STATE, retrieve_clauses


@tool
def retrieve_contract_text(query: str) -> str:
    """
    Finds the clauses of the loaded contract that answer a QUESTION about its
    content, using similarity search.

    Use this for questions like "What is the termination notice period?",
    "Which law governs this agreement?" or "What does the confidentiality
    clause say?". Do NOT use it to judge whether the contract is complete or
    risky (use check_contract_compliance for that).

    Input:
    query (str) - the topic or question, e.g. "termination notice period".

    Returns:
    Up to 3 clauses, each labelled like [Clause 4: Termination] followed by
    its exact text. Always quote the clause number in your answer.
    For notice-period questions it ends with a NOTICE PERIOD CHECK line that
    was computed by code: copy its conclusion exactly.
    """
    text = retrieve_clauses(query)
    if STATE["clauses"] and "notice" in query.lower():
        text += "\n\n" + notice_period_check(STATE["clauses"])
    return text


@tool
def check_contract_compliance(focus: str = "all") -> str:
    """
    Runs a fixed, rule-based checklist (plain Python, no AI guessing) over the
    WHOLE loaded contract.

    Use this when the user asks if the contract is complete, safe, risky,
    what is missing, or asks for a review or risk score.

    Checks 9 rules: confidentiality, duration, termination and notice period,
    governing law, dispute resolution, liability cap, indemnification, return
    of information, injunctive relief. Also scans for red flags such as
    'sole discretion', perpetual obligations and automatic renewal.

    Input:
    focus (str) - always pass "all".

    Returns:
    A risk score out of 100 with its level (LOW / MEDIUM / HIGH), then each
    rule marked PASS, FAIL or MISSING with the clause number, then red flags.
    Report these results exactly as given. Do not change any status.
    """
    if not STATE["clauses"]:
        return "No contract is loaded yet. Ask the user to upload one first."
    return format_report(run_checklist(STATE["clauses"]))


@tool
def extract_contract_deadlines(focus: str = "all") -> str:
    """
    Lists every date and time period (notice periods, payment days, contract
    duration, effective dates) found in the loaded contract, each with its
    clause number.

    Use this when the user asks about deadlines, dates, durations, time limits
    or "when" something must happen.

    Input:
    focus (str) - always pass "all".

    Returns:
    One line per item: clause number, kind (date or period), value, and the
    sentence it came from.
    """
    if not STATE["clauses"]:
        return "No contract is loaded yet. Ask the user to upload one first."
    return format_deadlines(extract_deadlines(STATE["clauses"]))


tools = [retrieve_contract_text, check_contract_compliance, extract_contract_deadlines]
