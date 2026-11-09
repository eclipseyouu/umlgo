# Автоматизированное проектирование UML-диаграмм

Консольное приложение на Python для построения текстовых диаграмм
последовательности и деятельности из JSON-описания, анализа графа
деятельности и экспорта отчётов в Markdown/Mermaid.

Проект использует только стандартную библиотеку Python: сторонние пакеты
не требуются. Поддерживается Python 3.9+ (рекомендуется 3.11+).

## Возможности

- собственный JSON-парсер с позициями ошибок, escape-последовательностями
  (`\"`, `\\`, `\n`, `\t`, `\uXXXX`) и ограничением вложенности 512;
- декларативная валидация схем с путём до поля
  (`sequence[1].parameters: expected array, got string`);
- парсер логических условий (`AND`, `OR`, `NOT`, скобки, сравнения);
- анализ графа: циклы (итеративный Тарьян), недостижимые шаги, тупики,
  висящие узлы, топологическая сортировка;
- Markdown-отчёты `sequence-diagram.md` и `activity-diagram.md`;
- плагины с изоляцией ошибок и пример экспорта в Mermaid;
- REPL с историей команд;
- benchmark на 10 000 шагов.

## По-простому: что делает программа

Программа — это «переводчик»: вы даёте ей описание процесса в JSON-файле,
а она строит понятную текстовую UML-диаграмму и отчёт.

- **Диаграмма последовательности** — кто с кем общается и в каком порядке
  (например: клиент → система заказов → оплата).
- **Диаграмма деятельности** — шаги процесса и ветвления (например:
  проверили товар → оплатили или уведомили клиента).

Есть два способа работы:

1. **REPL** — интерактивный режим, где команды вводятся по одной.
2. **Одна команда** — сразу указать файл и действие.

В примерах ниже используется `python3`. В некоторых системах команда
называется просто `python`.

### Первый запуск по шагам

1. Откройте терминал.
2. Перейдите в папку проекта (путь может отличаться):

   ```bash
   cd "/home/student/Рабочий стол/sh/prrrr"
   ```

3. Запустите интерактивный режим:

   ```bash
   python3 run.py --repl
   ```

4. Появится приглашение `>`. Вводите команды по одной:

   ```text
   > help
   > load samples/activity_sample.json
   > render activity
   > analyze
   > export markdown
   > quit
   ```

Что делает каждая команда:

| Команда | Что произойдёт |
|---|---|
| `help` | покажет список всех команд |
| `load samples/activity_sample.json` | прочитает и проверит JSON-файл |
| `render activity` | выведет диаграмму деятельности в терминал |
| `analyze` | покажет циклы, недостижимые шаги и тупики |
| `export markdown` | создаст файл `activity-diagram.md` |
| `quit` | завершит программу |

Пример сеанса:

```text
> load samples/activity_sample.json
Загружено: .../samples/activity_sample.json (activity)
> render activity
Activity Diagram:
StartOrderProcessing -> CheckInventory
CheckInventory -> ProcessPayment (if inventoryAvailable AND NOT blacklisted)
...
> analyze
Анализ графа деятельности
  Узлов: 6   Переходов: 5
  Циклы: не найдены
...
> export markdown
Отчёт записан: .../activity-diagram.md
> quit
```

### Те же действия одной командой

Без REPL удобно запускать отдельные операции:

```bash
# Диаграмма последовательности
python3 run.py --file samples/sequence_sample.json --render sequence

# Диаграмма деятельности
python3 run.py --file samples/activity_sample.json --render activity

# Анализ графа
python3 run.py --file samples/activity_sample.json --analyze

# Markdown-отчёт
python3 run.py --file samples/activity_sample.json --export markdown

# Mermaid-разметка через плагин
python3 run.py --file samples/activity_sample.json --export mermaid
```

- `--file` — путь к входному JSON-файлу;
- `--render sequence|activity` — какая диаграмма нужна;
- `--analyze` — только анализ графа деятельности;
- `--export markdown|mermaid` — куда сохранить результат.

### Где посмотреть результат

- В терминале — сама диаграмма и сообщения программы.
- В папке проекта после `export markdown`:
  - `activity-diagram.md` — отчёт с диаграммой и блоком «Анализ»;
  - `sequence-diagram.md` — отчёт по диаграмме последовательности.
