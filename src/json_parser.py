"""Небольшой JSON-парсер, написанный с нуля.

Поддерживаются все типы JSON, escape-последовательности (включая
суррогатные пары), ограничение глубины вложенности и ошибки с позицией.
Стандартный модуль json намеренно не используется.
"""

from __future__ import annotations

import sys

MAX_DEPTH = 512
_WHITESPACE = " \t\r\n"
_HEX_DIGITS = set("0123456789abcdefABCDEF")
_SIMPLE_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


class JSONParseError(ValueError):
    """Ошибка разбора JSON с указанием строки и столбца (1-based)."""

    def __init__(self, message, line, column):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(str(self))

    def __str__(self):
        return "{} at {}:{}".format(self.message, self.line, self.column)


class _Parser:
    def __init__(self, text, max_depth):
        self.text = text
        self.length = len(text)
        self.pos = 0
        self.line = 1
        self.column = 1
        self.max_depth = max_depth

    def parse(self):
        self._skip_whitespace()
        if self.pos >= self.length:
            self._error("Unexpected end of input")
        value = self._parse_value(0)
        self._skip_whitespace()
        if self.pos < self.length:
            self._error("Unexpected character {!r}".format(self.text[self.pos]))
        return value

    def _advance(self):
        char = self.text[self.pos]
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _skip_whitespace(self):
        while self.pos < self.length and self.text[self.pos] in _WHITESPACE:
            self._advance()

    def _error(self, message, line=None, column=None):
        raise JSONParseError(
            message,
            self.line if line is None else line,
            self.column if column is None else column,
        )

    def _parse_value(self, depth):
        self._skip_whitespace()
        if self.pos >= self.length:
            self._error("Unexpected end of input")
        char = self.text[self.pos]
        if char == "{":
            if depth + 1 > self.max_depth:
                self._error("Maximum nesting depth of {} exceeded".format(self.max_depth))
            return self._parse_object(depth + 1)
        if char == "[":
            if depth + 1 > self.max_depth:
                self._error("Maximum nesting depth of {} exceeded".format(self.max_depth))
            return self._parse_array(depth + 1)
        if char == '"':
            return self._parse_string()
        if char == "-" or char.isdigit():
            return self._parse_number()
        if self.text.startswith("true", self.pos):
            self._consume_literal("true")
            return True
        if self.text.startswith("false", self.pos):
            self._consume_literal("false")
            return False
        if self.text.startswith("null", self.pos):
            self._consume_literal("null")
            return None
        self._error("Unexpected character {!r}".format(char))

    def _consume_literal(self, literal):
        for _ in literal:
            self._advance()

    def _parse_object(self, depth):
        self._advance()  # {
        result = {}
        self._skip_whitespace()
        if self.pos < self.length and self.text[self.pos] == "}":
            self._advance()
            return result
        while True:
            self._skip_whitespace()
            if self.pos >= self.length:
                self._error("Unterminated object")
            if self.text[self.pos] != '"':
                self._error("Expected property name in double quotes")
            key = self._parse_string()
            self._skip_whitespace()
            if self.pos >= self.length or self.text[self.pos] != ":":
                self._error("Expected ':' after property name")
            self._advance()  # :
            result[key] = self._parse_value(depth)
            self._skip_whitespace()
            if self.pos >= self.length:
                self._error("Unterminated object")
            char = self.text[self.pos]
            if char == ",":
                self._advance()
                self._skip_whitespace()
                if self.pos < self.length and self.text[self.pos] == "}":
                    self._error("Trailing comma in object")
                continue
            if char == "}":
                self._advance()
                return result
            self._error("Expected ',' or '}' in object")

    def _parse_array(self, depth):
        self._advance()  # [
        result = []
        self._skip_whitespace()
        if self.pos < self.length and self.text[self.pos] == "]":
            self._advance()
            return result
        while True:
            result.append(self._parse_value(depth))
            self._skip_whitespace()
            if self.pos >= self.length:
                self._error("Unterminated array")
            char = self.text[self.pos]
            if char == ",":
                self._advance()
                self._skip_whitespace()
                if self.pos < self.length and self.text[self.pos] == "]":
                    self._error("Trailing comma in array")
                continue
            if char == "]":
                self._advance()
                return result
            self._error("Expected ',' or ']' in array")

    def _parse_string(self):
        self._advance()  # opening quote
        chars = []
        while True:
            if self.pos >= self.length:
                self._error("Unterminated string")
            char = self._advance()
            if char == '"':
                return "".join(chars)
            if char == "\\":
                if self.pos >= self.length:
                    self._error("Unterminated escape sequence")
                escape = self._advance()
                if escape in _SIMPLE_ESCAPES:
                    chars.append(_SIMPLE_ESCAPES[escape])
                elif escape == "u":
                    chars.append(self._parse_unicode_escape())
                else:
                    self._error("Invalid escape sequence '\\{}'".format(escape))
            else:
                if ord(char) < 0x20:
                    self._error("Unescaped control character in string")
                chars.append(char)

    def _parse_unicode_escape(self):
        code = self._read_hex4()
        if 0xD800 <= code <= 0xDBFF:
            saved_pos = self.pos
            saved_line = self.line
            saved_column = self.column
            if (
                self.pos + 1 < self.length
                and self.text[self.pos] == "\\"
                and self.text[self.pos + 1] == "u"
            ):
                self._advance()
                self._advance()
                low = self._read_hex4()
                if 0xDC00 <= low <= 0xDFFF:
                    return chr(0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00))
                self.pos = saved_pos
                self.line = saved_line
                self.column = saved_column
            return chr(code)
        return chr(code)

    def _read_hex4(self):
        if self.pos + 4 > self.length:
            self._error("Incomplete \\u escape sequence")
        digits = self.text[self.pos : self.pos + 4]
        if any(digit not in _HEX_DIGITS for digit in digits):
            self._error("Invalid \\u escape sequence")
        for _ in range(4):
            self._advance()
        return int(digits, 16)

    def _parse_number(self):
        start = self.pos
        is_float = False
        if self.text[self.pos] == "-":
            self._advance()
            if self.pos >= self.length:
                self._error("Invalid number")
        if self.pos >= self.length:
            self._error("Invalid number")
        char = self.text[self.pos]
        if char == "0":
            self._advance()
            if self.pos < self.length and self.text[self.pos].isdigit():
                self._error("Leading zeros are not allowed")
        elif "1" <= char <= "9":
            self._advance()
            while self.pos < self.length and self.text[self.pos].isdigit():
                self._advance()
        else:
            self._error("Invalid number")
        if self.pos < self.length and self.text[self.pos] == ".":
            is_float = True
            self._advance()
            if self.pos >= self.length or not self.text[self.pos].isdigit():
                self._error("Expected digit after decimal point")
            while self.pos < self.length and self.text[self.pos].isdigit():
                self._advance()
        if self.pos < self.length and self.text[self.pos] in "eE":
            is_float = True
            self._advance()
            if self.pos < self.length and self.text[self.pos] in "+-":
                self._advance()
            if self.pos >= self.length or not self.text[self.pos].isdigit():
                self._error("Expected digit in exponent")
            while self.pos < self.length and self.text[self.pos].isdigit():
                self._advance()
        raw = self.text[start : self.pos]
        try:
            return float(raw) if is_float else int(raw)
        except ValueError:
            self._error("Invalid number")


def parse_json(text, max_depth=MAX_DEPTH):
    """Разобрать строку JSON и вернуть Python-значение.

    Глубина вложенности ограничена ``max_depth`` (по умолчанию 512).
    """

    if not isinstance(text, str):
        raise TypeError("parse_json() expects str, got {}".format(type(text).__name__))
    if text.startswith("\ufeff"):
        text = text[1:]
    old_limit = sys.getrecursionlimit()
    required_limit = max(old_limit, max_depth * 6 + 1000)
    if required_limit != old_limit:
        sys.setrecursionlimit(required_limit)
    try:
        return _Parser(text, max_depth).parse()
    finally:
        if required_limit != old_limit:
            sys.setrecursionlimit(old_limit)
