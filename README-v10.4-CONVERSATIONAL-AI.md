# BLACKTERM X v10.4 — Conversational AI Analyst

This drop-in update turns the case AI Investigation tab into an evidence-grounded conversation workspace.

## Changed files

- `blackterm_recon/assistant_engine.py`
- `blackterm_recon/desktop/pages/cases.py`

## Added test

- `tests/test_ai_conversation.py`

## New behavior

- Persistent operator/analyst conversation cards during the selected case session
- Evidence references attached to every AI response
- Context-aware suggested-question buttons
- Investigation quality score kept separate from target risk
- Historical scan comparison
- Explanations for every observed open port
- Executive brief, risk, evidence, memory, and next-action questions
- Clear warnings that exposure is not proof of exploitability

## Install

Extract this ZIP into the root of your existing BLACKTERM project and allow Windows to replace the two Python files.

Launch normally with:

```powershell
RUN_BLACKTERM.bat
```

## Suggested questions

- `Summarize this case`
- `Why is this risky?`
- `What changed since the previous scan?`
- `What should I do next?`
- `Explain every open port`
- `How complete is this investigation?`
- `Generate an executive brief`
