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
class Literal(Primary):
    value: Token

@dataclass
class Identifier(Primary):
    value: Token
    local: bool = True

@dataclass
class UnaryOp(ASTNode):
    operator: Token
    operand: ASTNode

    def pprint(self):
        indent = lambda s: '\n'.join('  '+line for line in s.splitlines())
        if isinstance(self.operand, Primary):
            return f'Unary {self.operator.value} ({self.operand.pprint()})'
        else:
            return f'Unary {self.operator.value} (\n{indent(self.operand.pprint())}\n)'

@dataclass
class BinaryOp(ASTNode):
    left: ASTNode
    operator: Token
    right: ASTNode

    def pprint(self):
        indent = lambda s: '\n'.join('  '+line for line in s.splitlines())
        left = self.left.pprint()
        right = self.right.pprint()
        if isinstance(self.left, Primary) and isinstance(self.right, Primary):
            return f'Binary {self.operator.value} ({left}, {right})'
        else:
            return f'Binary {self.operator.value} (\n{indent(left)},\n{indent(right)}\n)'

@dataclass
class Assignment(ASTNode):
    target: ASTNode
    expression: ASTNode
    local: bool = True

    def pprint(self):
        indent = lambda s: '\n'.join('  '+line for line in s.splitlines())
        target = self.target.pprint()
        expression = self.expression.pprint()
        if isinstance(self.target, Primary) and isinstance(self.expression, Primary):
            return f'Assign ({target}, {expression})'
        else:
            return f'Assign (\n{indent(target)},\n{indent(expression)}\n)'

@dataclass
class Block(ASTNode):
    expressions: List[ASTNode]

    def __iter__(self):
        yield from self.expressions

    def pprint(self):
        indent = lambda s: '\n'.join('  '+line for line in s.splitlines())
        return '{\n' + '\n'.join(indent(node.pprint()) for node in self) + '\n}'
            

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
