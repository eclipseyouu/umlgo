"""Парсер логических условий для диаграммы деятельности.

Поддерживаются AND, OR, NOT, скобки и сравнения ==, !=, <, >, <=, >=.
Грамматика (от низшего приоритета к высшему): OR, AND, NOT, сравнения,
первичные выражения. Реализован рекурсивный спуск.
"""

from __future__ import annotations

from dataclasses import dataclass


class ConditionError(ValueError):
    """Синтаксическая ошибка условия с позицией."""

    def __init__(self, message, line, column):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(str(self))

    def __str__(self):
        return "{} at {}:{}".format(self.message, self.line, self.column)


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Literal:
    raw: str


@dataclass(frozen=True)
class Compare:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Unary:
    op: str
    operand: object


@dataclass(frozen=True)
class Binary:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int


_COMPARISON_OPS = {"==", "!=", "<", ">", "<=", ">="}
_ESCAPES = {
    '"': '"',
    "'": "'",
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}
_HEX_DIGITS = set("0123456789abcdefABCDEF")


def _quote(value):
    result = ['"']
    for char in value:
        if char == '"':
            result.append('\\"')
        elif char == "\\":
            result.append("\\\\")
        elif char == "\n":
            result.append("\\n")
        elif char == "\r":
            result.append("\\r")
        elif char == "\t":
            result.append("\\t")
        elif ord(char) < 0x20:
            result.append("\\u{:04x}".format(ord(char)))
        else:
            result.append(char)
    result.append('"')
    return "".join(result)


class _Tokenizer:
    def __init__(self, text):
        self.text = text
        self.length = len(text)
        self.pos = 0
        self.line = 1
        self.column = 1

    def tokenize(self):
        tokens = []
        while True:
            token = self._next_token()
            tokens.append(token)
            if token.kind == "EOF":
                return tokens

    def _advance(self):
        char = self.text[self.pos]
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _error(self, message, line=None, column=None):
        raise ConditionError(
            message,
            self.line if line is None else line,
            self.column if column is None else column,
        )

    def _next_token(self):
        while self.pos < self.length and self.text[self.pos] in " \t\r\n":
            self._advance()
        if self.pos >= self.length:
            return Token("EOF", "", self.line, self.column)
        line, column = self.line, self.column
        char = self.text[self.pos]

        if char.isalpha() or char == "_":
            start = self.pos
            self._advance()
            while self.pos < self.length:
                current = self.text[self.pos]
                if current.isalnum() or current in "_.":
                    self._advance()
                else:
                    break
            raw = self.text[start : self.pos]
            keyword = raw.upper()
            if keyword in ("AND", "OR", "NOT"):
                return Token(keyword, raw, line, column)
            if keyword == "TRUE":
                return Token("LITERAL", "true", line, column)
            if keyword == "FALSE":
                return Token("LITERAL", "false", line, column)
            return Token("IDENT", raw, line, column)

        if char.isdigit() or (
            char == "-"
            and self.pos + 1 < self.length
            and self.text[self.pos + 1].isdigit()
        ):
            start = self.pos
            if char == "-":
                self._advance()
            while self.pos < self.length and self.text[self.pos].isdigit():
                self._advance()
            if self.pos < self.length and self.text[self.pos] == ".":
                self._advance()
                if self.pos >= self.length or not self.text[self.pos].isdigit():
                    self._error("Expected digit after decimal point")
                while self.pos < self.length and self.text[self.pos].isdigit():
                    self._advance()
            if self.pos < self.length and self.text[self.pos] in "eE":
                self._advance()
                if self.pos < self.length and self.text[self.pos] in "+-":
                    self._advance()
                if self.pos >= self.length or not self.text[self.pos].isdigit():
                    self._error("Expected digit in exponent")
                while self.pos < self.length and self.text[self.pos].isdigit():
                    self._advance()
            return Token("LITERAL", self.text[start : self.pos], line, column)

        if char in "\"'":
            return self._read_string(char, line, column)

        if char == "(":
            self._advance()
            return Token("LPAREN", char, line, column)
        if char == ")":
            self._advance()
            return Token("RPAREN", char, line, column)

        two = self.text[self.pos : self.pos + 2]
        if two in _COMPARISON_OPS:
            self._advance()
            self._advance()
            return Token("OP", two, line, column)
        if char in "<>":
            self._advance()
            return Token("OP", char, line, column)
        if char == "=":
            self._error("Unexpected '='; use '==' for comparison")
        if char == "!":
            self._error("Unexpected '!'; use '!=' for comparison")
        self._error("Unexpected character {!r}".format(char))

    def _read_string(self, quote, line, column):
        self._advance()
        chars = []
        while True:
            if self.pos >= self.length:
                self._error("Unterminated string", line, column)
            char = self._advance()
            if char == quote:
                return Token("LITERAL", _quote("".join(chars)), line, column)
            if char == "\\":
                if self.pos >= self.length:
                    self._error("Unterminated escape sequence")
                escape = self._advance()
                if escape in _ESCAPES:
                    chars.append(_ESCAPES[escape])
                elif escape == "u":
                    digits = self.text[self.pos : self.pos + 4]
                    if len(digits) != 4 or any(d not in _HEX_DIGITS for d in digits):
                        self._error("Invalid \\u escape sequence")
                    for _ in range(4):
                        self._advance()
                    chars.append(chr(int(digits, 16)))
                else:
                    self._error("Invalid escape sequence '\\{}'".format(escape))
            else:
                chars.append(char)


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    @property
    def current(self):
        return self.tokens[self.pos]

    def _error(self, message, token=None):
        token = token or self.current
        raise ConditionError(message, token.line, token.column)

    def parse(self):
        node = self._parse_or()
        if self.current.kind != "EOF":
            self._error("Unexpected token {!r}".format(self.current.value))
        return node

    def _match(self, kind):
        if self.current.kind == kind:
            token = self.current
            self.pos += 1
            return token
        return None

    def _expect(self, kind, message):
        token = self._match(kind)
        if token is None:
            self._error(message)
        return token

    def _parse_or(self):
        node = self._parse_and()
        while self._match("OR"):
            right = self._parse_and()
            node = Binary("OR", node, right)
        return node

    def _parse_and(self):
        node = self._parse_not()
        while self._match("AND"):
            right = self._parse_not()
            node = Binary("AND", node, right)
        return node

    def _parse_not(self):
        if self._match("NOT"):
            return Unary("NOT", self._parse_not())
        return self._parse_primary()

    def _parse_primary(self):
        if self._match("LPAREN"):
            node = self._parse_or()
            self._expect("RPAREN", "Expected ')'")
            return node
        return self._parse_comparison()

    def _parse_comparison(self):
        left = self._parse_operand()
        if self.current.kind == "OP":
            op = self.current.value
            self.pos += 1
            right = self._parse_operand()
            return Compare(op, left, right)
        return left

    def _parse_operand(self):
        token = self.current
        if token.kind == "IDENT":
            self.pos += 1
            return Var(token.value)
        if token.kind == "LITERAL":
            self.pos += 1
            return Literal(token.value)
        self._error("Expected variable, number or string")


