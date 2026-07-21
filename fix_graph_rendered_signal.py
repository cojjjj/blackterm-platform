from __future__ import annotations

from pathlib import Path
import re
import sys


def patch_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Could not find: {path}")

    source = path.read_text(encoding="utf-8")
    original = source

    # Ensure Signal is imported from PySide6.QtCore.
    qtcore_match = re.search(r"from PySide6\.QtCore import ([^\n]+)", source)
    if not qtcore_match:
        raise RuntimeError("Could not find the PySide6.QtCore import line.")

    imported = [part.strip() for part in qtcore_match.group(1).split(",")]
    if "Signal" not in imported:
        imported.append("Signal")
        replacement = "from PySide6.QtCore import " + ", ".join(imported)
        source = source[:qtcore_match.start()] + replacement + source[qtcore_match.end():]

    # Add the signal expected by pages/attack_surface.py.
    class_pattern = r"(class AttackSurfaceGraph\(QGraphicsView\):\s*\n)"
    class_match = re.search(class_pattern, source)
    if not class_match:
        raise RuntimeError("Could not find class AttackSurfaceGraph(QGraphicsView).")

    class_start = class_match.end()
    class_preview = source[class_start:class_start + 500]
    if not re.search(r"^\s+graphRendered\s*=\s*Signal\(", class_preview, re.MULTILINE):
        node_signal = re.search(
            r"(^\s+nodeActivated\s*=\s*Signal\([^\n]*\)\s*$)",
            source[class_start:],
            re.MULTILINE,
        )
        if node_signal:
            absolute_end = class_start + node_signal.end()
            source = (
                source[:absolute_end]
                + "\n    graphRendered = Signal(int, int)"
                + source[absolute_end:]
            )
        else:
            source = (
                source[:class_start]
                + "    nodeActivated = Signal(object)\n"
                + "    graphRendered = Signal(int, int)\n"
                + source[class_start:]
            )

    # Emit after a graph render when the method contains node and edge collections.
    if "self.graphRendered.emit(" not in source:
        render_match = re.search(
            r"(def _render_model\(self,\s*animate:\s*bool\).*?)(?=\n    def |\Z)",
            source,
            re.DOTALL,
        )
        if render_match:
            block = render_match.group(1)
            insertion_patterns = [
                r"(\n\s*self\._scene\.setSceneRect\([^\n]+\))",
                r"(\n\s*QTimer\.singleShot\(0,\s*self\.fit_graph\))",
            ]
            patched_block = block
            inserted = False
            for pattern in insertion_patterns:
                matches = list(re.finditer(pattern, patched_block))
                if matches:
                    point = matches[-1].end()
                    indent_match = re.search(r"\n(\s*)[^\n]*$", patched_block[:point])
                    indent = indent_match.group(1) if indent_match else "        "
                    patched_block = (
                        patched_block[:point]
                        + f"\n{indent}self.graphRendered.emit(len(self._nodes), len(self._edges))"
                        + patched_block[point:]
                    )
                    inserted = True
                    break

            if inserted:
                source = (
                    source[:render_match.start()]
                    + patched_block
                    + source[render_match.end():]
                )

    if source == original:
        print("No changes needed. graphRendered is already present.")
        return

    backup = path.with_suffix(path.suffix + ".before_graph_signal_fix")
    backup.write_text(original, encoding="utf-8")
    path.write_text(source, encoding="utf-8")

    print(f"Patched: {path}")
    print(f"Backup:  {backup}")
    print("The graphRendered signal is now available.")


def main() -> int:
    project_root = Path.cwd()
    target = project_root / "blackterm_recon" / "desktop" / "attack_surface_graph.py"

    try:
        patch_file(target)
    except Exception as exc:
        print(f"Patch failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
