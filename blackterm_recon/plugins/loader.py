from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
import importlib.util
import logging

from ..models import ScanContext


@dataclass(slots=True)
class LoadedPlugin:
    name: str
    version: str
    description: str
    path: Path
    module: ModuleType


class PluginManager:
    def __init__(self, directory: str, logger=None):
        self.directory = Path(directory).expanduser()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger("blackterm_recon.plugins")
        self.plugins = []

    def discover(self):
        self.plugins = []
        for path in sorted(self.directory.glob("*.py")):
            if path.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"blackterm_plugin_{path.stem}", path
                )
                if spec is None or spec.loader is None:
                    raise ImportError("unable to load plugin")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if not callable(getattr(module, "run", None)):
                    raise TypeError("plugin must define run(context)")
                meta = getattr(module, "PLUGIN_META", {})
                self.plugins.append(
                    LoadedPlugin(
                        name=str(meta.get("name", path.stem)),
                        version=str(meta.get("version", "0.0")),
                        description=str(meta.get("description", "")),
                        path=path,
                        module=module,
                    )
                )
            except Exception:
                self.logger.exception("Failed to load plugin %s", path)
        return list(self.plugins)

    def execute_all(self, context: ScanContext):
        output = {}
        for plugin in self.plugins:
            try:
                output[plugin.name] = plugin.module.run(context)
            except Exception as exc:
                output[plugin.name] = {"error": str(exc)}
        return output
