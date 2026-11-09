"""Загрузка плагинов из каталога plugins/.

Каждый плагин — .py-файл с атрибутом NAME и функцией register(registry).
Ошибки загрузки/регистрации логируются и не прерывают приложение.
"""

from __future__ import annotations

import importlib.util
import logging
import re
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def _empty_registry():
    return {"exporters": {}, "validators": {}}


class PluginManager:
    def __init__(self, registry=None):
        self.registry = registry if registry is not None else _empty_registry()
        self.registry.setdefault("exporters", {})
        self.registry.setdefault("validators", {})
        self.plugins = []
        self._names = set()
        self._counter = 0

    def load_directory(self, directory):
        directory = Path(directory)
        if not directory.is_dir():
            LOGGER.info("Plugin directory does not exist: %s", directory)
            return self.plugins
        for path in sorted(directory.glob("*.py")):
            if path.name.startswith("_"):
                continue
            self.load_file(path)
        return self.plugins

    def load_file(self, path):
        path = Path(path)
        self._counter += 1
        safe_stem = re.sub(r"\W", "_", path.stem)
        module_name = "_diagram_plugin_{}_{}".format(self._counter, safe_stem)
        info = {
            "name": None,
            "path": str(path),
            "module": module_name,
            "loaded": False,
            "error": None,
        }
        self.plugins.append(info)

        try:
            spec = importlib.util.spec_from_file_location(module_name, str(path))
        except Exception as error:  # pragma: no cover - защитный сценарий
            info["error"] = "spec creation failed: {}".format(error)
            LOGGER.warning("Plugin %s: %s", path, info["error"])
            return info
        if spec is None or spec.loader is None:
            info["error"] = "cannot create import spec"
            LOGGER.warning("Plugin %s: %s", path, info["error"])
            return info

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as error:
            sys.modules.pop(module_name, None)
            info["error"] = "import failed: {}".format(error)
            LOGGER.warning("Plugin %s: %s", path, info["error"])
            return info

        name = getattr(module, "NAME", None)
        if not isinstance(name, str) or not name:
            info["error"] = "NAME must be a non-empty string"
            LOGGER.warning("Plugin %s: %s", path, info["error"])
            sys.modules.pop(module_name, None)
            return info
        info["name"] = name

        if name in self._names:
            info["error"] = "plugin name conflict: {!r} already loaded".format(name)
            LOGGER.warning("Plugin %s: %s", path, info["error"])
            sys.modules.pop(module_name, None)
            return info

        register = getattr(module, "register", None)
        if not callable(register):
            info["error"] = "register(registry) function is missing"
            LOGGER.warning("Plugin %s: %s", path, info["error"])
            sys.modules.pop(module_name, None)
            return info

        snapshot = {key: dict(value) for key, value in self.registry.items()}
        try:
            register(self.registry)
        except Exception as error:
            self.registry.clear()
            self.registry.update(snapshot)
            sys.modules.pop(module_name, None)
            info["error"] = "register() failed: {}".format(error)
            LOGGER.warning("Plugin %s: %s", path, info["error"])
            return info

        self._names.add(name)
        info["loaded"] = True
        LOGGER.info("Loaded plugin %s from %s", name, path)
        return info
