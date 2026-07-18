from pathlib import Path
import importlib.util
import sys


def load_module():
    script = Path(__file__).parents[1] / "tools" / "update_stats.py"
    spec = importlib.util.spec_from_file_location("update_stats", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_stats_markers_are_stable(tmp_path):
    module = load_module()
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")
    block = f"{module.START_MARKER}\nhello\n{module.END_MARKER}"
    assert module.replace_stats_section(readme, block)
    assert not module.replace_stats_section(readme, block)
    assert readme.read_text(encoding="utf-8").count(module.START_MARKER) == 1


def test_line_count_handles_utf8(tmp_path):
    module = load_module()
    target = tmp_path / "sample.py"
    target.write_text("one\ntwo\nthree\n", encoding="utf-8")
    assert module.line_count(target) == 3
