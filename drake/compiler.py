from dataclasses import dataclass, field, InitVar
from typing import Dict
from .bytecode import Op

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

## Functions
def compileASTNode(node, values, *scopes):
    from . import ast
    if not scopes:
        scopes = ([],)
    localscope = scopes[0]
    if isinstance(node, ast.Literal):
        type, value = node.value
        if type == 'NUMBER':
            if '.' in value:  # Real
                value = Real(value)
            else:
                value = int(value)
        index = len(values)
        values.append(value)
        yield Op.LOAD_VALUE, index
    elif isinstance(node, ast.Identifier):
        name = node.name.value
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
    elif isinstance(node, ast.UnaryOp):
        yield from compileASTNode(node.operand, values, *scopes)
        yield UNARY_OPS.get(node.operator.value, Op.INVALID),  # InvalidOperatorError
    elif isinstance(node, ast.BinaryOp):
        yield from compileASTNode(node.right, values, *scopes)
        yield from compileASTNode(node.left, values, *scopes)
        yield BINARY_OPS.get(node.operator.value, Op.INVALID),  # InvalidOperatorError
    elif isinstance(node, ast.Assignment):
        name = node.name.value
        if node.local:
            if name in localscope:
                index = localscope.index(name)
        yield from compileASTNode(node.expression, values, *scopes)
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
    elif isinstance(node, ast.Block):
        last = len(nodes)
        for i, subnode in enumerate(node, 1):
            yield from compileASTNode(subnode, values, *scopes)
            if i != last:  # Last expression stays on the stack as the block's value
                yield Op.POP,
