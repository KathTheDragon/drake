from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union
from .scopes import Scope
from .types import Type

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
    'UnaryOpNode',
    'BinaryOpNode',
    'ParamNode',
    'LambdaNode',
    'IterNode',
    'MutableNode',
    'DoNode',
    'EnumNode',
    'ObjectNode',
    'ExceptionNode',
    'ModuleNode',
    'ThrowNode',
    'ReturnNode',
    'YieldNode',
    'YieldFromNode',
    'BreakNode',
    'ContinueNode',
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
    type: Type

@dataclass
class IdentifierNode(ASTNode):
    index: int
    scope: int = 0  # -1 -> builtin; 0 -> local; else -> nonlocal

@dataclass
class ValueNode(ASTNode):
    index: int  # Values are stored as their index in the global value storage

@dataclass
class RangeNode(ASTNode):
    start: ASTNode
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
class KwargNode(ASTNode):
    index: int
    value: ASTNode

@dataclass
class CallNode(ASTNode):
    function: ASTNode
    arguments: List[Union[ASTNode, Tuple[int, ASTNode]]]

@dataclass
class UnaryOpNode(ASTNode):
    operator: str
    operand: ASTNode

@dataclass
class BinaryOpNode(ASTNode):
    operator: str
    left: ASTNode
    right: ASTNode

@dataclass
class ParamNode(ASTNode):
    index: int
    default: Optional[ASTNode]

@dataclass
class LambdaNode(ASTNode):
    params: List[ParamNode]
    body: ASTNode

@dataclass
class IterNode(ASTNode):
    expression: ASTNode

@dataclass
class MutableNode(ASTNode):
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
class ReturnNode(ASTNode):
    expression: ASTNode

@dataclass
class YieldNode(ASTNode):
    expression: ASTNode

@dataclass
class YieldFromNode(ASTNode):
    expression: ASTNode

@dataclass
class BreakNode(ASTNode):
    pass

@dataclass
class ContinueNode(ASTNode):
    pass

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then: ASTNode
    default: Optional[ParseNode]

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
