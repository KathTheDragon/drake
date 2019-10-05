import enum
from dataclasses import dataclass, field
from typing import List
from .lexer import Token

## Helper functions
def indent(string):
    return '\n'.join('  '+line for line in string.splitlines())

class ASTNode:
    type: Types = field(init=False)

    def __post_init__(self):
        self.type = self.getType()

    def getType(self):
        return Type.INVALID

    def pprint(self):
        raise NotImplementedError

# Deprecate Primary in favour of Literal and Identifier
@dataclass
class PrimaryNode(ASTNode):
    value: Token

    def pprint(self):
        return f'{self.value.type} {self.value.value}'

@dataclass
class LiteralNode(Primary):
    value: Token

@dataclass
class IdentifierNode(Primary):
    value: Token
    local: bool = True

    def pprint(self):
        string = super().pprint()
        if self.local:
            return string
        else:
            return f'nonlocal {string}'

@dataclass
class UnaryOpNode(ASTNode):
    operator: Token
    operand: ASTNode

    def pprint(self):
        if isinstance(self.operand, Primary):
            return f'Unary {self.operator.value} ({self.operand.pprint()})'
        else:
            return f'Unary {self.operator.value} (\n{indent(self.operand.pprint())}\n)'

@dataclass
class BinaryOpNode(ASTNode):
    left: ASTNode
    operator: Token
    right: ASTNode

    def pprint(self):
        left = self.left.pprint()
        right = self.right.pprint()
        if isinstance(self.left, Primary) and isinstance(self.right, Primary):
            return f'Binary {self.operator.value} ({left}, {right})'
        else:
            return f'Binary {self.operator.value} (\n{indent(left)},\n{indent(right)}\n)'

@dataclass
class AssignmentNode(ASTNode):
    target: ASTNode
    expression: ASTNode

    def pprint(self):
        target = self.target.pprint()
        expression = self.expression.pprint()
        if isinstance(self.target, Primary) and isinstance(self.expression, Primary):
            return f'Assign ({target}, {expression})'
        else:
            return f'Assign (\n{indent(target)},\n{indent(expression)}\n)'

@dataclass
class BlockNode(ASTNode):
    expressions: List[ASTNode]

    def __iter__(self):
        yield from self.expressions

    def __len__(self):
        return len(self.expressions)

    def pprint(self):
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
