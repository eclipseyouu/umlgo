"""Анализ графа деятельности.

Реализованы итеративный алгоритм Тарьяна (SCC), поиск недостижимых
вершин, тупиков и топологическая сортировка. Сложность O(V + E).
"""

from __future__ import annotations

import heapq


def _tarjan_scc(nodes, adjacency):
    """Итеративный Тарьян: возвращает список сильно связных компонент."""
    index = {}
    lowlink = {}
    on_stack = set()
    stack = []
    components = []
    counter = 0

    for start in nodes:
        if start in index:
            continue
        index[start] = counter
        lowlink[start] = counter
        counter += 1
        stack.append(start)
        on_stack.add(start)
        frames = [[start, 0]]

        while frames:
            node, position = frames[-1]
            if position < len(adjacency[node]):
                neighbour = adjacency[node][position]
                frames[-1][1] += 1
                if neighbour not in index:
                    index[neighbour] = counter
                    lowlink[neighbour] = counter
                    counter += 1
                    stack.append(neighbour)
                    on_stack.add(neighbour)
                    frames.append([neighbour, 0])
                elif neighbour in on_stack:
                    if index[neighbour] < lowlink[node]:
                        lowlink[node] = index[neighbour]
            else:
                frames.pop()
                if lowlink[node] == index[node]:
                    component = []
                    while True:
                        member = stack.pop()
                        on_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break
                    components.append(component)
                if frames:
                    parent = frames[-1][0]
                    if lowlink[node] < lowlink[parent]:
                        lowlink[parent] = lowlink[node]

    return components


def analyze_graph(nodes, edges):
    """Проанализировать ориентированный граф.

    ``nodes`` — упорядоченный список имён, ``edges`` — пары (source, target).
    Возвращает словарь с циклами, недостижимыми шагами, тупиками,
    начальными узлами, топологическим порядком и предупреждениями.
    """
    nodes = list(nodes)
    if not nodes:
        return {
            "nodes": [],
            "edge_count": 0,
            "start_nodes": [],
            "roots": [],
            "reachable_count": 0,
            "unreachable": [],
            "sinks": [],
            "dead_ends": [],
            "cycles": [],
            "has_cycle": False,
            "topological_order": [],
            "warnings": [],
        }

    order_index = {node: i for i, node in enumerate(nodes)}
    adjacency = {node: [] for node in nodes}
    indegree = {node: 0 for node in nodes}
    seen_edges = set()

    for source, target in edges:
        if source not in adjacency or target not in adjacency:
            raise ValueError("Edge references unknown node: {!r} -> {!r}".format(source, target))
        key = (source, target)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        adjacency[source].append(target)
        indegree[target] += 1

    roots = [node for node in nodes if indegree[node] == 0]
    warnings = []

    if len(roots) > 1:
        warnings.append(
            "Multiple start nodes (no incoming transitions): {}".format(", ".join(roots))
        )
    elif not roots:
        warnings.append(
            "No start node (node without incoming transitions); using {!r}".format(nodes[0])
        )

    start_nodes = roots if roots else [nodes[0]]

    reachable = set(start_nodes)
    stack = list(start_nodes)
    while stack:
        node = stack.pop()
        for neighbour in adjacency[node]:
            if neighbour not in reachable:
                reachable.add(neighbour)
                stack.append(neighbour)

    unreachable = [node for node in nodes if node not in reachable]
    if unreachable:
        warnings.append("Unreachable steps from start: {}".format(", ".join(unreachable)))

    sinks = [node for node in nodes if not adjacency[node]]
    dead_ends = [node for node in sinks if not node.startswith("End")]
    if dead_ends:
        warnings.append(
            "Dead-end steps (no outgoing transitions, not End*): {}".format(
                ", ".join(dead_ends)
            )
        )

    raw_components = _tarjan_scc(nodes, adjacency)
    cycles = []
    for component in raw_components:
        if len(component) > 1 or component[0] in adjacency[component[0]]:
            cycles.append(sorted(component, key=order_index.get))
    cycles.sort(key=lambda component: order_index[component[0]])

    if cycles:
        warnings.append(
            "Cycles detected: {}".format(
                "; ".join("[{}]".format(", ".join(component)) for component in cycles)
            )
        )

    topological_order = None
    if not cycles:
        remaining = dict(indegree)
        heap = [(order_index[node], node) for node in nodes if remaining[node] == 0]
        heapq.heapify(heap)
        topological_order = []
        while heap:
            _, node = heapq.heappop(heap)
            topological_order.append(node)
            for neighbour in adjacency[node]:
                remaining[neighbour] -= 1
                if remaining[neighbour] == 0:
                    heapq.heappush(heap, (order_index[neighbour], neighbour))
        if len(topological_order) != len(nodes):
            topological_order = None

    return {
        "nodes": nodes,
        "edge_count": len(seen_edges),
        "start_nodes": start_nodes,
        "roots": roots,
        "reachable_count": len(reachable),
        "unreachable": unreachable,
        "sinks": sinks,
        "dead_ends": dead_ends,
        "cycles": cycles,
        "has_cycle": bool(cycles),
        "topological_order": topological_order,
        "warnings": warnings,
    }


def format_analysis(analysis):
    """Человекочитаемое представление анализа (для REPL и CLI)."""
    lines = [
        "Анализ графа деятельности",
        "  Узлов: {}   Переходов: {}".format(
            len(analysis["nodes"]), analysis["edge_count"]
        ),
        "  Начальные узлы: {}".format(
            ", ".join(analysis["start_nodes"]) or "нет"
        ),
        "  Недостижимые шаги: {}".format(
            ", ".join(analysis["unreachable"]) or "нет"
        ),
        "  Тупиковые шаги (не End*): {}".format(
            ", ".join(analysis["dead_ends"]) or "нет"
        ),
    ]
    if analysis["cycles"]:
        lines.append(
            "  Циклы: {}".format(
                "; ".join(
                    "[{}]".format(", ".join(component))
                    for component in analysis["cycles"]
                )
            )
        )
    else:
        lines.append("  Циклы: не найдены")
    if analysis["topological_order"] is not None:
        lines.append("  Топологический порядок: {}".format(
            " -> ".join(analysis["topological_order"])
        ))
    else:
        lines.append("  Топологический порядок: недоступен (есть циклы)")
    if analysis["warnings"]:
        lines.append("  Предупреждения:")
        for warning in analysis["warnings"]:
            lines.append("    - {}".format(warning))
    return "\n".join(lines)
