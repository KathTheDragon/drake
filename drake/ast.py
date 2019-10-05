import enum
from dataclasses import dataclass, field
from typing import List, Optional
from .lexer import Token

## Helper functions
def indent(string):
    return '\n'.join('  '+line for line in string.splitlines())

def isprimary(*nodes):
    return all(isinstance(node, (PrimaryNode, str)) for node in nodes)

def pprint(name, *args):
    argstrings = [(arg.pprint() if isinstance(arg, ASTNode) else arg) for arg in args]
    if isprimary(*args):
        return f'{name} (\n{',\n'.join((indent(arg) for arg in argstrings))}\n)'
    else:
        return f'{name} ( {', '.join(argstrings)} )'

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
        return f'{self.value.type.capitalise()} {self.value.value}'

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
        return pprint(f'Unary {self.operator.value}', self.operand)

@dataclass
class BinaryOpNode(ASTNode):
    left: ASTNode
    operator: Token
    right: ASTNode

    def pprint(self):
        return pprint(f'Binary {self.operator.value}', self.left, self.right)

@dataclass
class SubscriptNode(ASTNode):
    container: ASTNode
    subscript: ASTNode

    def pprint(self):
        return pprint('Subscript', self.container, self.subscript)

@dataclass
class AttrLookupNode(ASTNode):
    obj: ASTNode
    attribute: IdentifierNode

    def pprint(self):
        return pprint('AttrLookup', self.obj, self.attribute)

class KeywordNode(ASTNode):
    expression: ASTNode

    def pprint(self):
        name = self.__class__.__name__[:-4]
        return pprint(name, self.expression)

class KeywordOptionalNode(KeywordNode):
    expression: Optional[ASTNode]

    def pprint(self):
        if expression is None:
            return self.__class__.__name__[:-4]
        else:
            return super().pprint()

class IterNode(KeywordNode):
    pass

class ReturnNode(KeywordOptionalNode):
    pass

class BreakNode(KeywordOptionalNode):
    pass

class ContinueNode(KeywordOptionalNode):
    pass

class YieldNode(KeywordNode):
    pass

class YieldFromNode(KeywordNode):
    pass

@dataclass
class LambdaNode(ASTNode):
    params: List[Token]
    returns: ASTNode

    def pprint(self):
        name = self.__class__.__name__[:-4]
        params = ', '.join(param.value for param in self.params) or '()'
        if ',' in params:
            params = f'({params})'
        return pprint(name, params, self.returns)

@dataclass
class AssignmentNode(ASTNode):
    target: ASTNode
    expression: ASTNode

    def pprint(self):
        return pprint('Assign', self.target, self.expression)

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
        if self.default is None:  # No else
            return pprint('Case', self.var, self.cases)
        else:
            return pprint('Case', self.var, self.cases, self.default)

class IfNode(ASTNode):
    condition: ASTNode
    then: ASTNode
    default: Optional[ASTNode]

    def pprint(self):
        if self.default is None:  # No else
            return pprint('If', self.condition, self.then)
        else:
            return pprint('If', self.condition, self.then, self.default)

class ForNode(ASTNode):
    vars: List[Tokens]
    container: ASTNode
    body: BlockNode

    def pprint(self):
        vars = ', '.join(vars.value for var in self.vars) or '()'
        return pprint('For', vars, self.container, self.body)

class WhileNode(ASTNode):
    condition: ASTNode
    body: BlockNode

    def pprint(self):
        return pprint('While', self.condition, self.body)

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
