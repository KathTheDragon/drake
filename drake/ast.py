import enum
from dataclasses import dataclass, field
from typing import List, Optional, Union
from .lexer import Token

__all__ = [
    'ASTNode',
    'TypeNode',
    'TypehintNode',
    'LiteralNode',
    'IdentifierNode',
    'GroupingNode',
    'ListNode',
    'TupleNode',
    'PairNode',
    'MapNode',
    'UnaryOpNode',
    'BinaryOpNode',
    'SubscriptNode',
    'LookupNode',
    'CallNode',
    'IterNode',
    'ReturnNode',
    'BreakNode',
    'ContinueNode',
    'YieldNode',
    'YieldFromNode',
    'LambdaNode',
    'MultimethodNode',
    'AssignmentNode',
    'BlockNode',
    'ClassNode',
    'ExceptionNode',
    'CaseNode',
    'IfNode',
    'ForNode',
    'WhileNode'
]

## Helper functions
def indent(string):
    return '\n'.join('  '+line for line in string.splitlines())

def isprimary(*nodes):
    return all(isinstance(node, (LiteralNode, IdentifierNode, list)) for node in nodes)

def pprint(name, *args):
    argstrings = []
    for arg in args:
        if isinstance(arg, ASTNode):
            argstrings.append(str(arg))
        elif isinstance(arg, list):
            argstrings.append(f'({", ".join(item.value for item in arg)})')
        else:
            argstrings.append(arg)
    if isprimary(*args):
        return f'{name} ( {", ".join(argstrings)} )'
    else:
        delimiter = ',\n'  # Can't use this directly in the f-string
        return f'{name} (\n{delimiter.join((indent(arg) for arg in argstrings))}\n)'

## Classes
class ASTNode:
    def __str__(self):
        raise NotImplementedError

    @property
    def nodetype(self):
        return self.__class__.__name__[:-4]

@dataclass
class TypeNode(ASTNode):
    type: Token
    params: List['TypeNode']

    def __str__(self):
        type = self.type.value
        if self.params:
            return f'{type}[{", ".join(self.params)}]'
        else:
            return type

@dataclass
class TypehintNode(ASTNode):
    typehint: TypeNode
    expr: ASTNode

    def __str__(self):
        return f'<{self.typehint}> {self.expr}'

@dataclass
class LiteralNode(ASTNode):
    value: Token

    def __str__(self):
        return f'{self.value.type.capitalize()} {self.value.value}'

@dataclass
class IdentifierNode(ASTNode):
    name: Token

    def __str__(self):
        return f'Identifier {self.name.value}'

@dataclass
class GroupingNode(ASTNode):
    expr: ASTNode

    def __str__(self):
        if isprimary(self.expr):
            return f'({self.expr})'
        else:
            return f'(\n{self.expr}\n)'

@dataclass
class SequenceNode(ASTNode):
    items: List[ASTNode]

    def __str__(self):
        return pprint(self.nodetype, *self.items)

@dataclass
class ListNode(SequenceNode):
    pass

@dataclass
class TupleNode(SequenceNode):
    pass

@dataclass
class PairNode(ASTNode):
    key: ASTNode
    value: ASTNode

    def __str__(self):
        return pprint('Pair', self.key, self.value)

@dataclass
class MapNode(SequenceNode):
    items: List[PairNode]

@dataclass
class UnaryOpNode(ASTNode):
    operator: Token
    operand: ASTNode

    def __str__(self):
        return pprint(f'Unary {self.operator.value}', self.operand)

@dataclass
class BinaryOpNode(ASTNode):
    left: ASTNode
    operator: Token
    right: ASTNode

    def __str__(self):
        return pprint(f'Binary {self.operator.value}', self.left, self.right)

@dataclass
class SubscriptNode(ASTNode):
    container: ASTNode
    subscript: List[ASTNode]

    def __str__(self):
        return pprint('Subscript', self.container, *self.subscript)

