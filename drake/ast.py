import enum
from dataclasses import dataclass
from typing import List
from .lexer import Token

class ASTNode():
    def pprint(self):
        raise NotImplementedError

# Deprecate Primary in favour of Literal and Identifier
@dataclass
class Primary(ASTNode):
    value: Token

    def pprint(self):
        return f'{self.value.type} {self.value.value}'

@dataclass
class Literal(ASTNode):
    value: Token

@dataclass
class Identifier(ASTNode):
    name: Token
    local: bool = True

@dataclass
class UnaryOp(ASTNode):
    operand: ASTNode
    operator: Token

@dataclass
class BinaryOp(ASTNode):
    left: ASTNode
    operator: Token
    right: ASTNode

    def pprint(self):
        indent = lambda s: '\n'.join('  '+line for line in s.splitlines())
        left = self.left.pprint()
        right = self.right.pprint()
        br = ''
        if not (type(self.left) == type(self.right) == Primary):
            left = indent(left)
            right = indent(right)
            br = '\n'
        return f'Binary {self.operator.value} ({br}{left},{br}{right}{br})'

@dataclass
class Assignment(ASTNode):
    name: Token
    expression: ASTNode
    local: bool = True

@dataclass
class Block(ASTNode):
    expressions: List[ASTNode]

    def __iter__(self):
        yield from self.expressions

class Precedence(enum.IntEnum):
    NONE       = enum.auto()
    ASSIGNMENT = enum.auto()   # -> = += -= *= /=
    OR         = enum.auto()   # boolean or
    XOR        = enum.auto()   # boolean xor
    AND        = enum.auto()   # boolean and
    EQUALITY   = enum.auto()   # == != in is
    COMPARISON = enum.auto()   # < > <= >=
    RANGE      = enum.auto()   # ..
    BIT_OR     = enum.auto()   # bitwise |
    BIT_XOR    = enum.auto()   # bitwise ^
    BIT_AND    = enum.auto()   # bitwise &
    SHIFT      = enum.auto()   # >> <<
    ADD        = enum.auto()   # + -
    MULT       = enum.auto()   # * /
    EXP        = enum.auto()   # **
    UNARY      = enum.auto()   # ! -
    CALL       = enum.auto()   # . () []
    PRIMARY    = enum.auto()
