from dataclasses import dataclass, field, InitVar
from typing import Dict
from . import ast
from .bytecode import Op, Unit, Bytecode

## Constants
UNARY_OPS = {
    '-':      Op.NEGATION,
    '!':      Op.BITWISE_NOT,
    'not':    Op.BOOLEAN_NOT,
}
BINARY_OPS = {
    '+':      Op.ADD,
    '-':      Op.SUBTRACT,
    '*':      Op.MULTIPLY,
    '/':      Op.DIVIDE,
    '%':      Op.MODULUS,
    '**':     Op.POWER,
    '&':      Op.BITWISE_AND,
    '|':      Op.BITWISE_OR,
    '^':      Op.BITWISE_XOR,
    '<<':     Op.BITSHIFT_LEFT,
    '>>':     Op.BITSHIFT_RIGHT,
    'and':    Op.BOOLEAN_AND,
    'or':     Op.BOOLEAN_OR,
    'xor':    Op.BOOLEAN_XOR,
    'is':     Op.IS,
    'is not': Op.IS_NOT,
    '==':     Op.EQUALS,
    '!=':     Op.NOT_EQUALS,
    '<':      Op.LESS_THAN,
    '<=':     Op.LESS_EQUALS,
    '>':      Op.GREATER_THAN,
    '>=':     Op.GREATER_EQUALS,
    'in':     Op.IN,
    'not in': Op.NOT_IN,
    '..':     Op.RANGE,
}

## Classes
@dataclass
class Decimal:
    value: InitVar[str]
    mantissa: int = field(init=False)
    exponent: int = field(init=False)

    def __post_init__(self, value):
        integer, fraction = value.split('.')
        self.mantissa = int(value.replace('.', ''))
        self.exponent = len(fraction)

