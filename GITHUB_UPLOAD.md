# Upload This Kit to GitHub

Place every file and folder in this pack into the root of your local BLACKTERM project.

Your project root should then contain:

```text
README.md
ROADMAP.md
CHANGELOG.md
CONTRIBUTING.md
SECURITY.md
docs/
screenshots/
blackterm_recon/
tests/
pyproject.toml
```

Then run:

```powershell
git init
git branch -M main
git remote add origin https://github.com/cojjjj/blackterm-platform.git
git add .
git commit -m "release: publish BLACKTERM Platform v6.0 preview"
git push -u origin main
```

If `origin` already exists:

```powershell
git remote set-url origin https://github.com/cojjjj/blackterm-platform.git
git add .
git commit -m "release: publish BLACKTERM Platform v6.0 preview"
git push -u origin main
```

Because the GitHub repository already contains an initial commit, Git may ask you to pull first. Use:

```powershell
git pull origin main --allow-unrelated-histories
```

Resolve any duplicate `.gitignore` or `LICENSE` file by keeping the repository versions, then commit and push again.
