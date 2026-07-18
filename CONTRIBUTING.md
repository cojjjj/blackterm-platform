# Contributing to BLACKTERM

Thanks for your interest in BLACKTERM.

## Before You Start

- Use BLACKTERM only on systems you own or are authorized to test.
- Keep pull requests focused and easy to review.
- Do not submit offensive features intended for unauthorized access, persistence, credential theft, evasion, or destructive activity.
- Never commit API keys, credentials, private scan data, or personal information.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

## Pull Requests

1. Create a focused branch.
2. Add or update tests where appropriate.
3. Run the complete test suite.
4. Explain what changed and why.
5. Include screenshots for visible UI changes.

## Style

- Prefer clear names and small functions.
- Add type hints to new public functions.
- Keep UI work separate from scanning and storage logic.
- Preserve the existing BLACKTERM visual language.
- Avoid unrelated formatting changes.

## Bug Reports

Include:

- Operating system and Python version
- Exact steps to reproduce
- Full traceback or relevant logs
- Expected and actual behavior
- Screenshot when the problem is visual