_PRECEDENCE = {"OR": 1, "AND": 2}


def _render(node):
    if isinstance(node, Var):
        return node.name
    if isinstance(node, Literal):
        return node.raw
    if isinstance(node, Compare):
        return "{} {} {}".format(_render(node.left), node.op, _render(node.right))
    if isinstance(node, Unary):
        operand = _render(node.operand)
        if isinstance(node.operand, (Binary, Unary, Compare)):
            return "NOT ({})".format(operand)
        return "NOT {}".format(operand)
    if isinstance(node, Binary):
        precedence = _PRECEDENCE[node.op]
        left = _render(node.left)
        right = _render(node.right)
        if isinstance(node.left, Binary) and _PRECEDENCE[node.left.op] < precedence:
            left = "({})".format(left)
        if isinstance(node.right, Binary):
            right_precedence = _PRECEDENCE[node.right.op]
            if right_precedence < precedence or right_precedence == precedence:
                right = "({})".format(right)
        return "{} {} {}".format(left, node.op, right)
    raise TypeError("Unknown AST node: {!r}".format(node))


def parse_condition(text):
    """Разобрать условие в AST."""
    if not isinstance(text, str):
        raise TypeError("parse_condition() expects str")
    tokens = _Tokenizer(text).tokenize()
    return _Parser(tokens).parse()


def render_condition(node):
    """Нормализованное текстовое представление AST."""
    return _render(node)


def normalize_condition(text):
    """Разобрать и нормализовать условие."""
    return render_condition(parse_condition(text))
