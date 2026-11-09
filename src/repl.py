"""Интерактивный REPL-режим приложения."""

from __future__ import annotations

from pathlib import Path

from .activity_diagram import ActivityDiagram
from .graph_analysis import format_analysis
from .json_parser import JSONParseError, parse_json
from .markdown_writer import write_activity_report, write_sequence_report
from .plugin_loader import PluginManager
from .schema_validator import SchemaError, validate_activity, validate_sequence
from .sequence_diagram import SequenceDiagram


class CommandError(ValueError):
    pass


def tokenize_command(line):
    """Разбить строку команды на аргументы с поддержкой кавычек."""
    tokens = []
    buffer = []
    started = False
    quote = None
    index = 0
    length = len(line)
    while index < length:
        char = line[index]
        if quote is not None:
            if char == quote:
                quote = None
            elif char == "\\" and index + 1 < length:
                index += 1
                buffer.append(line[index])
            else:
                buffer.append(char)
        else:
            if char.isspace():
                if started:
                    tokens.append("".join(buffer))
                    buffer = []
                    started = False
            elif char in "\"'":
                quote = char
                started = True
            elif char == "\\" and index + 1 < length:
                index += 1
                buffer.append(line[index])
                started = True
            else:
                buffer.append(char)
                started = True
        index += 1
    if quote is not None:
        raise CommandError("Unterminated quote in command")
    if started:
        tokens.append("".join(buffer))
    return tokens


