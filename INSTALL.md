# Install BLACKTERM v6.0

1. Close BLACKTERM.
2. Open this update pack.
3. Drag the `blackterm_recon` and `tests` folders into the root of your main project.
4. Choose **Replace the files in the destination**.
5. Run:

```powershell
python -m pytest
blackterm gui
```

No database deletion or dependency reinstall is required for this update.
