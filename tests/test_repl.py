import tempfile
import unittest
from pathlib import Path

from src.repl import CommandError, REPL, tokenize_command

ACTIVITY = '''{
  "activity": [
    {"step": "Start", "next": "End"},
    {"step": "End"}
  ]
}'''


class CommandTokenizerTest(unittest.TestCase):
    def test_quotes_and_spaces(self):
        self.assertEqual(
            tokenize_command('load "file with spaces.json"'),
            ["load", "file with spaces.json"],
        )

    def test_single_quotes(self):
        self.assertEqual(tokenize_command("export 'my format'"), ["export", "my format"])

    def test_escaped_space(self):
        self.assertEqual(tokenize_command("load file\\ name.json"), ["load", "file name.json"])

    def test_empty_string_argument(self):
        self.assertEqual(tokenize_command('export ""'), ["export", ""])

    def test_unterminated_quote(self):
        with self.assertRaises(CommandError):
            tokenize_command('load "abc')


class REPLTest(unittest.TestCase):
    def test_load_render_analyze_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "activity.json").write_text(ACTIVITY, encoding="utf-8")
            repl = REPL(root)
            output = []

            repl.dispatch("load activity.json", output.append)
            self.assertEqual(repl.kind, "activity")
            self.assertIn("Загружено", output[-1])

            repl.dispatch("validate", output.append)
            self.assertIn("Схема корректна", output[-1])

            repl.dispatch("render activity", output.append)
            self.assertIn("Activity Diagram:", output[-1])

            repl.dispatch("analyze", output.append)
            self.assertIn("Анализ графа деятельности", output[-1])

            repl.dispatch("export markdown", output.append)
            self.assertTrue((root / "activity-diagram.md").is_file())
            self.assertIn("activity-diagram.md", output[-1])

            repl.dispatch("plugins", output.append)
            self.assertIn("Плагины не загружены", output[-1])

            self.assertFalse(repl.dispatch("quit", output.append))

    def test_render_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "activity.json").write_text(ACTIVITY, encoding="utf-8")
            repl = REPL(root)
            output = []
            repl.dispatch("load activity.json", output.append)
            with self.assertRaises(CommandError):
                repl.dispatch("render sequence", output.append)

    def test_validate_without_load(self):
        with tempfile.TemporaryDirectory() as directory:
            repl = REPL(Path(directory))
            with self.assertRaises(CommandError):
                repl.dispatch("validate", lambda text: None)

    def test_run_writes_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "activity.json").write_text(ACTIVITY, encoding="utf-8")
            repl = REPL(root)
            commands = iter(["load activity.json", "render activity", "unknown", "quit"])
            outputs = []

            def input_fn(prompt):
                try:
                    return next(commands)
                except StopIteration:
                    raise EOFError

            repl.run(input_fn=input_fn, output_fn=outputs.append)
            history = (root / "history.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                history,
                ["load activity.json", "render activity", "unknown", "quit"],
            )
            self.assertTrue(any("Ошибка:" in line for line in outputs))


if __name__ == "__main__":
    unittest.main()
