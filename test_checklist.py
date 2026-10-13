"""Run: python test_checklist.py   (needs no AI, no internet)"""
from checklist import split_clauses, run_checklist, extract_deadlines, format_report, format_deadlines

text = open("sample_contracts/sample_nda.txt", encoding="utf-8").read()
clauses = split_clauses(text)
print("Clauses found:", [(c["number"], c["title"]) for c in clauses])
print()
print(format_report(run_checklist(clauses)))
print()
print(format_deadlines(extract_deadlines(clauses)))