@dataclass
class LookupNode(ASTNode):
    obj: ASTNode
    attribute: IdentifierNode

    def __str__(self):
        return pprint('Lookup', self.obj, self.attribute)

@dataclass
class CallNode(ASTNode):
    function: ASTNode
    arguments: List[ASTNode]

    def __str__(self):
        return pprint('Call', self.function, *self.arguments)

@dataclass
class KeywordNode(ASTNode):
    expression: ASTNode

    def __str__(self):
        return pprint(self.nodetype, self.expression)

@dataclass
class IterNode(KeywordNode):
    pass

@dataclass
class ReturnNode(KeywordNode):
    pass

@dataclass
class BreakNode(ASTNode):
    def __str__(self):
        return 'Break'

@dataclass
class ContinueNode(ASTNode):
    def __str__(self):
        return 'Continue'

@dataclass
class YieldNode(KeywordNode):
    pass

@dataclass
class YieldFromNode(KeywordNode):
    pass

@dataclass
class LambdaNode(ASTNode):
    params: List[Union[IdentifierNode, 'AssignmentNode']]
    returns: ASTNode

    def __str__(self):
        return pprint(self.nodetype, *self.params, self.returns)

@dataclass
class MultimethodNode(SequenceNode):
    items: List[LambdaNode]

@dataclass
class AssignmentNode(ASTNode):
    mode: str
    target: ASTNode
    expression: ASTNode

    def __str__(self):
        if self.mode:
            return pprint(f'Assign {self.mode}', self.target, self.expression)
        else:
            return pprint('Assign', self.target, self.expression)

@dataclass
class BlockNode(ASTNode):
    expressions: List[ASTNode]

    def __iter__(self):
        yield from self.expressions

    def __len__(self):
        return len(self.expressions)

    def __str__(self):
        return 'Block {\n' + '\n'.join(indent(str(node)) for node in self) + '\n}'

@dataclass
class ClassNode(LambdaNode):
    returns: BlockNode

@dataclass
class ExceptionNode(ClassNode):
    pass

@dataclass
class CaseNode(ASTNode):
    var: IdentifierNode
    cases: MapNode
    default: Optional[ASTNode]

    def __str__(self):
        if self.default is None:  # No else
            return pprint('Case', self.var, self.cases)
        else:
            return pprint('Case', self.var, self.cases, self.default)

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then: ASTNode
    default: Optional[ASTNode]

    def __str__(self):
        if self.default is None:  # No else
            return pprint('If', self.condition, self.then)
        else:
            return pprint('If', self.condition, self.then, self.default)

@dataclass
class ForNode(ASTNode):
    vars: List[ASTNode]
    container: ASTNode
    body: BlockNode

    def __str__(self):
        return pprint('For', *self.vars, self.container, self.body)

@dataclass
class WhileNode(ASTNode):
    condition: ASTNode
    body: BlockNode

    def __str__(self):
        return pprint('While', self.condition, self.body)

class Precedence(enum.IntEnum):
    NONE       = enum.auto()
    ASSIGNMENT = enum.auto()  # : = += -= *= /=
    FLOW       = enum.auto()  # if case for while
    LAMBDA     = enum.auto()  # ->
    OR         = enum.auto()  # or
    XOR        = enum.auto()  # xor
    AND        = enum.auto()  # and
    COMPARISON = enum.auto()  # in is == != < > <= >=
    RANGE      = enum.auto()  # ..
    BIT_OR     = enum.auto()  # |
    BIT_XOR    = enum.auto()  # ^
    BIT_AND    = enum.auto()  # &
    SHIFT      = enum.auto()  # >> <<
    ADD        = enum.auto()  # + -
    MULT       = enum.auto()  # * / %
    EXP        = enum.auto()  # **
    UNARY      = enum.auto()  # not ! -
    CALL       = enum.auto()  # . ...(...) ...[...]
    PRIMARY    = enum.auto()  # literal identifier tuple list map block
