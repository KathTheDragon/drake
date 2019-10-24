import re
from dataclasses import dataclass

## Constants
KEYWORDS = [
    'break',
    'case',
    'class',
    'const',
    'continue',
    'del',
    'else',
    'exception',
    'false',
    'for',
    'if',
    'interface',
    'iter',
    'mutable',
    'none',
    'nonlocal',
    'return',
    'self',
    'then',
    'true',
    'while',
    'yield from',
    'yield',
]
KEYWORD_OPERATORS = [
    'and',
    'in',
    'is not',
    'is',
    'not in',
    'not',
    'or',
    'xor',
]
STRING = r'(?:[^\\\n]|\\.)*?'
INTEGER = r'0|[1-9]\d*'
DECIMAL = r'0|\d*[1-9]'
TOKENS = {
    'COMMENT': r'//.*$',
    'ASSIGNMENT': r'[-+*/]?=(?!=)',
    'LAMBDA': r'->',
    'OPERATOR': fr'[-+/&|^~]|[<>!=]=|[*<>]{{1,2}}|\.\.|(?:{"|".join(KEYWORD_OPERATORS)})(?!\w)',
    'DOT': r'\.',
    'COMMA': r',',
    'COLON': r':',
    'LBRACKET': r'[([{]',
    'RBRACKET': r'[}\])]',
    'KEYWORD': fr'(?:{"|".join(KEYWORDS)})(?!\w)',
    'IDENTIFIER': r'[a-zA-Z_]\w*[!?]?',
    'STRING': fr'\'{STRING}\'|\"{STRING}\"',
    'IMAG_DECIMAL': fr'(?:{INTEGER})\.(?:{DECIMAL})j',
    'IMAG_INTEGER': fr'{INTEGER}j',
    'DECIMAL': fr'(?:{INTEGER})\.(?:{DECIMAL})',
    'INTEGER': INTEGER,
    'WHITESPACE': r'[ \t]+',
    'UNKNOWN': r'.+?'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()))

## Classes
@dataclass
class Token:
    type: str
    value: str
    linenum: int
    column: int

    def __iter__(self):
        yield self.type
        yield self.value

## Functions
def lex(source):
    brackets = []
    for linenum, line in enumerate(source.splitlines()):
        empty = True
        for match in TOKEN_REGEX.finditer(line):
            type = match.lastgroup
            value = match.group()
            column = match.start()
            if type in ('COMMENT', 'WHITESPACE'):
                continue
            empty = False
            if type == 'KEYWORD':
                if value == 'none':
                    type = 'NONE'
                elif value in ('true', 'false'):
                    type = 'BOOLEAN'
            yield Token(type, value, linenum, column)
        if not empty:
            yield Token('NEWLINE', 'nl', linenum, len(line))
    yield Token('EOF', 'eof', linenum+1, 0)
