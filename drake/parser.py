from dataclasses import dataclass, field
from typing import Iterator, List, Tuple, Union
from .ast import *
from .ast import Precedence
from .lexer import Token

## Constants
EOF = Token('EOF', '', -1, 0)

## Exceptions
class DrakeSyntaxError(Exception):
    def __init__(self, error, token):
        value = token.value
        linenum = token.linenum
        column = token.column
        super().__init__(f'{error}: {value} @ {linenum}:{column}')
        self.error = error
        self.value = value
        self.linenum = linenum
        self.column = column

def expectedToken(expected, token):
    return DrakeSyntaxError(f'expected {expected}', token)

def unexpectedToken(token):
    return DrakeSyntaxError('unexpected token', token)

class DrakeCompilerWarning(Warning):
    def __init__(self, warning, token):
        value = token.value
        linenum = token.linenum
        column = token.column
        super().__init__(f'{warning}: {value} @ {linenum}:{column}')
        self.warning = warning
        self.value = value
        self.linenum = linenum
        self.column = column

## Classes
@dataclass
class DescentParser:
    self: Iterator[Token]
    current: Token = field(init=False)
    next: Token = field(init=False, default=EOF)
    ast: BlockNode = field(init=False)
    log: List[Exception] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self.advance()
        self.advance()
        self.ast = self.parse()

    def advance(self) -> None:
        self.current = self.next
        try:
            self.next = next(self.tokens)
        except StopIteration:
            self.next = EOF

    def matches(self, type: str, value: Union[str, Tuple[str]]=()) -> bool:
        if self.current.type != type:
            return False
        if isinstance(value, str):
            return self.current.value == value
        else:
            return self.current.value in value

    def consume(self, type: str, value: Union[str, Tuple[str]]) -> None:
        if self.matches(type, value):
            self.advance()
        else:
            raise expectedToken(value, self.current)

