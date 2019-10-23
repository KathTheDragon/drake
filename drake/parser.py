from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Tuple, Union
from .ast import *
from .ast import Precedence
from .lexer import Token

## Constants
EOF = Token('EOF', '', -1, 0)
LITERAL = (
    'STRING',
    'INTEGER',
    'DECIMAL',
    'IMAG_INTEGER',
    'IMAG_DECIMAL',
    'BOOLEAN',
    'NONE'
)
Values = Union[str, Tuple[str]]

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

    # Basic token functions
    def advance(self) -> None:
        self.current = self.next
        try:
            self.next = next(self.tokens)
        except StopIteration:
            self.next = EOF

    def matches(self, type: Values, value: Values=()) -> bool:
        if isinstance(type, str):
            if self.current.type != type:
                return False
        else:
            if self.current.type not in type:
                return False
        if isinstance(value, str):
            return self.current.value == value
        elif values:
            return self.current.value in value
        else:
            return True

    def consume(self, type: Values, value: Values) -> None:
        if self.matches(type, value):
            self.advance()
        else:
            raise expectedToken(value, self.current)

    # Pattern functions
    def leftassoc(self, func: Callable, operator: Values) -> ASTNode:
        expr = func()
        while self.matches('OPERATOR', operator):
            op = self.current
            self.advance()
            right = func()
            expr = BinaryOpNode(expr, op, right)
        return expr

    def rightassoc(self, func: Callable, operator: Values) -> ASTNode:
        expr = func()
        if not self.matches('OPERATOR', operator):
            return expr
        op = self.current
        self.advance()
        right = self.rightassoc(func, operator)
        return BinaryOpNode(expr, op, right)

