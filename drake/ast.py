import enum
from dataclasses import dataclass, field
from typing import List
from .lexer import Token

## Helper functions
def indent(string):
    return '\n'.join('  '+line for line in string.splitlines())

def pprint(name, *args, inline=False):
    if inline:
        return f'{name} ( {', '.join(args)} )'
    else:
        return f'{name} (\n{',\n'.join(args)}\n)'

## Enums
class Types(enum.Enum):
    INVALID = enum.auto()

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
class LiteralNode(PrimaryNode):
    value: Token

@dataclass
class IdentifierNode(PrimaryNode):
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
        name = f'Unary {self.operator.value}'
        operand = self.operand.pprint()
        inline = isinstance(self.operand, PrimaryNode)
        return pprint(name, operand, inline=inline)

@dataclass
class BinaryOpNode(ASTNode):
    left: ASTNode
    operator: Token
    right: ASTNode

    def pprint(self):
        name = f'Binary {self.operator.value}'
        left = self.left.pprint()
        right = self.right.pprint()
        inline = isinstance(self.left, PrimaryNode) and isinstance(self.right, PrimaryNode)
        return pprint(name, *args, inline=inline)

@dataclass
class AssignmentNode(ASTNode):
    target: ASTNode
    expression: ASTNode

    def pprint(self):
        target = self.target.pprint()
        expression = self.expression.pprint()
        inline = isinstance(self.target, PrimaryNode) and isinstance(self.expression, PrimaryNode)
        return pprint('Assign', target, expression, inline=inline)

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