class REPL:
    def __init__(self, root, plugin_manager=None):
        self.root = Path(root)
        self.plugin_manager = plugin_manager or PluginManager()
        self.history_path = self.root / "history.txt"
        self.data = None
        self.diagram = None
        self.kind = None
        self.source = None

    def run(self, input_fn=None, output_fn=None):
        input_fn = input_fn or input
        output_fn = output_fn or print
        output_fn("Диаграммы UML. Введите help для списка команд.")
        while True:
            try:
                line = input_fn("> ")
            except EOFError:
                output_fn("")
                break
            except KeyboardInterrupt:
                output_fn("")
                break
            if line is None:
                break
            if not line.strip():
                continue
            self._append_history(line)
            try:
                if not self.dispatch(line, output_fn):
                    break
            except (JSONParseError, SchemaError, CommandError, OSError) as error:
                output_fn("Ошибка: {}".format(error))
            except Exception as error:  # плагины и прочие неожиданные сбои
                output_fn("Ошибка: {}".format(error))
        return 0

    def _append_history(self, line):
        try:
            with self.history_path.open("a", encoding="utf-8") as handle:
                handle.write(line.rstrip("\n") + "\n")
        except OSError:
            pass

    def dispatch(self, line, output_fn=None):
        output_fn = output_fn or print
        tokens = tokenize_command(line)
        if not tokens:
            return True
        command = tokens[0].lower()
        arguments = tokens[1:]

        if command in ("quit", "exit"):
            return False
        if command == "help":
            self._show_help(output_fn)
        elif command == "load":
            self._command_load(arguments, output_fn)
        elif command == "validate":
            self._command_validate(output_fn)
        elif command == "render":
            self._command_render(arguments, output_fn)
        elif command == "analyze":
            self._command_analyze(output_fn)
        elif command == "export":
            self._command_export(arguments, output_fn)
        elif command == "plugins":
            self._command_plugins(output_fn)
        else:
            raise CommandError("unknown command {!r}; try help".format(tokens[0]))
        return True

    def _show_help(self, output_fn):
        output_fn(
            "Команды:\n"
            "  load <file>          загрузить JSON\n"
            "  validate             проверить схему и ссылки\n"
            "  render sequence      вывести диаграмму последовательности\n"
            "  render activity      вывести диаграмму деятельности\n"
            "  analyze              анализ графа деятельности\n"
            "  export <format>      markdown | mermaid | другой плагин\n"
            "  plugins              список плагинов\n"
            "  quit                 выход"
        )

    def _command_load(self, arguments, output_fn):
        if len(arguments) != 1:
            raise CommandError("usage: load <file>")
        path = Path(arguments[0])
        if not path.is_absolute():
            path = self.root / path
        text = path.read_text(encoding="utf-8")
        self.load_text(text, path)
        output_fn("Загружено: {} ({})".format(path, self.kind))

    def load_text(self, text, source=None):
        data = parse_json(text)
        if not isinstance(data, dict):
            raise SchemaError("$", "expected object, got {}".format(type(data).__name__))
        has_sequence = "sequence" in data
        has_activity = "activity" in data
        if has_sequence == has_activity:
            raise SchemaError("$", "expected exactly one of 'sequence' or 'activity'")
        if has_sequence:
            diagram = SequenceDiagram.from_data(data)
            kind = "sequence"
        else:
            diagram = ActivityDiagram.from_data(data)
            kind = "activity"
        self.data = data
        self.diagram = diagram
        self.kind = kind
        self.source = str(source) if source is not None else None
        return diagram

    def _command_validate(self, output_fn):
        if self.data is None:
            raise CommandError("nothing is loaded; use load <file>")
        if self.kind == "sequence":
            SequenceDiagram.from_data(self.data)
        else:
            validate_activity(self.data)
            ActivityDiagram.from_data(self.data)
        output_fn("Схема корректна: {}".format(self.kind))

    def _command_render(self, arguments, output_fn):
        if self.diagram is None:
            raise CommandError("nothing is loaded; use load <file>")
        if len(arguments) > 1:
            raise CommandError("usage: render [sequence|activity]")
        requested = arguments[0].lower() if arguments else self.kind
        if requested not in ("sequence", "activity"):
            raise CommandError("unknown diagram type {!r}".format(requested))
        if requested != self.kind:
            raise CommandError(
                "loaded diagram is {}, not {}".format(self.kind, requested)
            )
        output_fn(self.diagram.render())

    def _command_analyze(self, output_fn):
        if self.diagram is None:
            raise CommandError("nothing is loaded; use load <file>")
        if self.kind != "activity":
            raise CommandError("analyze is available only for activity diagrams")
        output_fn(format_analysis(self.diagram.analyze()))

    def _command_export(self, arguments, output_fn):
        if self.diagram is None:
            raise CommandError("nothing is loaded; use load <file>")
        if len(arguments) != 1:
            raise CommandError("usage: export <format>")
        export_format = arguments[0].lower()
        if export_format in ("markdown", "md"):
            if self.kind == "sequence":
                path = write_sequence_report(
                    self.root / "sequence-diagram.md", self.diagram
                )
            else:
                path = write_activity_report(
                    self.root / "activity-diagram.md", self.diagram
                )
            output_fn("Отчёт записан: {}".format(path))
            return
        exporters = self.plugin_manager.registry.get("exporters", {})
        exporter = exporters.get(export_format)
        if exporter is None:
            available = ["markdown"] + sorted(exporters)
            raise CommandError(
                "unknown export format {!r}; available: {}".format(
                    export_format, ", ".join(available)
                )
            )
        text = exporter(self.diagram, self.kind)
        extensions = {"mermaid": "mmd", "plantuml": "puml"}
        extension = extensions.get(export_format, export_format)
        path = self.root / "{}-diagram.{}".format(self.kind, extension)
        path.write_text(text + "\n", encoding="utf-8")
        output_fn("Экспорт записан: {}".format(path))

    def _command_plugins(self, output_fn):
        if not self.plugin_manager.plugins:
            output_fn("Плагины не загружены.")
            return
        export_names = ", ".join(
            sorted(self.plugin_manager.registry.get("exporters", {}))
        ) or "нет"
        output_fn("Экспортёры: {}".format(export_names))
        for plugin in self.plugin_manager.plugins:
            status = "ok" if plugin["loaded"] else "error"
            line = "  {} [{}] {}".format(
                plugin["name"] or Path(plugin["path"]).name, status, plugin["path"]
            )
            if plugin["error"]:
                line += " -- {}".format(plugin["error"])
            output_fn(line)
