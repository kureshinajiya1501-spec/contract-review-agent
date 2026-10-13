import os
import re

import gradio
from langchain.agents import create_agent

from llm import create_llm
from legal_tools import tools
from legal_rag import load_contract, STATE
from checklist import run_checklist, report_rows
from system_prompts import SYSTEM_PROMPT_LEGAL

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(HERE, "sample_contracts", "sample_nda.txt")

DISCLAIMER = (
    "**Disclaimer:** This tool gives an automated review for learning and "
    "screening only. It is **not a substitute for a licensed lawyer's review.**"
)

contract_agent = create_agent(
    model=create_llm(),
    tools=tools,
    system_prompt=SYSTEM_PROMPT_LEGAL,
)


def clean(text: str) -> str:
    """Remove <think> blocks that some models add."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def ask(question: str) -> str:
    if not STATE["clauses"]:
        return "Please upload a contract (or click 'Load sample NDA') first."
    if not question.strip():
        return "Please type a question about the contract."
    try:
        response = contract_agent.invoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        answer = clean(response["messages"][-1].content)
        # remove the model's own disclaimer line, we add one fixed line at the very end
        answer = re.sub(r"(?im)^\s*_?Note:\s*This is an automated review.*$", "", answer).strip()
        called = {
            getattr(m, "name", None): str(m.content)
            for m in response["messages"] if getattr(m, "name", None)
        }

        # Guard: a risk score may only appear if the compliance tool really ran.
        if "check_contract_compliance" not in called:
            answer = "\n".join(
                line for line in answer.splitlines()
                if not re.search(r"risk score|red flags?", line, re.I)
            ).strip()

        # Attach the EXACT tool outputs. Rule-based results go ABOVE the AI text.
        top, bottom = [], []
        if "check_contract_compliance" in called:
            top.append("**Exact rule-based result:**\n```\n" + called["check_contract_compliance"] + "\n```")
        if "extract_contract_deadlines" in called:
            top.append("**Exact dates and deadlines found:**\n```\n" + called["extract_contract_deadlines"] + "\n```")
        if "retrieve_contract_text" in called:
            bottom.append("**Clauses the agent read:**\n```\n" + called["retrieve_contract_text"] + "\n```")

        parts = []
        if top:
            parts.append("\n\n".join(top))
            parts.append("**Explanation:**\n" + answer)
        else:
            parts.append(answer)
        if bottom:
            parts.append("---\n" + "\n\n".join(bottom))
        return "\n\n".join(parts) + "\n\n_Note: This is an automated review, not legal advice. Please consult a licensed lawyer._"
    except Exception as e:  # fail gracefully, never crash the demo
        return f"Sorry, the agent hit an error: {e}\nTry again, or check that Ollama is running."


def on_upload(file):
    if file is None:
        return "Please choose a PDF or TXT contract."
    path = file if isinstance(file, str) else file.name
    try:
        return load_contract(path)
    except Exception as e:
        return f"Could not load this file: {e}"


def on_sample():
    try:
        return load_contract(SAMPLE_PATH)
    except Exception as e:
        return f"Could not load the sample: {e}"


def on_check():
    """Deterministic dashboard. Does NOT use the LLM at all."""
    if not STATE["clauses"]:
        return "Load a contract first.", [], ""
    report = run_checklist(STATE["clauses"])
    summary = f"## Risk score: {report['score']}/100 ({report['level']} risk)"
    flags = "\n".join(
        f"- **{f['flag']}** in {f['clause']}: _{f['evidence']}_" for f in report["flags"]
    ) or "No red flags found."
    return summary, report_rows(report), "### Red flags\n" + flags


def deploy_agent():
    with gradio.Blocks(title="Contract & Compliance Review Agent") as iface:
        gradio.Markdown("# Contract & Compliance Review Agent")
        gradio.Markdown(
            "Upload a contract. Ask questions about its clauses, or run a rule-based "
            "compliance check that finds missing clauses and risky terms."
        )
        gradio.Markdown(DISCLAIMER)

        with gradio.Row():
            file = gradio.File(label="Contract (PDF or TXT)", type="filepath")
            with gradio.Column():
                load_btn = gradio.Button("Load uploaded contract", variant="primary")
                sample_btn = gradio.Button("Load sample NDA")
                status = gradio.Textbox(label="Status", interactive=False)

        with gradio.Tab("Ask the agent"):
            question = gradio.Textbox(
                label="Your question",
                placeholder="What is the termination notice period?  |  Is anything missing?  |  What are the deadlines?",
            )
            ask_btn = gradio.Button("Ask", variant="primary")
            answer = gradio.Markdown()

        with gradio.Tab("Compliance dashboard (rule-based)"):
            check_btn = gradio.Button("Run compliance check", variant="primary")
            score_md = gradio.Markdown()
            table = gradio.Dataframe(
                headers=["Rule", "Status", "Where", "Note"],
                datatype="str", interactive=False, wrap=True,
            )
            flags_md = gradio.Markdown()

        load_btn.click(on_upload, inputs=file, outputs=status)
        sample_btn.click(on_sample, outputs=status)
        ask_btn.click(ask, inputs=question, outputs=answer)
        question.submit(ask, inputs=question, outputs=answer)
        check_btn.click(on_check, outputs=[score_md, table, flags_md])

    iface.launch()


if __name__ == "__main__":
    deploy_agent()
