import tempfile
import unittest
from pathlib import Path

from src.plugin_loader import PluginManager


GOOD_PLUGIN = '''
NAME = "demo_export"


def exporter(diagram, kind):
    return "demo:{}".format(kind)


def register(registry):
    registry.setdefault("exporters", {})["demo"] = exporter
'''

IMPORT_ERROR_PLUGIN = '''
NAME = "broken"
raise RuntimeError("boom")
'''

MISSING_REGISTER_PLUGIN = '''
NAME = "no_register"
'''

REGISTER_ERROR_PLUGIN = '''
NAME = "register_error"


def register(registry):
    registry.setdefault("exporters", {})["partial"] = lambda diagram, kind: "x"
    raise RuntimeError("register boom")
'''


def conflict_plugin(name):
    return '''
NAME = "%s"


def register(registry):
    registry.setdefault("exporters", {})[NAME] = lambda diagram, kind: "x"
''' % name


class PluginLoaderTest(unittest.TestCase):
    def test_successful_load(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "good.py").write_text(GOOD_PLUGIN, encoding="utf-8")
            manager = PluginManager()
            manager.load_directory(directory)
            self.assertEqual(len(manager.plugins), 1)
            self.assertTrue(manager.plugins[0]["loaded"])
            self.assertIn("demo", manager.registry["exporters"])
            self.assertEqual(manager.registry["exporters"]["demo"](None, "activity"), "demo:activity")

    def test_import_error_is_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "good.py").write_text(GOOD_PLUGIN, encoding="utf-8")
            Path(directory, "broken.py").write_text(IMPORT_ERROR_PLUGIN, encoding="utf-8")
            manager = PluginManager()
            with self.assertLogs("src.plugin_loader", level="WARNING") as logs:
                manager.load_directory(directory)
            self.assertEqual(len(manager.plugins), 2)
            broken = [item for item in manager.plugins if "broken.py" in item["path"]][0]
            self.assertFalse(broken["loaded"])
            self.assertIn("import failed", broken["error"])
            self.assertTrue(any("boom" in line for line in logs.output))
            self.assertIn("demo", manager.registry["exporters"])

    def test_missing_register(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "no_register.py").write_text(
                MISSING_REGISTER_PLUGIN, encoding="utf-8"
            )
            manager = PluginManager()
            manager.load_directory(directory)
            self.assertFalse(manager.plugins[0]["loaded"])
            self.assertIn("register(registry)", manager.plugins[0]["error"])

    def test_register_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "register_error.py").write_text(
                REGISTER_ERROR_PLUGIN, encoding="utf-8"
            )
            manager = PluginManager()
            manager.load_directory(directory)
            self.assertFalse(manager.plugins[0]["loaded"])
            self.assertIn("register() failed", manager.plugins[0]["error"])
            self.assertNotIn("partial", manager.registry["exporters"])

    def test_name_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "a.py").write_text(conflict_plugin("same"), encoding="utf-8")
            Path(directory, "b.py").write_text(conflict_plugin("same"), encoding="utf-8")
            manager = PluginManager()
            manager.load_directory(directory)
            self.assertEqual(len(manager.plugins), 2)
            loaded = [item for item in manager.plugins if item["loaded"]]
            self.assertEqual(len(loaded), 1)
            errors = [item for item in manager.plugins if not item["loaded"]]
            self.assertIn("conflict", errors[0]["error"])

    def test_missing_directory(self):
        manager = PluginManager()
        manager.load_directory("/path/that/does/not/exist")
        self.assertEqual(manager.plugins, [])


if __name__ == "__main__":
    unittest.main()
