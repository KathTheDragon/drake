import re
from dataclasses import dataclass
from .exceptions import DrakeSyntaxError

## Constants
KEYWORDS = [
    'break',
    'case',
    'class',
    'constant',
    'continue',
    'del'
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
STRING = r'([^\\\n]|\\.)*?'
TOKENS = {
    'ASSIGNMENT': r'[-+*/]?=',
    'LAMBDA': r'->',
    'OPERATOR': fr'[-+&|^~:]|[<>!=]=|[*/<>]{{1,2}}|\.\.|(?:{"|".join(KEYWORD_OPERATORS)})(?!\w)',
    'DOT': r'\.',
    'COMMA': r',',
    'LBRACKET': r'[([{]',
    'RBRACKET': r'[}\])]',
    'KEYWORD': fr'(?:{"|".join(KEYWORDS)})(?!\w)',
    'IDENTIFIER': r'[a-zA-Z_]\w*[!?]?',
    'STRING': fr'\'{STRING}\'|\"{STRING}\"',
    'NUMBER': r'\d+(?:\.\d+)?',
    'WHITESPACE': r'[ \t]+',
    'UNKNOWN': r'.'
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
        for match in TOKEN_REGEX.finditer(line):
            type = match.lastgroup
            value = match.group()
            column = match.start()
            if type == 'LBRACKET':
                brackets.append(value)
            elif type == 'RBRACKET':
                if not brackets:
                    raise DrakeSyntaxError(f'unexpected bracket', value, linenum, column)
                bracket = brackets.pop()
                if bracket+value not in ('()', '[]', '{}'):
                    raise DrakeSyntaxError(f'mismatched brackets', value, linenum, column)
            elif type == 'WHITESPACE':
                continue
            elif type == 'UNKNOWN':
                raise DrakeSyntaxError(f'unexpected character', value, linenum, column)
            yield Token(type, value, linenum, column)
        yield Token('NEWLINE', '', linenum, len(line))
