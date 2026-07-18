# Installation

Close BLACKTERM and copy the `blackterm_recon` and `tests` folders into the root of the existing project. Choose **Replace the files in the destination**.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
blackterm gui
```

The default behavior is **Ask after every scan**. Change it under **Settings → After autonomous scan**.
