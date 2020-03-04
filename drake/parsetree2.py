import enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

__all__ = [
    'ParseNode',
    'TypeNode',
    'DeclarationNode',
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
    'AssignmentNode',
    'BlockNode',
    'ObjectNode',
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
        if isinstance(arg, ParseNode):
            argstrings.append(str(arg))
        elif isinstance(arg, list):
            argstrings.append(f'({", ".join(item.value for item in arg)})')
        elif arg:
            argstrings.append(arg)
    if isprimary(*args):
        return f'{name} ( {", ".join(argstrings)} )'
    else:
        delimiter = ',\n'  # Can't use this directly in the f-string
        return f'{name} (\n{delimiter.join((indent(arg) for arg in argstrings))}\n)'

## Classes
@dataclass
class ParseNode:
    def __str__(self):
        raise NotImplementedError

    @property
    def nodetype(self):
        return self.__class__.__name__[:-4]

@dataclass
class IdentifierNode(ParseNode):
    name: str

    def __str__(self):
        return f'Identifier {self.name}'

@dataclass
class LiteralNode(ParseNode):
    value: str

    def __str__(self):
        return f'{self.nodetype} {self.value}'

@dataclass
class StringNode(LiteralNode):
    pass

@dataclass
class NumberNode(LiteralNode):
    pass

@dataclass
class BooleanNode(LiteralNode):
    pass

@dataclass
class NoneNode(ParseNode):
    pass

@dataclass
class GroupingNode(ParseNode):
    expr: ParseNode

    def __str__(self):
        if isprimary(self.expr):
            return f'({self.expr})'
        else:
            return f'(\n{self.expr}\n)'

@dataclass
class SequenceNode(ParseNode):
    items: List[ParseNode]

    def __str__(self):
        return pprint(self.nodetype, *self.items)

@dataclass
class ListNode(SequenceNode):
    pass

@dataclass
class TupleNode(SequenceNode):
    pass

@dataclass
class PairNode(ParseNode):
    key: ParseNode
    value: ParseNode

    def __str__(self):
        return pprint('Pair', self.key, self.value)

@dataclass
class MappingNode(SequenceNode):
    items: List[PairNode]

@dataclass
class BlockNode(ParseNode):  # Not inheriting from SequenceNode, though it is a kind of sequence
    expressions: List[ParseNode]

    def __iter__(self):
        yield from self.expressions

    def __len__(self):
        return len(self.expressions)

    def __str__(self):
        return 'Block {\n' + '\n'.join(indent(str(node)) for node in self) + '\n}'

@dataclass
class SubscriptNode(ParseNode):
    container: ParseNode
    subscript: List[ParseNode]

    def __str__(self):
        return pprint('Subscript', self.container, *self.subscript)

@dataclass
class LookupNode(ParseNode):
    obj: ParseNode
    attribute: IdentifierNode

    def __str__(self):
        return pprint('Lookup', self.obj, self.attribute)

VArg = Union[ParseNode, UnaryOpNode]  # expr | '*' expr
KwArg = Union['AssignmentNode', UnaryOpNode]  # name = expr | '**' expr

@dataclass
class CallNode(ParseNode):
    function: ParseNode
    arguments: List[Union[VArg, KwArg]]

    def __str__(self):
        return pprint('Call', self.function, *self.arguments)

@dataclass
class UnaryOpNode(ParseNode):
    operator: str
    operand: ParseNode

    def __str__(self):
        return pprint(f'Unary {self.operator}', self.operand)

@dataclass
class BinaryOpNode(ParseNode):
    left: ParseNode
    operator: str
    right: ParseNode

    def __str__(self):
        return pprint(f'Binary {self.operator}', self.left, self.right)

VParam = Union['DeclarationNode', UnaryOpNode]  # type name | '*' type name
KwParam = Union['AssignmentNode', UnaryOpNode]  # type name = expr | '**' type name

@dataclass
class LambdaNode(ParseNode):
    params: List[Union[VParam, KwParam]]
    returns: ParseNode

    def __str__(self):
        return pprint(self.nodetype, *self.params, self.returns)

@dataclass
class KeywordNode(ParseNode):
    expression: ParseNode

    def __str__(self):
        return pprint(self.nodetype, self.expression)

@dataclass
class IterNode(KeywordNode):
    pass

@dataclass
class ObjectNode(ParseNode):
    definition: BlockNode

    def __str__(self):
        return pprint('Object', *self.definition)

@dataclass
class ExceptionNode(ObjectNode):
    pass

@dataclass
class MutableNode(KeywordNode):
    pass

@dataclass
class ReturnNode(KeywordNode):
    pass

@dataclass
class YieldNode(KeywordNode):
    pass

@dataclass
class YieldFromNode(KeywordNode):
    pass

@dataclass
class BreakNode(ParseNode):
    def __str__(self):
        return 'Break'

@dataclass
class ContinueNode(ParseNode):
    def __str__(self):
        return 'Continue'

@dataclass
class IfNode(ParseNode):
    condition: ParseNode
    then: ParseNode
    default: Optional[ParseNode]

    def __str__(self):
        if self.default is None:  # No else
            return pprint('If', self.condition, self.then)
        else:
            return pprint('If', self.condition, self.then, self.default)

@dataclass
class CaseNode(ParseNode):
    value: ParseNode
    cases: MapNode
    default: Optional[ParseNode]

    def __str__(self):
        if self.default is None:  # No else
            return pprint('Case', self.var, self.cases)
        else:
            return pprint('Case', self.var, self.cases, self.default)

@dataclass
class ForNode(ParseNode):
    vars: List[ParseNode]
    container: ParseNode
    body: BlockNode

    def __str__(self):
        return pprint('For', *self.vars, self.container, self.body)

@dataclass
class WhileNode(ParseNode):
    condition: ParseNode
    body: BlockNode

    def __str__(self):
        return pprint('While', self.condition, self.body)

@dataclass
class Target(ParseNode):  # Just a wrapper to cooperate with pprint
    mode: str
    typehint: TypeNode
    name: str

    def __str__(self):
        if mode:
            return f'{mode} {name}'
        else:
            return name

@dataclass
class AssignmentNode(ParseNode):
    targets: List[Target]
    expression: ParseNode

    def __str__(self):
        return pprint('Assign', *self.targets, self.expression)

@dataclass
class TypeNode(ParseNode):
    type: str
    params: List['TypeNode']

    def __str__(self):
        type = self.type.value
        if self.params:
            return f'{type}[{", ".join(self.params)}]'
        else:
            return type

@dataclass
class DeclarationNode(ParseNode):
    typehint: TypeNode
    name: str

    def __str__(self):
        return f'<{self.typehint}> {self.name}'