@dataclass
class ASTCompiler:
    ast: ast.ParseNode
    bytecode: Bytecode = field(init=False)

    def __post_init__(self):
        self.bytecode = self.compile()

    def compile(self):
        values = []
        insbytecode = Bytecode.assemble(self.Program(self.ast, values))
        valuebytecode = Bytecode.assemble(self.Values(values))
        return valuebytecode + insbytecode

    def Values(self, values):
        # PUSH each byte (or maybe there'll be a PUSH_LONG for pushing multiple bytes)
        # Then MAKE_ the value, with argument how many bytes to pop from the stack
        # Finally STORE_VALUE
        for value in values:
            if isinstance(value, str):
                continue
                yield Op.MAKE_STRING, -1
            elif isinstance(value, int):
                continue
                yield Op.MAKE_INTEGER, -1
            elif isinstance(value, Decimal):
                continue
                yield Op.MAKE_DECIMAL, -1
            else:
                yield Op.INVALID,
                continue
            yield Op.STORE_VALUE,

    def Program(self, node, values):
        yield from self.Node(node, values, [])
        yield Op.HALT,

    def Node(self, node, values, *scopes):
        type = node.__class__.__name__
        yield from getattr(self, type, 'InvalidNode')(node, values, *scopes)

    def InvalidNode(self, node, values, *scopes):
        yield Op.INVALID,  # InvalidNodeError

    def LiteralNode(self, node, values, *scopes):
        type, value = node.value
        if type.startswith('IMAG_'):
            value = value.strip('j')
        value = {
            'INTEGER': int,
            'DECIMAL': Decimal,
            'IMAG_INTEGER': int,
            'IMAG_DECIMAL': Decimal,
        }.get(type)(node.value.value)
        try:
            index = values.index(value)
        except ValueError:
            index = len(values)
            values.append(value)
        yield Op.LOAD_VALUE, index
        if type in ('IMAG_INTEGER', 'IMAG_DECIMAL'):
            yield Op.MAKE_IMAGINARY,

    def UnitNode(self, node, values, *scopes):
        yield Op.MAKE_UNIT, Unit(node.unit.value.upper())._value_

    def IdentifierNode(self, node, values, *scopes):
        localscope = scopes[0]
        name = node.value.value
        if node.local:
            if name in localscope:
                index = localscope.index(name)
            else:
                index = -1  # NameError, not in scope
            yield Op.LOAD_LOCAL, index
        else:
            for i, scope in enumerate(scopes[1:], 1):
                if name in scope:
                    index = scope.index(name)
                    break
            else:
                i = -1
                index = -1  # NameError, not in any scope
            yield Op.LOAD_NONLOCAL, i, index

    def ListNode(self, node, values, *scopes):
        for item in node.items:
            yield from self.Node(item, values, *scopes)
        yield Op.MAKE_LIST, len(node.items)

    def TupleNode(self, node, values, *scopes):
        for item in node.items:
            yield from self.Node(item, values, *scopes)
        yield Op.MAKE_TUPLE, len(node.items)

    def MapNode(self, node, values, *scopes):
        for pair in node.items:
            yield from self.Node(pair.name, values, *scopes)
            yield from self.Node(pair.value, values, *scopes)
        yield Op.MAKE_MAP, len(node.items)

    def UnaryOpNode(self, node, values, *scopes):
        yield from self.Node(node.operand, values, *scopes)
        yield UNARY_OPS.get(node.operator.value, Op.INVALID),  # InvalidOperatorError

    def BinaryOpNode(self, node, values, *scopes):
        yield from self.Node(node.right, values, *scopes)
        yield from self.Node(node.left, values, *scopes)
        type, value = node.operator
        if type == 'ASSIGNMENT':
            value = value.strip('=')
        yield BINARY_OPS.get(value, Op.INVALID),  # InvalidOperatorError

    def SubscriptNode(self, node, values, *scopes):
        yield from self.Node(node.container, values, *scopes)
        yield from self.Node(node.subscript, values, *scopes)
        yield Op.GET_SUBSCRIPT,

    def AttrLookupNode(self, node, values, *scopes):
        yield from self.Node(node.obj, values, *scopes)
        yield from self.LiteralNode(node.attribute)

    def CallNode(self, node, values, *scopes):
        for arg in node.arguments:
            yield from self.Node(arg, values, *scopes)
        yield from self.Node(node.function)
        yield Op.CALL, len(node.arguments)

    def IterNode(self, node, values, *scopes):
        yield from self.Node(node.expression, values, scopes)
        yield Op.MAKE_ITERATOR,

    def ReturnNode(self, node, values, *scopes):
        yield from self.Node(node.expression, values, scopes)
        yield Op.RETURN

    def BreakNode(self, node, values, *scopes):
        yield Op.BREAK

    def ContinueNode(self, node, values, *scopes):
        yield Op.CONTINUE

    def YieldNode(self, node, values, *scopes):
        yield from self.Node(node.expression, values, scopes)
        yield Op.YIELD,

    def YieldFromNode(self, node, values, *scopes):
        yield from self.Node(node.expression, values, scopes)
        yield Op.YIELD_FROM,

    def LambdaNode(self, node, values, *scopes):
        yield Op.INVALID,  # Not implemented

    def AssignmentNode(self, node, values, *scopes):
        localscope = scopes[0]
        yield from self.Node(node.expression, values, *scopes)
        target = node.target
        if isinstance(target, ast.IdentifierNode):
            name = target.value.value
            if target.local:
                if name in localscope:
                    index = localscope.index(name)
                else:
                    index = len(localscope)
                    localscope.append(name)
                yield Op.STORE_LOCAL, index
            else:
                for i, scope in enumerate(scopes[1:], 1):
                    if name in scope:
                        index = scope.index(name)
                        break
                else:
                    i = -1
                    index = -1  # NameError, not in any scope
                yield Op.STORE_NONLOCAL, i, index
        else:
            yield Op.INVALID,

    def BlockNode(self, node, values, *scopes):
        last = len(node)
        for i, subnode in enumerate(node, 1):
            yield from self.Node(subnode, values, *scopes)
            if i != last:  # Last expression stays on the stack as the block's value
                yield Op.POP,

    def ObjectNode(self, node, values, *scopes):
        yield Op.INVALID,  # Not implemented

    def InterfaceNode(self, node, values, *scopes):
        yield Op.INVALID,  # Not implemented

    def ExceptionNode(self, node, values, *scopes):
        yield Op.INVALID,  # Not implemented

    def CaseNode(self, node, values, *scopes):
        yield Op.INVALID,  # Not implemented

    def IfNode(self, node, values, *scopes):
        yield Op.INVALID,  # Not implemented

    def ForNode(self, node, values, *scopes):
        yield Op.INVALID,  # Not implemented

    def WhileNode(self, node, values, *scopes):
        yield Op.INVALID,  # Not implemented
