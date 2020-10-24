import re
from dataclasses import dataclass, field, InitVar
from typing import Iterator

## Constants
KEYWORDS = [
    'as',
    'break',
    'case',
    'catch',
    'const',
    'continue',
    'do',
    'else',
    'enum',
    'exception',
    'flags',
    'for',
    'from',
    'if',
    'iter',
    'module',
    'mutable',
    'object',
    'pass',
    'then',
    'throw',
    'while',
    'yield',
]
KEYWORD_OPERATORS = [
    'and',
    'in',
    'is',
    'not',
    'or',
    'xor',
]
TOKENS = {
    'BLANK': r'(?://.*$|/\*(?:.|[\r\n])*?\*/|\s)+',
    'LAMBDA': r'->',
    'RANGE': r'\.\.',
    'DOT': r'\.',
    'COMMA': r',',
    'COLON': r':',
    'LBRACKET': r'\(',
    'LSQUARE': r'\[',
    'LBRACE': r'\{',
    'RBRACKET': r'\)',
    'RSQUARE': r'\]',
    'RBRACE': r'\}',
    'OPERATOR': r'(?:[-+/%&|^!=]|[*<>]{1,2})=?',
    'IDENTIFIER': r'[a-zA-Z_]\w*[!?]?',
    'STRING': r'\'(?:[^\\\n]|\\.)*?\'|\"(?:[^\\\n]|\\.)*?\"',
    'BINARY': r'0b(?:_?[01])+',
    'OCTAL': r'0o(?:_?[0-7])+',
    'HEXADECIMAL': r'0x(?:_?[\da-fA-F])+',
    'DECIMAL': r'\d(?:_?\d)*(?:\.\d(?:_?\d)*)?(?:[eE][+-]?\d(?:_?\d)*)?[jJ]?',
    'UNKNOWN': r'.'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()), re.M)

## Classes
@dataclass
class Token:
    kind: str
    value: str
    linenum: int
    column: int

    def __iter__(self):
        yield self.kind
        yield self.value

EOF = Token('EOF', 'eof', -1, -1)

@dataclass
class Lexer:
    source: InitVar[str]
    _nexttoken: Token = field(init=False, default=None)
    _tokens: Iterator[Token] = field(init=False)

    def __post_init__(self, source):
        self.EOF = EOF
        self._tokens = lex(source)
        self._next()

    def _next(self):
        token = self._nexttoken
        self._nexttoken = next(self._tokens, self.EOF)
        if self._nexttoken.kind == 'EOF':
            self.EOF = self._nexttoken
        if token.kind in ('LBRACKET', 'LSQUARE', 'LBRACE', 'COMMA'):
            if self._nexttoken.kind == 'NEWLINE':
                self._next()
        return token

    def _peek(self):
        return self._nexttoken

## Functions
def lex(source):
    linenum = 1
    for match in TOKEN_REGEX.finditer(source):
        type = match.lastgroup
        value = match.group()
        column = match.start()
        if type == 'BLANK':
            newlines = len(f'{value} '.splitlines()) - 1
            if newlines:
                # To-do: suppress newlines after commas and open brackets, and
                # before close brackets
                yield Token('NEWLINE', 'nl', linenum, column)
                linenum += newlines
            continue
        elif type == 'OPERATOR':
            if value.endswith('=') and value not in ('<=', '>=', '==', '!='):
                type = 'ASSIGNMENT'
        elif type == 'IDENTIFIER':
            if value in KEYWORDS:
                type = 'KEYWORD'
            elif value in KEYWORD_OPERATORS:
                type = 'OPERATOR'
            elif value in ('true', 'false'):
                type = 'BOOLEAN'
            elif value == 'none':
                type = 'NONE'
        elif type in ('BINARY', 'OCTAL', 'HEXADECIMAL', 'DECIMAL'):
            type = 'NUMBER'
        yield Token(type, value, linenum, column)
    yield Token('EOF', 'eof', linenum, match.end())
