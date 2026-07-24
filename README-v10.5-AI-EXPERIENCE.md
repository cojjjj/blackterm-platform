# BLACKTERM X v10.5 // AI Experience

This update contains only the source files changed after v10.4.

## Added

- Staged AI thinking feedback before answers
- ChatGPT-style typed response animation
- Distinct operator and BLACKTERM AI message cards
- Clickable evidence references that open the case evidence area
- Visual risk, confidence, and investigation-quality meters
- Live AI memory/context counts for scans, evidence, notes, and timeline entries
- Context-aware suggested questions remain supported
- First working AI Case Builder entry point
- AI Case Builder preloads the target into BLACKTERM's existing autonomous investigation wizard
- Existing authorization confirmation and workflow-stage controls are preserved

## Replace these files

Copy the included `blackterm_recon` folder into the root of the existing BLACKTERM project and allow Windows to replace:

- `blackterm_recon/desktop/pages/cases.py`
- `blackterm_recon/desktop/investigation_wizard.py`
- `blackterm_recon/desktop/main_window.py`

## Run

Double-click `RUN_BLACKTERM.bat`.

## AI Case Builder

Open **Cases**, select **AI CASE BUILDER**, enter an authorized domain/IP/hostname, review the prefilled workflow, confirm authorization, and start the investigation.

## Validation

- Python compilation passed for all changed files.
- 11 focused assistant/conversation tests passed.
- The PySide6 desktop UI could not be launched in the Linux validation environment, so final visual validation should be performed on Windows with the existing launcher.
