from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union
from . import types
from .scopes import Scope
from .types import typecheck

__all__ = [
    'ASTNode',
    'IdentifierNode',
    'ValueNode',
    'RangeNode',
    'ListNode',
    'TupleNode',
    'MappingNode',
    'BlockNode',
    'SubscriptNode',
    'LookupNode',
    'CallNode',
    'LambdaNode',
    'IterNode',
    'DoNode',
    'EnumNode',
    'ObjectNode',
    'ExceptionNode',
    'ModuleNode',
    'ThrowNode',
    'RaisesNode',
    'IfNode',
    'CaseNode',
    'TryNode',
    'ForNode',
    'WhileNode',
    'AssignmentNode'
]

## Nodes
@dataclass
class ASTNode:
    @property
    def type(self):
        raise types.InvalidType

@dataclass
class IdentifierNode(ASTNode):
    index: int
    scope: int = 0  # -1 -> builtin; 0 -> local; else -> nonlocal

@dataclass
class ValueNode(ASTNode):
    _type: types.Type = field(init=True)
    index: int  # Values are stored as their index in the global value storage

    @property
    def type(self):
        return self._type

@dataclass
class RangeNode(ASTNode):
    start: ASTNode
    inclusive: bool = False
    end: Optional[ASTNode] = None
    step: Optional[ASTNode] = None

@dataclass
class ListNode(ASTNode):
    items: List[ASTNode]

@dataclass
class TupleNode(ASTNode):
    items: List[ASTNode]

@dataclass
class MappingNode(ASTNode):
    items: List[Tuple[ASTNode, ASTNode]]

@dataclass
class BlockNode(ASTNode):
    expressions: List[ASTNode]
    locals: Scope

@dataclass
class SubscriptNode(ASTNode):
    container: ASTNode
    subscript: Union[RangeNode, ListNode]

@dataclass
class LookupNode(ASTNode):
    obj: ASTNode
    attribute: int  # Attributes are just identifiers pointing to an object's internal namespace

@dataclass
class CallNode(ASTNode):
    function: ...  # Need to figure out how functions should be done
    arguments: List[Union[ASTNode, Tuple[int, ASTNode]]]


@dataclass
class LambdaNode(ASTNode):
    params: List[Union[ASTNode, Tuple[int, ASTNode]]]
    body: ASTNode

@dataclass
class IterNode(ASTNode):
    expression: ASTNode


@dataclass
class DoNode(ASTNode):
    block: BlockNode

@dataclass
class EnumNode(ASTNode):
    flags: bool
    items: List[ValueNode]

@dataclass
class ObjectNode(ASTNode):
    definition: BlockNode

@dataclass
class ExceptionNode(ASTNode):
    definition: BlockNode

@dataclass
class ModuleNode(ASTNode):
    definition: BlockNode

@dataclass
class ThrowNode(ASTNode):
    expression: ASTNode


@dataclass
class RaisesNode(ASTNode):
    expression: ASTNode
    exception: IdentifierNode

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then: ASTNode
    default: Optional[ASTNode]

@dataclass
class CaseNode(ASTNode):
    value: ASTNode
    cases: Tuple[ASTNode, ASTNode]
    default: Optional[ASTNode]

@dataclass
class TryNode(ASTNode):
    body: ASTNode
    catch: List[Tuple[IdentifierNode, ASTNode]]
    finally_: Optional[ASTNode]

@dataclass
class ForNode(ASTNode):
    container: ASTNode
    body: ASTNode

@dataclass
class WhileNode(ASTNode):
    condition: ASTNode
    body: ASTNode

@dataclass
class AssignmentNode(ASTNode):
    targets: Union[IdentifierNode, List[IdentiferNode]]
    expression: ASTNode
