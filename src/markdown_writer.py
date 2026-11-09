"""Генерация Markdown-отчётов по диаграммам."""

from __future__ import annotations

from pathlib import Path


def _cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def sequence_markdown(diagram):
    lines = [
        "# Диаграмма последовательности",
        "",
        "```text",
        diagram.render(),
        "```",
        "",
        "## Участники",
        "",
    ]
    for participant in diagram.participants():
        lines.append("- {}".format(participant))
    lines.extend(
        [
            "",
            "## Взаимодействия",
            "",
            "| # | Actor | Action | Target | Parameters |",
            "|---|-------|--------|--------|------------|",
        ]
    )
    for index, event in enumerate(diagram.events, start=1):
        parameters = ", ".join(str(item) for item in event.get("parameters", []))
        lines.append(
            "| {} | {} | {} | {} | {} |".format(
                index,
                _cell(event["actor"]),
                _cell(event["action"]),
                _cell(event["target"]),
                _cell(parameters),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _bullets(items, empty_text="нет"):
    if not items:
        return ["- {}".format(empty_text)]
    return ["- {}".format(item) for item in items]


def activity_markdown(diagram, analysis):
    lines = [
        "# Диаграмма деятельности",
        "",
        "```text",
        diagram.render(),
        "```",
        "",
        "## Анализ",
        "",
        "Узлов: **{}**, уникальных переходов: **{}**.".format(
            len(analysis["nodes"]), analysis["edge_count"]
        ),
        "",
        "### Циклы",
        "",
    ]
    if analysis["cycles"]:
        for component in analysis["cycles"]:
            lines.append(
                "- Цикл: {}".format(" -> ".join(component))
                if len(component) > 1
                else "- Самопетля: {}".format(component[0])
            )
    else:
        lines.append("- не найдены")

    lines.extend(["", "### Недостижимые шаги", ""])
    lines.extend(_bullets(analysis["unreachable"]))

    lines.extend(["", "### Висящие узлы (без входящих переходов)", ""])
    lines.extend(_bullets(analysis["roots"]))

    lines.extend(["", "### Тупиковые узлы (без исходящих переходов)", ""])
    lines.extend(_bullets(analysis["sinks"]))
    if analysis["dead_ends"]:
        lines.append(
            "- Внимание: не финальные шаги: {}".format(
                ", ".join(analysis["dead_ends"])
            )
        )

    lines.extend(["", "### Порядок выполнения", ""])
    if analysis["topological_order"] is None:
        lines.append("- Топологическая сортировка невозможна: обнаружены циклы.")
    else:
        for index, node in enumerate(analysis["topological_order"], start=1):
            lines.append("{}. {}".format(index, node))

    lines.extend(["", "### Предупреждения", ""])
    lines.extend(_bullets(analysis["warnings"]))
    lines.append("")
    return "\n".join(lines)


def write_sequence_report(path, diagram):
    path = Path(path)
    path.write_text(sequence_markdown(diagram), encoding="utf-8")
    return path


def write_activity_report(path, diagram, analysis=None):
    path = Path(path)
    if analysis is None:
        analysis = diagram.analyze()
    path.write_text(activity_markdown(diagram, analysis), encoding="utf-8")
    return path
