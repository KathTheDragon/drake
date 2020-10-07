import re
from dataclasses import dataclass

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
    'finally',
    'flags',
    'for',
    'from',
    'if',
    'iter',
    'module',
    'mutable',
    'nonlocal',
    'object',
    'pass',
    'return',
    'self',
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
    'LBRACKET': r'[([{]',
    'RBRACKET': r'[}\])]',
    'OPERATOR': r'(?:[-+/%&|^!=]|[*<>]{1,2})=?',
    'IDENTIFIER': r'[a-zA-Z_]\w*[!?]?',
    'STRING': r'\'(?:[^\\\n]|\\.)*?\'|\"(?:[^\\\n]|\\.)*?\"',
    'BINARY': r'0b(?:_?[01])+',
    'OCTAL': r'0o(?:_?[0-7])+',
    'HEXADECIMAL': r'0x(?:_?[\da-fA-F])+',
    'DECIMAL': r'\d(?:_?\d)*(?:\.\d(?:_?\d)*)?(?:[eE][+-]?\d(?:_?\d)*)?[jJ]?',
    'UNKNOWN': r'.+?'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()), re.M)

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
    linenum = 1
    for match in TOKEN_REGEX.finditer(source):
        type = match.lastgroup
        value = match.group()
        column = match.start()
        if type == 'BLANK':
            newlines = len(f'{value} '.splitlines()) - 1
            if newlines:
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
