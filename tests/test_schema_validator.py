import unittest

from src.schema_validator import (
    SchemaError,
    validate_activity,
    validate_sequence,
)


class SchemaValidatorTest(unittest.TestCase):
    def test_valid_sequence(self):
        data = {
            "sequence": [
                {
                    "actor": "A",
                    "action": "Do",
                    "target": "B",
                    "parameters": ["x: 1"],
                }
            ]
        }
        self.assertIs(validate_sequence(data), data)

    def test_missing_field(self):
        data = {"sequence": [{"action": "Do", "target": "B"}]}
        with self.assertRaises(SchemaError) as context:
            validate_sequence(data)
        self.assertEqual(context.exception.path, "sequence[0].actor")
        self.assertIn("missing required field", str(context.exception))

    def test_wrong_type_with_path(self):
        data = {
            "sequence": [
                {"actor": "A", "action": "Do", "target": "B"},
                {
                    "actor": "A",
                    "action": "Do",
                    "target": "B",
                    "parameters": "not-an-array",
                },
            ]
        }
        with self.assertRaises(SchemaError) as context:
            validate_sequence(data)
        self.assertEqual(context.exception.path, "sequence[1].parameters")
        self.assertIn("expected array, got string", str(context.exception))

    def test_empty_sequence(self):
        with self.assertRaises(SchemaError) as context:
            validate_sequence({"sequence": []})
        self.assertEqual(context.exception.path, "sequence")
        self.assertIn("at least 1", str(context.exception))

    def test_top_level_type(self):
        with self.assertRaises(SchemaError) as context:
            validate_sequence([])
        self.assertIn("expected object, got array", str(context.exception))

    def test_empty_string_field(self):
        data = {"sequence": [{"actor": "", "action": "Do", "target": "B"}]}
        with self.assertRaises(SchemaError) as context:
            validate_sequence(data)
        self.assertEqual(context.exception.path, "sequence[0].actor")
        self.assertIn("must not be empty", str(context.exception))

    def test_valid_activity(self):
        data = {
            "activity": [
                {"step": "Start", "next": "End"},
                {"step": "End"},
            ]
        }
        self.assertIs(validate_activity(data), data)

    def test_condition_requires_branches(self):
        data = {
            "activity": [
                {"step": "Start", "condition": "a > 1", "true": "End"},
                {"step": "End"},
            ]
        }
        with self.assertRaises(SchemaError) as context:
            validate_activity(data)
        self.assertEqual(context.exception.path, "activity[0].false")

    def test_activity_step_wrong_type(self):
        data = {"activity": [{"step": 10}]}
        with self.assertRaises(SchemaError) as context:
            validate_activity(data)
        self.assertEqual(context.exception.path, "activity[0].step")
        self.assertIn("expected string, got integer", str(context.exception))

    def test_extra_fields_allowed(self):
        data = {
            "sequence": [
                {
                    "actor": "A",
                    "action": "Do",
                    "target": "B",
                    "comment": "extra",
                }
            ]
        }
        validate_sequence(data)


if __name__ == "__main__":
    unittest.main()
