import enum
from dataclasses import dataclass, field

# Abbreviations:
#   TOS = top of stack
#   NOS = next (second) on stack
#   3OS = third on stack
NULLARY_OPS = [
    'INVALID',
    # Program
    'NOP',
    'HALT',
    'POP',
    # Arithmetic
    'NEGATION',
    'ADD',
    'SUBTRACT',
    'MULTIPLY',
    'DIVIDE',
    'MODULUS',
    'POWER',
    # Bitwise
    'BITWISE_NOT',
    'BITWISE_AND',
    'BITWISE_OR',
    'BITWISE_XOR',
    'BITSHIFT_LEFT',
    'BITSHIFT_RIGHT',
    # Boolean
    'BOOLEAN_NOT',
    'BOOLEAN_AND',
    'BOOLEAN_OR',
    'BOOLEAN_XOR',
    # Comparison
    'IS',
    'IS_NOT',
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
UNARY_OPS = [
    'LOAD_VALUE',
    'LOAD_LOCAL',
    'STORE_LOCAL',
]
BINARY_OPS = [
    'LOAD_NONLOCAL',
    'STORE_NONLOCAL',
]
OPS = NULLARY_OPS + UNARY_OPS + BINARY_OPS

## Classes
Op = enum.Enum('Op', ' '.join(OPS), start=0)

class Bytecode(bytearray):
    def __repr__(self):
        contents = ''.join((fr'\x{hex(byte)[2:]:0>2}' for byte in self))
        return f"Bytecode(b'{contents}')"

    @staticmethod
    def assemble(instructions):
        bytecode = Bytecode()
        for instruction in instructions:
            op = instruction[0]
            opname = op._name_
            if opname in NULLARY_OPS:
                oplength = 1
            elif opname in UNARY_OPS:
                oplength = 2
            elif opname in BINARY_OPS:
                oplength = 3
            if oplength == len(instruction):
                bytecode.append(op._value_)
                bytecode.extend(instruction[1:])
        return bytecode

    def disassemble(self):
        ip = 0
        while ip < len(self):
            op = Op(self[ip])
            opname = op._name_
            if opname in NULLARY_OPS:
                oplength = 1
            elif opname in UNARY_OPS:
                oplength = 2
            elif opname in BINARY_OPS:
                oplength = 3
            nextip = ip + oplength
            args = self[ip+1:nextip]
            ip = nextip
            yield (op,) + tuple(args)
