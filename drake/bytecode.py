import enum
from dataclasses import dataclass, field

# Abbreviations:
#   TOS = top of stack
#   NOS = next (second) on stack
#   3OS = third on stack
NULLARY_OPS = [
    # Program
    'NOP',
    'POP',
]
UNARY_OPS = [
    # Program
    'LOAD_VALUE',
    'LOAD_LOCAL',
    'STORE_LOCAL',
    # Operators
    'NEGATION',
    'BITWISE_NOT',
    'BOOLEAN_NOT',
]
BINARY_OPS = [
    # Program
    'LOAD_NONLOCAL',
    'STORE_NONLOCAL',
    # Arithmetic
    'ADD',
    'SUBTRACT',
    'MULTIPLY',
    'DIVIDE',
    'MODULUS',
    'POWER',
    # Bitwise
    'BITWISE_AND',
    'BITWISE_OR',
    'BITWISE_XOR',
    'BITSHIFT_LEFT',
    'BITSHIFT_RIGHT',
    # Boolean
    'BOOLEAN_AND',
    'BOOLEAN_OR',
    'BOOLEAN_XOR',
    # Comparison
    'IS',
    'IS_NOT'
    'EQUALS',
    'NOT_EQUALS',
    'LESS_THAN',
    'LESS_EQUALS',
    'GREATER_THAN',
    'GREATER_EQUALS',
    # Containment
    'IN',
    'NOT_IN',
    # Misc
    'RANGE',
]
TERNARY_OPS = [
]
OPS = NULLARY_OPS + UNARY_OPS + BINARY_OPS + TERNARY_OPS

## Classes
Op = enum.Enum('Op', ' '.join(OPS), start=0)
