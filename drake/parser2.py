import contextlib, re
from dataclasses import dataclass, field
from typing import Callable, Generic, Iterator, List, Tuple, TypeVar, Union
from .parsetree import *

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
    parsed: str = None
    parsetree: ParseNode = None

    def __iter__(parser):
        return parser, parser.parsed

    def _with(parser, cursor=None, linenum=None, column=None, parsed=None, parsetree=None):
        if cursor is None:
            cursor = parser.cursor
        if linenum is None:
            linenum = parser.linenum
        if column is None:
            column = parser.column
        if parsed is None:
            parsed = parser.parsed
        if parsetree is None:
            parsetree = parser.parsetree
        return Parser(parser.source, cursor, linenum, column, parsed, parsetree)

    # Basic matching methods
    def raw_match(parser, pattern, text):
        match = pattern.match(parser.source, parser.cursor)
        if match is None:
            raise Expected(text, parser)
        cursor = match.end()
        column = parser.column + (cursor - parser.cursor)
        return parser._with(cursor=cursor, column=column, parsed=match.group())

    def skip(parser):
        with OPTIONAL:
            parser = parser.raw_match(WHITESPACE, 'whitespace')
        with OPTIONAL:
            parser = parser.raw_match(COMMENT, 'comment')
        return parser

    def match(parser, pattern, text=''):
        if isinstance(pattern, str):
            text = text or pattern
            pattern = re.compile(re.escape(pattern))
        parser, value = parser.raw_match(pattern, text)
        return parser.skip()._with(parsed=value)

    def newline(parser):
        parser = parser.match(NEWLINE, 'newline')._with(linenum=parser.linenum+1, column=0)
        with OPTIONAL:
            parser = parser.newline()
        return parser

    # Generic matching methods
    def nodelist(parser, item):
        with OPTIONAL:
            parser = parser.newline()
        with OPTIONAL:
            items = []
            parser, item = item(parser)
            items.append(item)
            try:
                while True:
                    try:
                        parser, item = item(parser.newline())
                        items.append(item)
                    except InvalidSyntax:
                        break
            except InvalidSyntax:
                while True:
                    try:
                        parser = parser.match(',')
                        with OPTIONAL:
                            parser = parser.newline()
                        parser, item = item(parser)
                        items.append(item)
                    except InvalidSyntax:
                        break
                with OPTIONAL:
                    parser = parser.match(',')
        with OPTIONAL:
            parser = parser.newline()
        return parser._with(parsed=items)
