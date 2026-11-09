import json
import unittest

from src.json_parser import JSONParseError, parse_json


class JSONParserTest(unittest.TestCase):
    def test_all_types(self):
        text = '{"a": [1, 2.5, -3e2, true, false, null, "x"], "b": {}}'
        self.assertEqual(parse_json(text), json.loads(text))

    def test_arbitrary_key_order_and_empty_containers(self):
        text = '{"z": [], "a": {}, "m": [{"k": 1}]}'
        self.assertEqual(parse_json(text), json.loads(text))
        self.assertEqual(list(parse_json(text).keys()), ["z", "a", "m"])

    def test_escape_sequences(self):
        text = '"quote: \\" backslash: \\\\ slash: \\/ newline:\\n tab:\\t unicode:\\u0041"'
        self.assertEqual(parse_json(text), json.loads(text))
        self.assertEqual(parse_json(text), 'quote: " backslash: \\ slash: / newline:\n tab:\t unicode:A')

    def test_surrogate_pair(self):
        text = '"\\ud83d\\ude00"'
        self.assertEqual(parse_json(text), json.loads(text))
        self.assertEqual(parse_json(text), "\U0001F600")

    def test_large_numbers(self):
        text = "[123456789012345678901234567890, 1e400, -0.5]"
        self.assertEqual(parse_json(text)[0], 123456789012345678901234567890)
        self.assertEqual(parse_json(text)[1], float("inf"))
        self.assertEqual(parse_json(text)[2], -0.5)

    def test_unterminated_string_has_position(self):
        with self.assertRaises(JSONParseError) as context:
            parse_json('{\n  "a": "oops')
        message = str(context.exception)
        self.assertIn("Unterminated string", message)
        self.assertIn("at 2:", message)

    def test_invalid_escape(self):
        with self.assertRaises(JSONParseError) as context:
            parse_json('"\\x"')
        self.assertIn("Invalid escape sequence", str(context.exception))

    def test_incomplete_unicode_escape(self):
        with self.assertRaises(JSONParseError):
            parse_json('"\\u12"')

    def test_trailing_comma_object(self):
        with self.assertRaises(JSONParseError) as context:
            parse_json('{"a": 1,}')
        self.assertIn("Trailing comma", str(context.exception))

    def test_trailing_comma_array(self):
        with self.assertRaises(JSONParseError):
            parse_json("[1, 2,]")

    def test_leading_zero(self):
        with self.assertRaises(JSONParseError) as context:
            parse_json("[01]")
        self.assertIn("Leading zeros", str(context.exception))

    def test_trailing_data(self):
        with self.assertRaises(JSONParseError) as context:
            parse_json("{} {}")
        self.assertIn("Unexpected character", str(context.exception))

    def test_unexpected_character(self):
        with self.assertRaises(JSONParseError):
            parse_json("{'a': 1}")

    def test_empty_input(self):
        with self.assertRaises(JSONParseError):
            parse_json("   ")

    def test_depth_limit(self):
        text = "[" * 513 + "0" + "]" * 513
        with self.assertRaises(JSONParseError) as context:
            parse_json(text)
        self.assertIn("Maximum nesting depth", str(context.exception))

    def test_exact_depth_limit(self):
        text = "[" * 512 + "0" + "]" * 512
        value = parse_json(text)
        for _ in range(512):
            value = value[0]
        self.assertEqual(value, 0)

    def test_type_error_for_non_string(self):
        with self.assertRaises(TypeError):
            parse_json(b"{}")

    def test_bom_is_ignored(self):
        self.assertEqual(parse_json("\ufeff{\"a\": 1}"), {"a": 1})


if __name__ == "__main__":
    unittest.main()
