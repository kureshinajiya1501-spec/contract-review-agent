# Contract & Compliance Review Agent

Capabl Agentic AI Hackathon, Track 4: Legal.

An AI agent that reads a contract (PDF or TXT), answers questions about its clauses with the exact clause number, and runs a **rule-based compliance check** that finds missing clauses, risky terms and deadlines.

> **Design decision:** code decides, AI explains. Every PASS / FAIL / MISSING status and the risk score come from plain Python rules, so the same contract always gives the same result. The LLM only chooses which tool to call and explains the result in simple words.

**Disclaimer:** this is an automated screening tool, not a substitute for a licensed lawyer's review.

## Features

- **Clause-aware RAG:** the contract is split on numbered clauses (never mid-clause), embedded with `BAAI/bge-small-en-v1.5` and stored in Chroma.
- **Three tools** for the agent:
  - `retrieve_contract_text`: similarity search, returns clauses labelled with their clause number.
  - `check_contract_compliance`: 9 deterministic rules plus red-flag scan, risk score out of 100.
  - `extract_contract_deadlines`: every date and time period, with its clause and full sentence.
- **Notice period check done by code:** the contract term is never confused with a termination notice period.
- **Hallucination guard:** a risk score can only appear if the compliance tool really ran, and the exact tool output is always shown above or below the AI's explanation.
- **Rule-based dashboard tab** that works without the LLM at all.
- Works fully offline with a local Ollama model.

## The 9 compliance rules

Confidentiality, duration/term, termination and notice period (FAIL under 15 days), governing law, dispute resolution, liability cap, indemnification, return/destruction of information, injunctive relief. Plus red flags such as `sole discretion`, perpetual obligations, automatic renewal, non-compete and unlimited liability.

## Architecture

```
PDF/TXT -> split by clause -> embeddings -> Chroma
                                  |
user question -> agent (LLM + system prompt) -> chooses a tool
                      |-> retrieve_contract_text    (Chroma search)
                      |-> check_contract_compliance (pure Python rules)
                      |-> extract_contract_deadlines (pure Python regex)
                                  |
              exact tool output + AI explanation -> Gradio UI
```

## Setup (Windows, PowerShell)

1. Install Python 3.10+ and [Ollama](https://ollama.com).
2. Pull a model: `ollama pull llama3.2:3b`
3. In the project folder:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python agent.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once.

Optional: copy `.env.example` to `.env` to change the model (`OLLAMA_MODEL=...`).

## Usage

1. Open the local link printed in the terminal (`http://127.0.0.1:7860`).
2. Click **Load sample NDA** or upload your own PDF/TXT contract.
3. Ask: `What is the termination notice period?`, `Is anything missing from this contract?`, `What are the deadlines?`
4. Open the **Compliance dashboard** tab and click **Run compliance check** for the rule-based table.

Test the rules engine without any AI: `python test_checklist.py`

## Project structure

| File | Purpose |
|---|---|
| `agent.py` | Agent creation, answer post-processing, Gradio UI |
| `checklist.py` | Deterministic engine: clause splitter, rules, risk score, deadlines |
| `legal_rag.py` | Load PDF/TXT, split, embed, Chroma, retrieval |
| `legal_tools.py` | The three LangChain tools |
| `system_prompts.py` | Agent instructions |
| `llm.py` | Ollama model connection |
| `test_checklist.py` | AI-free test of the rules engine |
| `sample_contracts/` | Sample NDA with deliberate gaps for demos |

## Limitations

Rules are regex based, so unusual wording can be missed. The local 3B model can phrase explanations imperfectly, which is why the exact rule-based result is always displayed next to it.
