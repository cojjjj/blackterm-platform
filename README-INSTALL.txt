BLACKTERM RECON — Core Intelligence Engine

Replace the matching project files with the files in this update while preserving
this folder structure.

Changed files:
  blackterm_recon/intelligence/registry.py       (new)
  blackterm_recon/intelligence/models.py
  blackterm_recon/intelligence/modules.py
  blackterm_recon/intelligence/engine.py
  blackterm_recon/intelligence/__init__.py
  blackterm_recon/models.py
  blackterm_recon/database.py
  blackterm_recon/engine.py
  tests/test_core_intelligence_engine.py         (new)

Then run from the project root:
  .\.venv\Scripts\Activate.ps1
  python -m pip install -e .
  pytest -q tests/test_core_intelligence_engine.py tests/test_v80_intelligence_engine.py tests/test_database.py
  python -m blackterm_recon gui

The database migrates automatically to schema version 9 and adds an
intelligence_json column. Existing scans remain readable.

The automatic scan integration runs only the passive scan-context normalizer.
It does not add new network requests. DNS, WHOIS, TLS, HTTP, and technology
collection remain available through the Live Intelligence workflow for targets
you own or are authorized to assess.
