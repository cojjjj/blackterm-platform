# BLACKTERM v7.2.2 — Project Stats

## Add these files

Copy these folders into the root of your BLACKTERM repository:

```text
tools/
.github/
assets/
tests/
```

The tool does not replace your existing README. It safely appends a statistics block or refreshes the existing block between its markers.

## Run locally

```powershell
python tools\update_stats.py --print
```

This creates or refreshes:

```text
README.md
assets/project-stats.json
assets/project-stats.svg
```

Then commit and push:

```powershell
git add README.md tools .github assets tests
git commit -m "feat: add automatic BLACKTERM project telemetry"
git push origin main
```

## Automatic GitHub updates

The included GitHub Action runs after pushes to `main`. It recounts the repository and commits updated telemetry only when the values changed.

If GitHub blocks the workflow's push, open:

```text
Repository Settings → Actions → General → Workflow permissions
```

Choose **Read and write permissions**, then save.
