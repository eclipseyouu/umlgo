"""CLI-точка входа приложения."""

from __future__ import annotations

import sys
from pathlib import Path

from .activity_diagram import ActivityDiagram, ActivityError
from .condition_parser import ConditionError
from .graph_analysis import format_analysis
from .json_parser import JSONParseError, parse_json
from .markdown_writer import write_activity_report, write_sequence_report
from .plugin_loader import PluginManager
from .repl import REPL, CommandError
from .schema_validator import SchemaError
from .sequence_diagram import SequenceDiagram

USAGE = """Использование:
  python run.py --repl
  python run.py --file <input.json> [--render sequence|activity] [--analyze] [--export <format>]

Опции:
  --file <path>       входной JSON (sequence или activity)
  --render <kind>     вывести диаграмму в терминал
  --analyze           анализ графа деятельности
  --export <format>   markdown или формат плагина (например, mermaid)
  --plugins-dir <dir> каталог плагинов (по умолчанию ./plugins)
"""


def _project_root():
    return Path(__file__).resolve().parent.parent


def _plugins_directory(root, explicit):
    if explicit is not None:
        return Path(explicit)
    local = root / "plugins"
    if local.is_dir():
        return local
    return _project_root() / "plugins"


def _load_diagram(path):
    text = Path(path).read_text(encoding="utf-8")
    data = parse_json(text)
    if not isinstance(data, dict):
        raise SchemaError("$", "expected object, got {}".format(type(data).__name__))
    has_sequence = "sequence" in data
    has_activity = "activity" in data
    if has_sequence == has_activity:
        raise SchemaError("$", "expected exactly one of 'sequence' or 'activity'")
    if has_sequence:
        return data, SequenceDiagram.from_data(data), "sequence"
    return data, ActivityDiagram.from_data(data), "activity"


def _parse_options(argv):
    options = {
        "repl": False,
        "file": None,
        "render": None,
        "analyze": False,
        "export": None,
        "plugins_dir": None,
        "help": False,
    }
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in ("--repl",):
            options["repl"] = True
        elif argument in ("--analyze",):
            options["analyze"] = True
        elif argument in ("--help", "-h"):
            options["help"] = True
        elif argument in ("--file", "-f", "--render", "--export", "--plugins-dir"):
            if index + 1 >= len(argv):
                raise CommandError("missing value for {}".format(argument))
            index += 1
            key = {
                "--file": "file",
                "-f": "file",
                "--render": "render",
                "--export": "export",
                "--plugins-dir": "plugins_dir",
            }[argument]
            options[key] = argv[index]
        else:
            raise CommandError("unknown option {!r}".format(argument))
        index += 1
    return options


def _export(diagram, kind, export_format, root, plugin_manager):
    export_format = export_format.lower()
    if export_format in ("markdown", "md"):
        if kind == "sequence":
            return write_sequence_report(root / "sequence-diagram.md", diagram)
        return write_activity_report(root / "activity-diagram.md", diagram)
    exporters = plugin_manager.registry.get("exporters", {})
    exporter = exporters.get(export_format)
    if exporter is None:
        available = ["markdown"] + sorted(exporters)
        raise CommandError(
            "unknown export format {!r}; available: {}".format(
                export_format, ", ".join(available)
            )
        )
    text = exporter(diagram, kind)
    extensions = {"mermaid": "mmd", "plantuml": "puml"}
    extension = extensions.get(export_format, export_format)
    path = root / "{}-diagram.{}".format(kind, extension)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    try:
        options = _parse_options(argv)
    except CommandError as error:
        print("Ошибка: {}".format(error), file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    if options["help"]:
        print(USAGE)
        return 0

    plugin_manager = PluginManager()
    plugin_manager.load_directory(
        _plugins_directory(root, options["plugins_dir"])
    )

    if options["repl"] or not options["file"]:
        repl = REPL(root, plugin_manager)
        if options["file"]:
            try:
                path = Path(options["file"])
                repl.load_text(path.read_text(encoding="utf-8"), path)
            except (JSONParseError, SchemaError, ActivityError, ConditionError, OSError) as error:
                print("Ошибка: {}".format(error), file=sys.stderr)
                return 1
        return repl.run()

    try:
        _, diagram, kind = _load_diagram(options["file"])
        performed = False
        if options["render"] is not None:
            if options["render"] not in ("sequence", "activity"):
                raise CommandError("unknown diagram type {!r}".format(options["render"]))
            if options["render"] != kind:
                raise CommandError(
                    "loaded diagram is {}, not {}".format(kind, options["render"])
                )
            print(diagram.render())
            performed = True
        if options["analyze"]:
            if kind != "activity":
                raise CommandError("--analyze is available only for activity diagrams")
            print(format_analysis(diagram.analyze()))
            performed = True
        if options["export"] is not None:
            path = _export(
                diagram, kind, options["export"], root, plugin_manager
            )
            print("Записано: {}".format(path))
            performed = True
        if not performed:
            print(diagram.render())
        return 0
    except (JSONParseError, SchemaError, ActivityError, ConditionError, CommandError, OSError) as error:
        print("Ошибка: {}".format(error), file=sys.stderr)
        return 1
