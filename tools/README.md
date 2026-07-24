# Screenshot Framing Tool

This optional tool wraps raw application screenshots in a consistent BLACKTERM presentation frame.

## Setup

```bash
python -m pip install -r tools/requirements.txt
```

Create this folder:

```text
docs/screenshots/raw/
```

Place the eight raw screenshots in that folder using the required names from `CAPTURE-GUIDE.md`.

Run:

```bash
python tools/frame_screenshots.py
```

The finished images are written to:

```text
docs/screenshots/
```

The script does not alter the source images.
