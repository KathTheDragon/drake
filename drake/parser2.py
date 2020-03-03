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

    def choice(parser, *tokens, parse=False):
        for token in tokens:
            try:
                return parser.match(token, parse=parse)
            except InvalidSyntax as e:
                pass
        raise e

    # Generic matching methods
    def nodelist(parser, item):
        with OPTIONAL:
            parser = parser.newline()
        with OPTIONAL:
            items = []
            parser, item = item(parser)
            items.append(item)
            try:
                with OPTIONAL:
                    while True:
                        parser, item = item(parser.newline())
                        items.append(item)
            except InvalidSyntax:
                with OPTIONAL:
                    while True:
                        parser = parser.match(',')
                        with OPTIONAL:
                            parser = parser.newline()
                        parser, item = item(parser)
                        items.append(item)
                with OPTIONAL:
                    parser = parser.match(',')
        with OPTIONAL:
            parser = parser.newline()
        return parser._with(parsed=items)

    def leftrecurse(parser, operators, operand):
        parser, left = operand(parser)
        with OPTIONAL:
            while True:
                parser, op = parser.choice(*operators, parse=True)
                parser, right = operand(parser)
                left = BinaryOpNode(left, op, right)
        return parser._with(parsed=left)

    def rightrecurse(parser, operators, operand):
        parser, left = operand(parser)
        with OPTIONAL:
            parser, op = parser.choice(*operators, parse=True)
            parser, right = parser.rightrecurse(operators, operand)
            left = BinaryOpNode(left, op, right)
        return parser._with(parsed=left)

    # Node matching methods
    def program(parser):
        parser, expressions = parser.nodelist(Parser.declaration).raw_match(EOF, 'eof')
        return BlockNode(expressions)

    def declaration(parser):
        try:
            parser, typehint = parser.typehint()
            parser, name = parser.identifier()
            return parser._with(parsed=DeclarationNode(typehint, name))
        except InvalidSyntax:
            return parser.assignment()

    def typehint(parser):
        parser, type = parser.match('<').type()
        return parser.match('>')._with(parsed=type)

    def type(parser):
        parser, type = parser.identifier()
        with OPTIONAL:
            parser, params = parser.match('[').nodelist(Parser.type).match(']')
            type = TypeNode(type, params)
        return parser._with(parsed=type)

    def assignment(parser):
        try:
            try:
                parser, targets = parser.match('(').nodelist(Parser.target).match(')')
            except InvalidSyntax:
                parser, target = parser.target()
                targets = [target]
            try:
                parser, value = parser.match('=').assignment()
            except InvalidSyntax:
                parser, op = parser.choice(*AUGMENTED_ASSIGNMENT, parse=True)
                op = op.rstrip('=')
                parser, value = parser.assignment()
                value = BinaryOpNode(target, op, value)
            return parser._with(parsed=AssignmentNode(targets, value))
        except InvalidSyntax:
            return parser.expression()
