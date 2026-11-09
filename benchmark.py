#!/usr/bin/env python3
"""Генератор большого графа деятельности и замер производительности."""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.activity_diagram import ActivityDiagram  # noqa: E402
from src.json_parser import parse_json  # noqa: E402
from src.schema_validator import validate_activity  # noqa: E402

STEPS = 10000
CONDITION = "inventory > 0 AND NOT blacklisted"


def build_activity_json(steps=STEPS):
    parts = ['{"activity":[']
    for index in range(steps):
        fields = ['"step":"s{}"'.format(index)]
        if index < steps - 1:
            fields.append('"next":"s{}"'.format(index + 1))
        if index < steps - 3:
            fields.append('"condition":"{}"'.format(CONDITION))
            fields.append('"true":"s{}"'.format(index + 2))
            fields.append('"false":"s{}"'.format(index + 3))
        elif index < steps - 1:
            fields.append('"condition":"{}"'.format(CONDITION))
            fields.append('"true":"s{}"'.format(steps - 1))
            fields.append('"false":"s{}"'.format(steps - 1))
        parts.append("{" + ",".join(fields) + "}")
        if index != steps - 1:
            parts.append(",")
    parts.append("]}")
    return "".join(parts)


def main():
    output = Path.cwd() / "bench_activity.json"
    text = build_activity_json()
    output.write_text(text, encoding="utf-8")
    size_mb = len(text.encode("utf-8")) / (1024 * 1024)

    start = time.perf_counter()
    data = parse_json(text)
    parse_time = time.perf_counter() - start

    start = time.perf_counter()
    validate_activity(data)
    validate_time = time.perf_counter() - start

    start = time.perf_counter()
    diagram = ActivityDiagram.from_data(data)
    build_time = time.perf_counter() - start

    start = time.perf_counter()
    analysis = diagram.analyze()
    analysis_time = time.perf_counter() - start

    start = time.perf_counter()
    rendered = diagram.render()
    render_time = time.perf_counter() - start

    total = parse_time + validate_time + build_time + analysis_time + render_time
    print("Файл: {}".format(output))
    print(
        "Шагов: {}, переходов в файле: {}, уникальных: {:.0f}, размер: {:.2f} МБ".format(
            len(diagram.nodes),
            len(diagram.edges),
            analysis["edge_count"],
            size_mb,
        )
    )
    print("JSON-парсинг:      {:.4f} с".format(parse_time))
    print("Валидация схемы:   {:.4f} с".format(validate_time))
    print("Построение графа:  {:.4f} с".format(build_time))
    print("Анализ (Тарьян):   {:.4f} с".format(analysis_time))
    print("Рендеринг:         {:.4f} с".format(render_time))
    print("Итого:             {:.4f} с".format(total))
    print("Строк в выводе: {}".format(rendered.count("\n") + 1))
    if total < 2.0:
        print("Результат: OK (< 2 c)")
        return 0
    print("Результат: FAIL (>= 2 c)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
