# BLACKTERM Platform v8.6 — Stability Foundation

This clean release consolidates rendering, animations, startup behavior, and
tests around the architecture that BLACKTERM currently uses.

## Before installing

Close BLACKTERM and delete these stale tests if they still exist:

```text
tests/test_v84_living_interface.py
tests/test_v841_animation_stability.py
tests/test_v85_premium_polish.py
tests/test_v851_render_engine_stability.py
```

## Install

Extract the ZIP and drag `blackterm_recon` and `tests` into:

```text
C:\Users\tyler\Desktop\BLACKTERM-RECON-DESKTOP-ALPHA
```

Choose **Replace the files in the destination**.

## Test

```powershell
pytest -q
```

## Run

```powershell
python -m blackterm_recon gui
```

Expected title:

```text
BLACKTERM Intelligence Platform v8.6 // Stability Foundation
```
