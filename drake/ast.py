import enum
from dataclasses import dataclass, field
from typing import List, Optional
from .lexer import Token

## Helper functions
def indent(string):
    return '\n'.join('  '+line for line in string.splitlines())

def isprimary(*nodes):
    return all(isinstance(node, (LiteralNode, IdentifierNode, list)) for node in nodes)

def pprint(name, *args):
    argstrings = []
    for arg in args:
        if isinstance(arg, ASTNode):
            argstrings.append(arg.pprint())
        elif isinstance(arg, list):
            argstrings.append(f'({", ".join(item.value for item in arg)})')
        else:
            argstrings.append(arg)
    if isprimary(*args):
        return f'{name} (\n{",\n".join((indent(arg) for arg in argstrings))}\n)'
    else:
        return f'{name} ( {", ".join(argstrings)} )'

## Classes
class ASTNode:
    type: str = field(init=False)

    def __post_init__(self):
        self.type = self.getType()

    def getType(self):
        return ''

    def pprint(self):
        raise NotImplementedError

@dataclass
class LiteralNode(ASTNode):
    value: Token

    def pprint(self):
        return f'{self.value.type.capitalise()} {self.value.value}'

@dataclass
class UnitNode(ASTNode):
    unit: Token

    def pprint(self):
        return {
            'none': 'NoneType none',
            'true': 'Boolean true',
            'false': 'Boolean false',
        }.get(self.unit.value, 'Unknown')

@dataclass
class IdentifierNode(ASTNode):
    name: Token
    local: bool = True

    def pprint(self):
        if self.local:
            return f'Identifier {self.name.value}'
        else:
            return f'nonlocal Identifier {self.name.value}'

@dataclass
class SequenceNode(ASTNode):
    items: List[ASTNode]

    def pprint(self):
        return pprint(self.__class__.__name__[:-4], *self.items)

@dataclass
class ListNode(SequenceNode):
    pass

@dataclass
class TupleNode(SequenceNode):
    pass

@dataclass
class PairNode(ASTNode):
    name: ASTNode
    value: ASTNode

    def pprint():
        pprint('Pair', self.name, self.value)

@dataclass
class MapNode(SequenceNode):
    items: List[PairNode]

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

@dataclass
class CallNode(ASTNode):
    function: ASTNode
    arguments: List[ASTNode]

    def pprint(self):
        return pprint('Call', self.function, *self.arguments)

@dataclass
class KeywordNode(ASTNode):
    expression: ASTNode

    def pprint(self):
        return pprint(self.__class__.__name__[:-4], self.expression)

@dataclass
class KeywordOptionalNode(KeywordNode):
    expression: Optional[ASTNode]

    def pprint(self):
        if expression is None:
            return self.__class__.__name__[:-4]
        else:
            return super().pprint()

@dataclass
class IterNode(KeywordNode):
    pass

@dataclass
class ReturnNode(KeywordOptionalNode):
    pass

@dataclass
class BreakNode(KeywordOptionalNode):
    pass

@dataclass
class ContinueNode(KeywordOptionalNode):
    pass

@dataclass
class YieldNode(KeywordNode):
    pass

@dataclass
class YieldFromNode(KeywordNode):
    pass

@dataclass
class LambdaNode(ASTNode):
    params: List[Token]
    returns: ASTNode

    def pprint(self):
        return pprint(self.__class__.__name__[:-4], self.params, self.returns)

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

@dataclass
class ExceptionNode(ClassNode):
    pass

@dataclass
class CaseNode(ASTNode):
    var: IdentifierNode
    cases: MapNode
    default: Optional[ASTNode]

    def pprint(self):
        if self.default is None:  # No else
            return pprint('Case', self.var, self.cases)
        else:
            return pprint('Case', self.var, self.cases, self.default)

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then: ASTNode
    default: Optional[ASTNode]

    def pprint(self):
        if self.default is None:  # No else
            return pprint('If', self.condition, self.then)
        else:
            return pprint('If', self.condition, self.then, self.default)

@dataclass
class ForNode(ASTNode):
    vars: List[Tokens]
    container: ASTNode
    body: BlockNode

    def pprint(self):
        return pprint('For', self.vars, self.container, self.body)

@dataclass
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