- После `export mermaid`:
  - `activity-diagram.mmd` или `sequence-diagram.mmd` — файл для
    Mermaid-редактора.

### Как описать свой процесс

Проще всего скопировать пример из `samples/` и изменить названия.
Для диаграммы деятельности главное:

```json
{"step": "ПроверитьЗаказ", "next": "Оплатить"}
```

или с условием:

```json
{
  "step": "ПроверитьЗаказ",
  "condition": "товарЕсть AND NOT клиентВЧёрномСписке",
  "true": "Оплатить",
  "false": "УведомитьКлиента"
}
```

- `step` — название шага (уникальное);
- `next` — следующий шаг;
- `condition` — условие;
- `true` / `false` — куда идти, если условие истинно или ложно.

Подробное описание форматов JSON находится ниже, в разделе «Формат JSON».

## Запуск

Из корня проекта:

```bash
python run.py --repl
python run.py --file samples/activity_sample.json --render activity
python run.py --file samples/activity_sample.json --analyze
python run.py --file samples/sequence_sample.json --render sequence
python run.py --file samples/activity_sample.json --export markdown
python run.py --file samples/activity_sample.json --export mermaid
```

Пример вывода:

```text
Activity Diagram:
StartOrderProcessing -> CheckInventory
CheckInventory -> ProcessPayment (if inventoryAvailable AND NOT blacklisted)
CheckInventory -> NotifyCustomer (if NOT (inventoryAvailable AND NOT blacklisted))
ProcessPayment -> CompleteOrder
NotifyCustomer -> EndOrderProcessing
```

```text
Sequence Diagram:
Customer -> OrderSystem: PlaceOrder(item: Milk, quantity: 2)
OrderSystem -> Order: CreateOrder(id: 123, items: [Milk])
Order -> PaymentGateway: ProcessPayment(amount: 50)
```

## Формат JSON

### Диаграмма последовательности

```json
{
  "sequence": [
    {"actor": "Customer", "action": "PlaceOrder", "target": "OrderSystem", "parameters": ["item: Milk", "quantity: 2"]},
    {"actor": "OrderSystem", "action": "CreateOrder", "target": "Order", "parameters": ["id: 123", "items: [Milk]"]},
    {"actor": "Order", "action": "ProcessPayment", "target": "PaymentGateway", "parameters": ["amount: 50"]}
  ]
}
```

Обязательные поля элемента: `actor`, `action`, `target` (непустые строки).
`parameters` — необязательный массив.

### Диаграмма деятельности

```json
{
  "activity": [
    {"step": "StartOrderProcessing", "next": "CheckInventory"},
    {"step": "CheckInventory", "condition": "inventoryAvailable AND NOT blacklisted", "true": "ProcessPayment", "false": "NotifyCustomer"},
    {"step": "ProcessPayment", "next": "CompleteOrder"},
    {"step": "NotifyCustomer", "next": "EndOrderProcessing"}
  ]
}
```

- `step` — обязательное уникальное имя шага;
- `next` — безусловный переход;
- `condition` — условие; при наличии обязательны `true` и `false`;
- у шага могут быть одновременно `next` и `condition` (безусловный переход
  плюс ветвление);
- шаг без исходящих переходов — финальный;
- если переход ссылается на шаг, для которого нет отдельной записи
  (например, `CompleteOrder` в примере выше), создаётся неявный финальный
  узел и выводится предупреждение в анализе.

Условия поддерживают `AND`, `OR`, `NOT`, скобки и сравнения
`==`, `!=`, `<`, `>`, `<=`, `>=`. Приоритеты: `NOT` > `AND` > `OR`,
сравнения выше логических операций. В отчёте условие нормализуется,
например `NOT (inventoryAvailable AND NOT blacklisted)`.

## Команды REPL

| Команда | Назначение |
|---|---|
| `load <file>` | загрузить и проверить JSON |
| `validate` | повторно проверить схему, условия и ссылки |
| `render sequence` | вывести диаграмму последовательности |
| `render activity` | вывести диаграмму деятельности |
| `analyze` | анализ графа деятельности |
| `export <format>` | `markdown`, `mermaid` или формат плагина |
| `plugins` | список загруженных плагинов и экспортёров |
| `help` | справка |
| `quit` / `exit` | выход |

