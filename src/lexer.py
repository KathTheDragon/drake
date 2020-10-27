import re
from dataclasses import dataclass, field, InitVar
from typing import Iterator

## Constants
ASSIGNMENT = {
    'OP_ADDEQ':     r'\+=',
    'OP_SUBEQ':     r'-=',
    'OP_POWEQ':     r'\*\*=',
    'OP_MULTEQ':    r'\*=',
    'OP_DIVEQ':     r'/=',
    'OP_MODEQ':     r'%=',
    'OP_BITANDEQ':  r'&=',
    'OP_BITXOREQ':  r'^=',
    'OP_BITOREQ':   r'\|=',
    'OP_LSHIFTEQ':  r'<<=',
    'OP_RSHIFTEQ':  r'>>=',
    'OP_ASSIGN':    r'=(?!=)',
}
OP_COMP = {
    'OP_LE':        r'<=',
    'OP_LT':        r'<',
    'OP_GE':        r'>=',
    'OP_GT':        r'>',
    'OP_NE':        r'!=',
    'OP_EQ':        r'==',
}
OPERATORS = {
    'OP_ADD':       r'\+',
    'OP_SUB':       r'-',
    'OP_POW':       r'\*\*',
    'OP_MULT':      r'\*',
    'OP_DIV':       r'/',
    'OP_MOD':       r'%',
    'OP_BITAND':    r'&',
    'OP_BITXOR':    r'^',
    'OP_BITOR':     r'\|',
    'OP_LSHIFT':    r'<<',
    'OP_RSHIFT':    r'>>',
    'OP_INV':       r'!',
    'OP_AND':       r'and',
    'OP_XOR':       r'xor',
    'OP_OR':        r'or',
    'OP_NOT':       r'not',
    'OP_IS':        r'is',
    'OP_IN':        r'in',
} | OP_COMP
KEYWORDS = {
    'KW_AS':        r'as',
    'KW_CASE':      r'case',
    'KW_CATCH':     r'catch',
    'KW_CONST':     r'const',
    'KW_DO':        r'do',
    'KW_ELSE':      r'else',
    'KW_ENUM':      r'enum',
    'KW_EXCEPTION': r'exception',
    'KW_FLAGS':     r'flags',
    'KW_FOR':       r'for',
    'KW_FROM':      r'from',
    'KW_IF':        r'if',
    'KW_ITER':      r'iter',
    'KW_MODULE':    r'module',
    'KW_MUTABLE':   r'mutable',
    'KW_OBJECT':    r'object',
    'KW_THEN':      r'then',
    'KW_THROW':     r'throw',
    'KW_TRY':       r'try',
    'KW_WHILE':     r'while',
    'KW_YIELD':     r'yield',
}
LITERALS = {
    'BOOLEAN':      r'true|false',
    'NONE':         r'none',
    'BREAK':        r'break',
    'CONTINUE':     r'continue',
    'PASS':         r'pass',
    'STRING':       r'\'(?:[^\\\n]|\\.)*?\'|\"(?:[^\\\n]|\\.)*?\"',
    'BINARY':       r'0b(?:_?[01])+',
    'OCTAL':        r'0o(?:_?[0-7])+',
    'HEXADECIMAL':  r'0x(?:_?[\da-fA-F])+',
    'DECIMAL':      r'\d(?:_?\d)*(?:\.\d(?:_?\d)*)?(?:[eE][+-]?\d(?:_?\d)*)?[jJ]?',
}
TOKENS = {
    'BLANK':        r'(?://.*$|/\*(?:.|[\r\n])*?\*/|\s)+',
    'LAMBDA':       r'->',
    'RANGE':        r'\.\.',
    'DOT':          r'\.',
    'COMMA':        r',',
    'COLON':        r':',
    'LBRACKET':     r'\(',
    'LSQUARE':      r'\[',
    'LBRACE':       r'\{',
    'RBRACKET':     r'\)',
    'RSQUARE':      r'\]',
    'RBRACE':       r'\}',
} | ASSIGNMENT | OPERATORS | KEYWORDS | LITERALS | {
    'IDENTIFIER':   r'[a-zA-Z_]\w*[!?]?',
    'UNKNOWN':      r'.'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()), re.M)

## Classes
@dataclass
class Token:
    kind: str
    value: str
    linenum: int = field(default=-1, compare=False)
    column: int = field(default=-1, compare=False)

    def __iter__(self):
        yield self.kind
        yield self.value

EOF = Token('EOF', 'eof')

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
        elif type in ('BINARY', 'OCTAL', 'HEXADECIMAL', 'DECIMAL'):
            type = 'NUMBER'
        yield Token(type, value, linenum, column)
    yield Token('EOF', 'eof', linenum, match.end())
