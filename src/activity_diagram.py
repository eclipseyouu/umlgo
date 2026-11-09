"""Диаграмма деятельности и построение графа переходов."""

from __future__ import annotations

from .condition_parser import ConditionError, parse_condition, render_condition
from .graph_analysis import analyze_graph
from .schema_validator import validate_activity


class ActivityError(ValueError):
    """Ошибка структуры диаграммы деятельности."""


class ActivityDiagram:
    def __init__(self, steps, nodes, edges, implicit_nodes=None):
        self.steps = steps
        self.nodes = nodes
        self.edges = edges
        self.implicit_nodes = implicit_nodes or []

    @classmethod
    def from_data(cls, data):
        validate_activity(data)
        steps = [dict(step) for step in data["activity"]]
        nodes = []
        known = set()
        for index, step in enumerate(steps):
            name = step["step"]
            if name in known:
                raise ActivityError(
                    "activity[{}].step: duplicate step name {!r}".format(index, name)
                )
            known.add(name)
            nodes.append(name)

        edges = []
        implicit_nodes = []
        for index, step in enumerate(steps):
            source = step["step"]
            if "next" in step:
                target = step["next"]
                cls._resolve_target(known, implicit_nodes, target)
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "condition": None,
                        "kind": "next",
                    }
                )
            if "condition" in step:
                try:
                    condition = render_condition(parse_condition(step["condition"]))
                except ConditionError as error:
                    raise ActivityError(
                        "activity[{}].condition: {}".format(index, error)
                    ) from error
                branches = (
                    ("true", condition, "true"),
                    ("false", "NOT ({})".format(condition), "false"),
                )
                for field, label, kind in branches:
                    target = step[field]
                    cls._resolve_target(known, implicit_nodes, target)
                    edges.append(
                        {
                            "source": source,
                            "target": target,
                            "condition": label,
                            "kind": kind,
                        }
                    )
        nodes.extend(implicit_nodes)
        return cls(steps, nodes, edges, implicit_nodes)

    @staticmethod
    def _resolve_target(known, implicit_nodes, target):
        # Шаг может ссылаться на узел, который не описан отдельной записью
        # (как CompleteOrder в примере из задания). Такой узел считается
        # неявным финальным шагом, но попадает в предупреждения анализа.
        if target not in known:
            known.add(target)
            implicit_nodes.append(target)

    def render(self):
        lines = ["Activity Diagram:"]
        for edge in self.edges:
            if edge["condition"] is None:
                lines.append(
                    "{} -> {}".format(edge["source"], edge["target"])
                )
            else:
                lines.append(
                    "{} -> {} (if {})".format(
                        edge["source"], edge["target"], edge["condition"]
                    )
                )
        return "\n".join(lines)

    def graph_edges(self):
        return [(edge["source"], edge["target"]) for edge in self.edges]

    def analyze(self):
        analysis = analyze_graph(self.nodes, self.graph_edges())
        if self.implicit_nodes:
            analysis["warnings"].append(
                "Implicit steps (referenced but not defined): {}".format(
                    ", ".join(self.implicit_nodes)
                )
            )
        return analysis
