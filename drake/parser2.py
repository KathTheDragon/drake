import contextlib, re
from dataclasses import dataclass, field
from typing import Callable, Generic, Iterator, List, Tuple, TypeVar, Union
from .parsetree import *

## Tokens
WHITESPACE = re.compile(r'[^\S\r\n]*')
COMMENT = re.compile('//.*$')
NEWLINE = re.compile(r'\r\n?|\n')

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
    parsetree: ParseNode = None

    def _with(parser, cursor=None, linenum=None, column=None, parsetree=None):
        if cursor is None:
            cursor = parser.cursor
        if linenum is None:
            linenum = parser.linenum
        if column is None:
            column = parser.column
        if parsetree is None:
            parsetree = parser.parsetree
        return Parser(parser.source, cursor, linenum, column, parsetree)

    # Basic matching methods
    def match_re(parser, pattern, text):
        match = pattern.match(parser.source, parser.cursor)
        if match is None:
            raise Expected(text, parser)
        cursor = match.end()
        column = parser.column + (cursor - parser.cursor)
        return parser._with(cursor=cursor, column=column), match.group()

    def match(parser, token):
        return parser.match_re(re.compile(re.escape(token)), token)

    def skip(parser):
        with OPTIONAL:
            parser, _ = parser.match_re(WHITESPACE, 'whitespace')
        with OPTIONAL:
            parser, _ = parser.match_re(COMMENT, 'comment')
        return parser

    def newline(parser):
        parser, _ = parser.match_re(NEWLINE, 'newline')
        parser = parser._with(linenum=parser.linenum+1, column=0).skip()
        with OPTIONAL:
            parser = parser.newline()
        return parser

    # Generic matching methods
    def nodelist(parser, item):
        with OPTIONAL:
            parser = parser.newline()
        with OPTIONAL:
            try:
                items = []
                parser, item = item(parser)
                items.append(item)
                while True:
                    try:
                        parser, item = item(parser.newline())
                        items.append(item)
                    except InvalidSyntax:
                        break
            except InvalidSyntax:
                items = []
                parser = item(parser)
                items.append(parser.parsed)
                while True:
                    try:
                        parser = parser.match(',')
                        with OPTIONAL:
                            parser = parser.newline()
                        parser = item(parser)
                        items.append(parser.parsed)
                    except InvalidSyntax:
                        break
                with OPTIONAL:
                    parser = parser.match(',')
        with OPTIONAL:
            parser = parser.newline()
