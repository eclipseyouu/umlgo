"""Диаграмма последовательности."""

from __future__ import annotations

from .schema_validator import validate_sequence


def _parameter_to_text(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


class SequenceDiagram:
    def __init__(self, events):
        self.events = events

    @classmethod
    def from_data(cls, data):
        validate_sequence(data)
        events = [dict(event) for event in data["sequence"]]
        return cls(events)

    def participants(self):
        result = []
        seen = set()
        for event in self.events:
            for name in (event["actor"], event["target"]):
                if name not in seen:
                    seen.add(name)
                    result.append(name)
        return result

    def render(self):
        lines = ["Sequence Diagram:"]
        for event in self.events:
            parameters = event.get("parameters", [])
            rendered_parameters = ", ".join(
                _parameter_to_text(parameter) for parameter in parameters
            )
            lines.append(
                "{} -> {}: {}({})".format(
                    event["actor"],
                    event["target"],
                    event["action"],
                    rendered_parameters,
                )
            )
        return "\n".join(lines)
