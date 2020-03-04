import contextlib, re
from dataclasses import dataclass, field
from typing import Any
from .parsetree2 import *

## Tokens
WHITESPACE = re.compile(r'[^\S\r\n]*')
COMMENT = re.compile('//.*$')
NEWLINE = re.compile(r'\r\n?|\n')
EOF = re.compile(r'$(?![\r\n])')
IDENTIFIER = re.compile(r'[a-zA-Z_]\w*[!?]?')
_STRING = r'(?:[^\\\n]|\\.)*?'
STRING = re.compile(fr'\'{STRING}\'|\"{STRING}\"')
NUMBER = re.compile(r'(?:0|[1-9]\d*)(?:\.\d*[1-9])?j?')

AUGMENTED_ASSIGNMENT = '|= ^= &= <<= >>= += -= *= /= %= **='.split()

## Exceptions
class ParseFailed(Exception):
    'Exception to signify a parse attempt failed and backtracking should occur'

class InvalidSyntax(Exception):
    def __init__(self, error, parser):
        linenum, column = parser.linenum, parser.column
        self.message = f'{error} @ {linenum}:{column}'
        self.linenum = linenum
        self.column = column

    def __str__(self):
        return self.message

def Expected(expected, parser):
    error = f'expected {expected}, got {parser.source[parser.cursor]}'
    return InvalidSyntax(error, parser)

## Context managers
OPTIONAL = contextlib.suppress(InvalidSyntax)

## Classes
@dataclass
class Parser:
    source: str
    cursor: int = 0
    linenum: int = 0
    column: int = 0
    parsed: Any = None

    def __iter__(parser):
        return parser, parser.parsed

    def _with(parser, cursor=None, linenum=None, column=None, parsed=None):
        if cursor is None:
            cursor = parser.cursor
        if linenum is None:
            linenum = parser.linenum
        if column is None:
            column = parser.column
        if parsed is None:
            parsed = parser.parsed
        return Parser(parser.source, cursor, linenum, column, parsed)

    # Basic matching methods
    def raw_match(parser, pattern, text, parse=False):
        match = pattern.match(parser.source, parser.cursor)
        if match is None:
            raise Expected(text, parser)
        cursor = match.end()
        column = parser.column + (cursor - parser.cursor)
        if parse:
            return parser._with(cursor=cursor, column=column, parsed=match.group())
        else:
            return parser._with(cursor=cursor, column=column)

    def skip(parser):
        with OPTIONAL:
            parser = parser.raw_match(WHITESPACE, 'whitespace')
        with OPTIONAL:
            parser = parser.raw_match(COMMENT, 'comment')
        return parser

    def match(parser, pattern, text='', parse=False):
        if isinstance(pattern, str):
            text = text or pattern
            pattern = re.compile(re.escape(pattern))
        return parser.raw_match(pattern, text, parse).skip()

    def newline(parser):
        parser = parser.match(NEWLINE, 'newline')._with(linenum=parser.linenum+1, column=0)
        with OPTIONAL:
            parser = parser.newline()
        return parser

    def choices(parser, *tokens, parse=False):
        exception = ValueError('items cannot be empty')
        for token in tokens:
            try:
                return parser.match(token, parse=parse)
            except InvalidSyntax as e:
                exception = e
        raise exception

    # Generic matching methods
    def nodelist(parser, item):
        with OPTIONAL:
            parser = parser.newline()
        parser, _item = item(parser)
        try:
            items = []
            try:
                while True:
                    parser, _item = item(parser.newline())
                    items.append(_item)
            except InvalidSyntax:
                if not items:
                    raise
        except InvalidSyntax:
            items = []
            with OPTIONAL:
                while True:
                    _parser = parser.match(',')
                    with OPTIONAL:
                        _parser = _parser.newline()
                    parser, _item = item(_parser)
                    items.append(_item)
            with OPTIONAL:
                parser = parser.match(',')
        with OPTIONAL:
            parser = parser.newline()
        return parser._with(parsed=[item]+items])

    def leftrecurse(parser, operators, operand):
        parser, left = operand(parser)
        with OPTIONAL:
            while True:
                _parser, op = parser.choices(*operators, parse=True)
                parser, right = operand(_parser)
                left = BinaryOpNode(left, op, right)
        return parser._with(parsed=left)

    def rightrecurse(parser, operators, operand):
        parser, left = operand(parser)
        with OPTIONAL:
            _parser, op = parser.choices(*operators, parse=True)
            parser, right = _parser.rightrecurse(operators, operand)
            left = BinaryOpNode(left, op, right)
        return parser._with(parsed=left)

    # Node matching methods
    def program(parser):
        return BlockNode(parser.nodelist(Parser.declaration).raw_match(EOF, 'eof').parsed)

    def declaration(parser):
        try:
            _parser, typehint = parser.typehint()
            _parser, name = _parser.identifier()
            return _parser._with(parsed=DeclarationNode(typehint, name))
        except InvalidSyntax:
            return parser.assignment()

    def typehint(parser):
        return parser.match('<').type().match('>')

    def type(parser):
        parser, type = parser.identifier()
        with OPTIONAL:
            parser, params = parser.match('[').nodelist(Parser.type).match(']')
            type = TypeNode(type, params)
        return parser._with(parsed=type)

    def assignment(parser):
        try:
            try:
                _parser, targets = parser.match('(').nodelist(Parser.target).match(')')
            except InvalidSyntax:
                _parser, target = parser.target()
                targets = [target]
            _parser, value = _parser.match('=').assignment()
            return _parser._with(parsed=AssignmentNode(targets, value))
        except InvalidSyntax:
            try:
                _parser, target = parser.target()
                _parser, op = _parser.choices(*AUGMENTED_ASSIGNMENT, parse=True)
                _parser, value = _parser.assignment()
                value = BinaryOpNode(target, op.rstrip('='), value)
                return _parser._with(parsed=AssignmentNode(targets, value))
            except InvalidSyntax:
                return parser.expression()

    def target(parser):
        mode = ''
        with OPTIONAL:
            parser, mode = parser.choices('nonlocal', 'const', parse=True)
        parser, name = parser.identifier()
        return parser._with(parsed=Target(mode, name))
