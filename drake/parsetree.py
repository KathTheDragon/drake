from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

__all__ = [
    'ParseNode',
    'IdentifierNode',
    'StringNode',
    'NumberNode',
    'BooleanNode',
    'NoneNode',
    'PairNode',
    'MappingNode',
    'BlockNode',
    'RangeNode',
    'ListNode',
    'TupleNode',
    'SubscriptNode',
    'LookupNode',
    'CallNode',
    'UnaryOpNode',
    'BinaryOpNode',
    'VParamNode',
    'KwParamNode',
    'LambdaNode',
    'IterNode',
    'DoNode',
    'ObjectNode',
    'EnumNode',
    'ModuleNode',
    'ExceptionNode',
    'MutableNode',
    'ThrowNode',
    'ReturnNode',
    'YieldNode',
    'YieldFromNode',
    'BreakNode',
    'ContinueNode',
    'PassNode',
    'IfNode',
    'CaseNode',
    'CatchNode',
    'TryNode',
    'ForNode',
    'WhileNode',
    'TypeNode',
    'DeclarationNode',
    'TargetNode',
    'AssignmentNode',
]

## Helper functions
def indent(string):
    return '\n'.join('  '+line for line in string.splitlines())

def isprimary(*nodes):
    return all(isinstance(node, (LiteralNode, NoneNode, IdentifierNode)) for node in nodes)

def pprint(name, *args):
    argstrings = []
    for arg in args:
        if isinstance(arg, ParseNode):
            argstrings.append(str(arg))
        elif isinstance(arg, list):
            argstrings.append(pprint('', *arg).strip())
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
    location: Tuple[int, int] = field(init=False, compare=False)

    def __post_init__(self):
        self.location = (0,0)  # Set this here so it doesn't fuck with signatures

    def __str__(self):
        return self.nodetype

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
class NoneNode(LiteralNode):
    value: str = field(init=False, default='none')

    def __str__(self):
        return 'None'

@dataclass
class SequenceNode(ParseNode):
    items: List[ParseNode]

    def __str__(self):
        return pprint(self.nodetype, *self.items)

@dataclass
class RangeNode(ParseNode):
    start: ParseNode
    end: Optional[ParseNode] = None
    step: Optional[ParseNode] = None

    def __str__(self):
        return pprint('Range', self.start, self.end, self.step)

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

    def __str__(self):
        return pprint('Block', *self.expressions)

@dataclass
class SubscriptNode(ParseNode):
    container: ParseNode
    subscript: Union[RangeNode, ListNode]

    def __str__(self):
        return pprint('Subscript', self.container, self.subscript)

@dataclass
class LookupNode(ParseNode):
    obj: ParseNode
    attribute: IdentifierNode

    def __str__(self):
        return pprint('Lookup', self.obj, self.attribute)

@dataclass
class KwargNode(ParseNode):
    name: IdentifierNode
    value: ParseNode

    def __str__(self):
        return pprint('Kwarg', self.name, self.value)

VArg = Union[ParseNode, 'UnaryOpNode']  # expr | '*' expr
KwArg = Union[KwargNode, 'UnaryOpNode']  # name = expr | '**' expr

@dataclass
class CallNode(ParseNode):
    function: ParseNode
    vargs: List[VArg]
    kwargs: List[KwArg]

    def __str__(self):
        return pprint('Call', self.function, self.vargs, self.kwargs)

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

@dataclass
class ParamNode(ParseNode):
    starred: bool
    typehint: TypeNode
    name: IdentifierNode

    def __str__(self):
        star = '*' if self.nodetype == 'VParam' else '**'
        if self.starred:
            return f'{self.nodetype} {star} <{self.typehint}> {self.name}'
        else:
            return f'{self.nodetype} <{self.typehint}> {self.name}'

@dataclass
class VParamNode(ParamNode):
    pass

