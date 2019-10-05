import enum
from dataclasses import dataclass, field
from typing import List, Optional
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

## Classes
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
class ListNode(ASTNode):
    items: List[ASTNode]

@dataclass
class TupleNode(ASTNode):
    items: List[ASTNode]

@dataclass
class MapNode(ASTNode):
    items: List[Tuple[ASTNode, ASTNode]]

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
class SubscriptNode(ASTNode):
    container: ASTNode
    subscript: ASTNode

    def pprint(self):
        container = self.container.pprint()
        subscript = self.subscript.pprint()
        inline = isinstance(self.container, PrimaryNode) and isinstance(self.subscript, PrimaryNode)
        return pprint('Subscript', container, subscript, inline=inline)

@dataclass
class AttrLookupNode(ASTNode):
    obj: ASTNode
    attribute: IdentifierNode

    def pprint(self):
        obj = self.obj.pprint()
        attribute = self.attribute.pprint()
        inline = isinstance(self.obj, PrimaryNode)
        return pprint('AttrLookup', obj, attribute, inline=inline)

class IterNode(ASTNode):
    expression: ASTNode

    def pprint(self):
        expression = self.expression.pprint()
        inline = isinstance(self.expression, PrimaryNode)
        return pprint('iter', expression, inline=inline)

class ReturnNode(ASTNode):
    expression: Optional[ASTNode]

    def pprint(self):
        if expression is None:
            return 'return'
        else:
            expression = self.expression.pprint()
            inline = isinstance(self.expression, PrimaryNode)
            return pprint('return', expression, inline=inline)

class BreakNode(ASTNode):
    expression: Optional[ASTNode]

    def pprint(self):
        if expression is None:
            return 'break'
        else:
            expression = self.expression.pprint()
            inline = isinstance(self.expression, PrimaryNode)
            return pprint('break', expression, inline=inline)

class ContinueNode(ASTNode):
    expression: Optional[ASTNode]

    def pprint(self):
        if expression is None:
            return 'continue'
        else:
            expression = self.expression.pprint()
            inline = isinstance(self.expression, PrimaryNode)
            return pprint('continue', expression, inline=inline)

class YieldNode(ASTNode):
    expression: ASTNode

    def pprint(self):
        expression = self.expression.pprint()
        inline = isinstance(self.expression, PrimaryNode)
        return pprint('yield', expression, inline=inline)

class YieldFromNode(ASTNode):
    expression: ASTNode

    def pprint(self):
        expression = self.expression.pprint()
        inline = isinstance(self.expression, PrimaryNode)
        return pprint('yield from', expression, inline=inline)

@dataclass
class LambdaNode(ASTNode):
    params: List[Token]
    returns: ASTNode

    def pprint(self):
        name = self.__class__.__name__[:-4]
        params = ', '.join(param.value for param in self.params) or '()'
        if ',' in params:
            params = f'({params})'
        returns = self.returns.pprint()
        return pprint(name, params, returns)

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

@dataclass
class ClassNode(LambdaNode):
    returns: BlockNode

@dataclass
class InterfaceNode(ASTNode):
    body: BlockNode

    def pprint(self):
        return f'Interface ({self.body.pprint()[1:-1]})'

class ExceptionNode(ClassNode):
    pass

class CaseNode(ASTNode):
    var: IdentifierNode
    cases: MapNode
    default: Optional[ASTNode]

    def pprint(self):
        var = self.var.pprint()
        cases = self.cases.pprint()
        if self.default is None:  # No else
            return pprint('Case', var, cases)
        else:
            default = self.default.pprint()
            return pprint('Case', var, cases, default)

class IfNode(ASTNode):
    condition: ASTNode
    then: ASTNode
    default: Optional[ASTNode]

    def pprint(self):
        condition = self.condition.pprint()
        then = self.then.pprint()
        if self.default is None:  # No else
            return pprint('If', condition, then)
        else:
            default = self.default.pprint()
            return pprint('If', condition, then, default)

class ForNode(ASTNode):
    vars: List[Tokens]
    container: ASTNode
    body: BlockNode

    def pprint(self):
        vars = ', '.join(vars.value for var in self.vars) or '()'
        container = self.container.pprint()
        body = self.body.pprint()
        return pprint('For', vars, container, body)

class WhileNode(ASTNode):
    condition: ASTNode
    body: BlockNode

    def pprint(self):
        condition = self.condition.pprint()
        body = self.body.pprint()
        return pprint('While', condition, body)

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
