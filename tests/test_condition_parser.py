import unittest

from src.condition_parser import (
    Binary,
    ConditionError,
    Var,
    normalize_condition,
    parse_condition,
)


class ConditionParserTest(unittest.TestCase):
    def test_simple_normalization(self):
        self.assertEqual(
            normalize_condition("  inventoryAvailable   AND   NOT blacklisted  "),
            "inventoryAvailable AND NOT blacklisted",
        )

    def test_precedence_or_and(self):
        self.assertEqual(normalize_condition("a OR b AND c"), "a OR b AND c")

    def test_parentheses_preserved(self):
        self.assertEqual(
            normalize_condition("( a OR b ) AND c"),
            "(a OR b) AND c",
        )

    def test_not_has_higher_precedence_than_and(self):
        self.assertEqual(normalize_condition("NOT a AND b"), "NOT a AND b")

    def test_comparisons(self):
        self.assertEqual(
            normalize_condition('amount >= 10 AND status == "ok"'),
            'amount >= 10 AND status == "ok"',
        )

    def test_comparison_with_numbers_and_negative(self):
        self.assertEqual(normalize_condition("x > -5 OR y <= 2.5"), "x > -5 OR y <= 2.5")

    def test_not_around_comparison(self):
        self.assertEqual(normalize_condition("NOT a == b"), "NOT (a == b)")

    def test_double_parentheses(self):
        self.assertEqual(normalize_condition("((a))"), "a")

    def test_string_escapes(self):
        self.assertEqual(
            normalize_condition(r'name == "a\"b"'),
            r'name == "a\"b"',
        )

    def test_boolean_literals(self):
        self.assertEqual(normalize_condition("flag == true"), "flag == true")

    def test_ast_shape(self):
        node = parse_condition("a OR b AND c")
        self.assertIsInstance(node, Binary)
        self.assertEqual(node.op, "OR")
        self.assertIsInstance(node.left, Var)
        self.assertEqual(node.right.op, "AND")

    def test_syntax_error_unexpected_character(self):
        with self.assertRaises(ConditionError) as context:
            parse_condition("a & b")
        self.assertIn("Unexpected character", str(context.exception))
        self.assertIn("at 1:3", str(context.exception))

    def test_syntax_error_missing_parenthesis(self):
        with self.assertRaises(ConditionError) as context:
            parse_condition("(a AND b")
        self.assertIn("Expected ')'", str(context.exception))

    def test_syntax_error_single_equals(self):
        with self.assertRaises(ConditionError) as context:
            parse_condition("a = b")
        self.assertIn("use '=='", str(context.exception))

    def test_syntax_error_unterminated_string(self):
        with self.assertRaises(ConditionError) as context:
            parse_condition('a == "x')
        self.assertIn("Unterminated string", str(context.exception))

    def test_syntax_error_unexpected_end(self):
        with self.assertRaises(ConditionError):
            parse_condition("a AND")

    def test_type_error(self):
        with self.assertRaises(TypeError):
            parse_condition(123)


if __name__ == "__main__":
    unittest.main()