@dataclass
class KwParamNode(ParamNode):
    value: Optional[ParseNode] = None

    def __str__(self):
        if value is not None:
            return pprint('KwParam', f'<{self.typehint}> {self.name}', self.value)
        else:
            return super().__str__()

@dataclass
class LambdaNode(ParseNode):
    vparams: List[VParamNode]
    kwparams: List[KwParamNode]
    returns: ParseNode

    def __str__(self):
        return pprint(self.nodetype, self.vparams, self.kwparams, self.returns)

@dataclass
class KeywordNode(ParseNode):
    expression: ParseNode

    def __str__(self):
        return pprint(self.nodetype, self.expression)

@dataclass
class IterNode(KeywordNode):
    pass

@dataclass
class DoNode(KeywordNode):
    expression: BlockNode

@dataclass
class ObjectNode(ParseNode):
    definition: BlockNode

    def __str__(self):
        return pprint(self.nodetype, self.definition)

@dataclass
class EnumNode(ParseNode):
    flags: bool
    items: List[PairNode]

    def __str__(self):
        if self.flags:
            return pprint('Enum flags', *self.items)
        else:
            return pprint('Enum', *self.items)

@dataclass
class ModuleNode(ObjectNode):
    pass

@dataclass
class ExceptionNode(ObjectNode):
    pass

@dataclass
class MutableNode(KeywordNode):
    pass

@dataclass
class ThrowNode(KeywordNode):
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
    pass

@dataclass
class ContinueNode(ParseNode):
    pass

@dataclass
class PassNode(ParseNode):
    pass

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
    cases: MappingNode
    default: Optional[ParseNode]

    def __str__(self):
        if self.default is None:  # No else
            return pprint('Case', self.var, self.cases)
        else:
            return pprint('Case', self.var, self.cases, self.default)

@dataclass
class CatchNode(ParseNode):
    exception: IdentifierNode
    name: Optional[IdentifierNode]
    body: ParseNode  # Might change to BlockNode

    def __str__(self):
        return pprint('Catch', self.exception, self.container, self.body)

@dataclass
class TryNode(ParseNode):
    body: ParseNode
    catches: List[CatchNode]
    finally_: Optional[ParseNode]

    def __str__(self):
        return pprint('Try', self.body, *self.catch, self.finally_)

@dataclass
class ForNode(ParseNode):
    vars: Union[IdentifierNode, List[IdentifierNode]]
    container: ParseNode
    body: BlockNode

    def __str__(self):
        return pprint('For', self.vars, self.container, self.body)

@dataclass
class WhileNode(ParseNode):
    condition: ParseNode
    body: BlockNode

    def __str__(self):
        return pprint('While', self.condition, self.body)

@dataclass
class TargetNode(ParseNode):
    mode: str
    typehint: Optional['TypeNode']
    name: IdentifierNode

    def __str__(self):
        fragments = []
        if self.mode:
            fragments.append(mode)
        if self.typehint:
            fragments.append(f'<{self.typehint}>')
        fragments.append(str(self.name))
        return ' '.join(fragments)

@dataclass
class AssignmentNode(ParseNode):
    targets: Union[TargetNode, List[TargetNode]]
    operator: str
    expression: ParseNode

    def __str__(self):
        if self.operator == '=':
            nodetype = 'Assign'
        else:
            nodetype = f'Assign {self.operator}'
        return pprint(nodetype, self.targets, self.expression)

@dataclass
class TypeNode(ParseNode):
    type: IdentifierNode
    params: List['TypeNode'] = field(default_factory=list)

    def __str__(self):
        type = self.type.name
        if self.params:
            return f'{type}[{", ".join(self.params)}]'
        else:
            return type

@dataclass
class DeclarationNode(ParseNode):
    const: bool
    typehint: TypeNode
    name: IdentifierNode

    def __str__(self):
        if self.const:
            return f'const <{self.typehint}> {self.name}'
        else:
            return f'<{self.typehint}> {self.name}'