История команд сохраняется в `history.txt` в рабочем каталоге.
Аргументы с пробелами заключаются в кавычки: `load "my file.json"`.

## Плагины

Плагины — `.py`-файлы в каталоге `plugins/`. Каждый обязан определить:

```python
NAME = "mermaid_export"

def register(registry):
    registry.setdefault("exporters", {})["mermaid"] = export

def export(diagram, kind):
    # diagram — SequenceDiagram или ActivityDiagram, kind — "sequence"/"activity"
    return "..."
```

Загрузка выполняется через `importlib.util.spec_from_file_location` с
уникальным именем модуля. Ошибки импорта, отсутствие `register`, конфликты
имён и исключения внутри `register()` логируются и не останавливают
приложение; частично зарегистрированные экспортёры откатываются.

В комплекте:

- `plugins/mermaid_export.py` — экспорт в Mermaid (`sequenceDiagram` и
  `flowchart TD`), формат `mermaid`.

Экспорт плагина записывается в `<kind>-diagram.<ext>`, например
`activity-diagram.mmd`.

## Анализ графа

Для диаграммы деятельности строятся:

- начальные узлы — вершины без входящих переходов (если их несколько,
  выводится предупреждение);
- недостижимые из начальных узлов шаги;
- тупики — вершины без исходящих переходов; не финальными считаются имена,
  не начинающиеся с `End`;
- циклы — сильно связные компоненты размера > 1 и самопетли (итеративный
  алгоритм Тарьяна);
- топологический порядок (только для ациклического графа).

Все предупреждения выводятся в консоль и попадают в раздел «Анализ»
Markdown-отчёта.

## Структура проекта

```text
project/
├── src/
│   ├── main.py
│   ├── json_parser.py
│   ├── schema_validator.py
│   ├── condition_parser.py
│   ├── sequence_diagram.py
│   ├── activity_diagram.py
│   ├── graph_analysis.py
│   ├── markdown_writer.py
│   ├── plugin_loader.py
│   └── repl.py
├── plugins/
│   └── mermaid_export.py
├── samples/
│   ├── sequence_sample.json
│   └── activity_sample.json
├── tests/
│   └── test_*.py
├── benchmark.py
├── README.md
└── run.py
```

## Тестирование

```bash
python -m unittest discover -s tests -v
```

Тесты покрывают JSON-парсер (включая ошибки и глубокую вложенность),
валидатор схем, парсер условий, анализ графа (циклы, самопетли,
недостижимые узлы, тупики), загрузчик плагинов, REPL и интеграционные
сценарии «JSON → диаграмма → Markdown».

Если установлен `coverage.py`, покрытие можно измерить так:

```bash
coverage run -m unittest discover -s tests
coverage report -m
```

Без сторонних библиотек покрытие подтверждается списком тестовых
сценариев выше; все основные модули (`src/*.py`) задействованы в тестах.
Дополнительно можно измерить покрытие стандартным модулем `trace`:

```bash
python -m trace --count --missing --coverdir .coverage_trace \
    --module unittest discover -s tests
```

При текущем наборе тестов покрытие `src/` составляет около 84%
(1256 из 1500 исполняемых строк).

## Производительность

```bash
python benchmark.py
```

Скрипт создаёт `bench_activity.json` с 10 000 шагов и ~30 000 переходов,
замеряет через `time.perf_counter()` парсинг, валидацию, построение графа,
анализ и рендеринг. Все алгоритмы анализа имеют сложность O(V + E)
(топологическая сортировка — O((V + E) log V) за счёт приоритетной очереди
для детерминированного порядка). Ожидаемое суммарное время — менее 2 секунд.

## SSH-ключ для GitHub

Актуальный публичный ключ для добавления в GitHub: **Settings → SSH and
GPG keys → New SSH key**.

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPPZuhG24pIF32f6sZu08AokuUo2mBPvir8KxjIWoJba student@cab-127-stud07
```

Скопируйте строку целиком, включая `ssh-ed25519` и комментарий в конце.
