# Demo Guide (you do NOT need legal knowledge)

You are not presenting law. You are presenting **how an AI agent plus plain Python rules reviews a document safely.** That is a technology story, and you know it better than the judges expect.

## 1. Six legal words in simple language

| Word | Meaning in one line |
|---|---|
| Contract | A written promise between two parties that the law can enforce |
| NDA | Non-Disclosure Agreement: a contract where one side promises to keep the other side's secrets |
| Clause | One numbered section of a contract |
| Termination notice | How many days of warning you must give before ending the contract |
| Liability cap | A limit on how much money one side can be forced to pay if something goes wrong |
| Indemnity | A promise to cover the other side's losses if you cause them |

Also useful: **governing law** is which country's or state's law applies, and **dispute resolution** is how fights are settled (court or arbitration).

## 2. The 3-minute demo script

**0:00 to 0:30, the problem**
"Most people sign contracts they cannot read. Lawyers are expensive. Our agent reads a contract, answers questions using the exact clause, and checks it against a fixed checklist of 9 rules."

**0:30 to 1:15, retrieval query**
Click *Load sample NDA*. Ask: **"What is the termination notice period?"**
Say: "The agent chose the retriever tool, found Clause 4, and quoted it. It shows the clause number so nothing is invented."

**1:15 to 2:15, tool-call query**
Ask: **"Is anything missing from this contract?"**
Then open the *Compliance dashboard* tab and click *Run compliance check*.
Say: "This part is plain Python, not AI. It found no liability cap, no indemnity, a 7-day notice marked FAIL, and red flags like 'sole discretion'. Risk score: 48 out of 100."

**2:15 to 2:45, your design decision**
"We separated deciding from explaining. Python decides PASS, FAIL or MISSING, so the result is the same every time. The AI only picks the tool and explains in simple words. That stops the AI from guessing about legal matters."

**2:45 to 3:00, close**
"It refuses to give legal advice, always shows a disclaimer, and works fully offline with a local model."

(If you finish the MCP bonus, add: "The tools run in a separate FastMCP server and the agent fetches them at runtime.")

## 3. Questions judges may ask

**Why not let the LLM decide?** LLMs can sound confident and be wrong. In legal text that is dangerous, so every status comes from code we can test.

**How do you stop hallucination?** Prompt rules force a tool call first, force clause citations, and say "the contract does not mention it" when nothing is found.

**Why split by clause, not by characters?** A fixed split can cut a clause in half and lose its meaning. Splitting on numbers keeps each clause whole, so the retriever returns complete clauses.

**What if the contract has no numbers?** The splitter falls back to a normal character splitter, so the app never crashes.

**What would you improve next?** More rule packs (employment, rental, service contracts), a Hindi and Gujarati version, and highlighting clauses inside the PDF.

**Can I trust it?** No, and it says so. It is a screening helper, not a lawyer.

## 4. If you forget something

Say less, not more. Show the app, run the two queries, state the one design decision. That already matches what the judges score.
