"""Пример плагина: экспорт диаграмм в Mermaid."""

NAME = "mermaid_export"


def _label(value):
    return str(value).replace('"', "'").replace("|", "/").replace("\n", " ")


def _sequence_mermaid(diagram):
    participants = diagram.participants()
    ids = {name: "p{}".format(index) for index, name in enumerate(participants)}
    lines = ["sequenceDiagram"]
    for name in participants:
        lines.append("    participant {} as {}".format(ids[name], _label(name)))
    for event in diagram.events:
        parameters = ", ".join(str(item) for item in event.get("parameters", []))
        lines.append(
            "    {}->>{}: {}({})".format(
                ids[event["actor"]],
                ids[event["target"]],
                _label(event["action"]),
                _label(parameters),
            )
        )
    return "\n".join(lines)


def _activity_mermaid(diagram):
    ids = {name: "n{}".format(index) for index, name in enumerate(diagram.nodes)}
    lines = ["flowchart TD"]
    for name in diagram.nodes:
        lines.append('    {}["{}"]'.format(ids[name], _label(name)))
    for edge in diagram.edges:
        source = ids[edge["source"]]
        target = ids[edge["target"]]
        if edge["condition"] is None:
            lines.append("    {} --> {}".format(source, target))
        else:
            lines.append(
                '    {} -->|"{}"| {}'.format(
                    source, _label(edge["condition"]), target
                )
            )
    return "\n".join(lines)


def export(diagram, kind):
    if kind == "sequence":
        return _sequence_mermaid(diagram)
    if kind == "activity":
        return _activity_mermaid(diagram)
    raise ValueError("mermaid exporter does not support kind {!r}".format(kind))


def register(registry):
    registry.setdefault("exporters", {})["mermaid"] = export
