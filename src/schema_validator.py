"""Минималистичный декларативный движок валидации схем.

Правила описываются обычными словарями: type, required, properties,
items, min_items, non_empty, min_length, min_value/max_value, enum.
"""

from __future__ import annotations


class SchemaError(ValueError):
    """Ошибка валидации с путём до проблемного поля."""

    def __init__(self, path, message):
        self.path = path or "$"
        self.message = message
        super().__init__(str(self))

    def __str__(self):
        return "{}: {}".format(self.path, self.message)


def _actual_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def _is_type(value, expected):
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "any":
        return True
    raise ValueError("Unknown schema type: {}".format(expected))


def _join(path, key):
    return "{}.{}".format(path, key) if path else str(key)


def _index_path(path, index):
    return "{}[{}]".format(path, index)


def validate(data, schema, path=""):
    """Проверить значение по декларативной схеме.

    :raises SchemaError: при первом найденном нарушении.
    """

    expected_type = schema.get("type")
    if expected_type is not None and not _is_type(data, expected_type):
        raise SchemaError(
            path or "$",
            "expected {}, got {}".format(expected_type, _actual_type(data)),
        )

    if expected_type == "object":
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                raise SchemaError(_join(path, field), "missing required field")
        properties = schema.get("properties", {})
        for name, subschema in properties.items():
            field_path = _join(path, name)
            if name in data:
                validate(data[name], subschema, field_path)
            elif subschema.get("required"):
                raise SchemaError(field_path, "missing required field")

    elif expected_type == "array":
        min_items = schema.get("min_items")
        if min_items is not None and len(data) < min_items:
            raise SchemaError(
                path or "$",
                "expected at least {} item(s), got {}".format(min_items, len(data)),
            )
        max_items = schema.get("max_items")
        if max_items is not None and len(data) > max_items:
            raise SchemaError(
                path or "$",
                "expected at most {} item(s), got {}".format(max_items, len(data)),
            )
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(data):
                validate(item, item_schema, _index_path(path, index))

    elif expected_type == "string":
        if schema.get("non_empty") and data == "":
            raise SchemaError(path or "$", "must not be empty")
        min_length = schema.get("min_length")
        if min_length is not None and len(data) < min_length:
            raise SchemaError(
                path or "$",
                "expected length >= {}, got {}".format(min_length, len(data)),
            )

    if "enum" in schema and data not in schema["enum"]:
        raise SchemaError(
            path or "$",
            "expected one of {}, got {!r}".format(schema["enum"], data),
        )

    if expected_type in ("integer", "number"):
        min_value = schema.get("min_value")
        if min_value is not None and data < min_value:
            raise SchemaError(path or "$", "expected value >= {}".format(min_value))
        max_value = schema.get("max_value")
        if max_value is not None and data > max_value:
            raise SchemaError(path or "$", "expected value <= {}".format(max_value))


SEQUENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "sequence": {
            "type": "array",
            "required": True,
            "min_items": 1,
            "items": {
                "type": "object",
                "properties": {
                    "actor": {"type": "string", "required": True, "non_empty": True},
                    "action": {"type": "string", "required": True, "non_empty": True},
                    "target": {"type": "string", "required": True, "non_empty": True},
                    "parameters": {"type": "array", "required": False, "items": {}},
                },
            },
        }
    },
}

ACTIVITY_SCHEMA = {
    "type": "object",
    "properties": {
        "activity": {
            "type": "array",
            "required": True,
            "min_items": 1,
            "items": {
                "type": "object",
                "properties": {
                    "step": {"type": "string", "required": True, "non_empty": True},
                    "next": {"type": "string", "required": False, "non_empty": True},
                    "condition": {
                        "type": "string",
                        "required": False,
                        "non_empty": True,
                    },
                    "true": {"type": "string", "required": False, "non_empty": True},
                    "false": {"type": "string", "required": False, "non_empty": True},
                },
            },
        }
    },
}


def validate_sequence(data):
    validate(data, SEQUENCE_SCHEMA)
    return data


def validate_activity(data):
    validate(data, ACTIVITY_SCHEMA)
    for index, step in enumerate(data["activity"]):
        path = _index_path("activity", index)
        if "condition" in step:
            for branch in ("true", "false"):
                if branch not in step:
                    raise SchemaError(
                        _join(path, branch),
                        "required when 'condition' is present",
                    )
    return data
