from dataclasses import dataclass, field, InitVar
from typing import Dict
from .bytecode import Op, Bytecode
from . import ast

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
class Real:
    value: InitVar[str]
    integer: int = field(init=False)
    mantissa: int = field(init=False)
    exponent: int = field(init=False)

    def __post_init__(self, value):
        integer, fraction = value.split('.')
        self.integer = int(integer)
        self.mantissa = int(fraction)
        self.exponent = len(fraction)

@dataclass
class ASTCompiler:
    ast: ast.ASTNode
    bytecode: Bytecode = field(init=False)

    def __post_init__(self):
        self.bytecode = self.compile()

    def compile(self):
        values = []
        insbytecode = Bytecode.assemble(self.Node(self.ast, values, []))
        valuebytecode = Bytecode.assemble(self.Values(values))
        haltbytecode = Bytecode.assemble((Op.HALT,))
        return valuebytecode + insbytecode + haltbytecode

    def Values(self, values):
        yield from ()

    def Node(self, node, values, *scopes):
        type = node.__class__.__name__
        yield from getattr(self, type, 'InvalidNode')(node, values, *scopes)

    def InvalidNode(self, node, values, *scopes):
        yield Op.INVALID,  # InvalidNodeError

    def LiteralNode(self, node, values, *scopes):
        type, value = node.value
        if type == 'NUMBER':
            if '.' in value:  # Real
                value = Real(value)
            else:
                value = int(value)
        index = len(values)
        values.append(value)
        yield Op.LOAD_VALUE, index

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

    def UnaryOpNode(self, node, values, *scopes):
        yield from self.Node(node.operand, values, *scopes)
        yield UNARY_OPS.get(node.operator.value, Op.INVALID),  # InvalidOperatorError

    def BinaryOpNode(self, node, values, *scopes):
        yield from self.Node(node.right, values, *scopes)
        yield from self.Node(node.left, values, *scopes)
        yield BINARY_OPS.get(node.operator.value, Op.INVALID),  # InvalidOperatorError

    def AssignmentNode(self, node, values, *scopes):
        localscope = scopes[0]
        yield from self.Node(node.expression, values, *scopes)
        target = node.target
        if isinstance(target, ast.Identifier):
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
