import enum
from dataclasses import dataclass, field

OPS = [
    'INVALID',
    # Program
    'NOP',
    'HALT',
    # Stack
    'POP',
    # Memory
    'LOAD_VALUE',
    'LOAD_LOCAL',
    'STORE_LOCAL',
    'LOAD_NONLOCAL',
    'STORE_NONLOCAL',
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
OP_LENGTHS = {
    'LOAD_VALUE': 2,
    'LOAD_LOCAL': 2,
    'STORE_LOCAL': 2,
    'LOAD_NONLOCAL': 3,
    'STORE_NONLOCAL': 3,
}

## Classes
Op = enum.Enum('Op', ' '.join(OPS), start=-1)

class Bytecode(bytearray):
    def __repr__(self):
        contents = ''.join((fr'\x{hex(byte)[2:]:0>2}' for byte in self))
        return f"Bytecode(b'{contents}')"

    @staticmethod
    def assemble(instructions):
        bytecode = Bytecode()
        for instruction in instructions:
            op = instruction[0]
            oplength = OP_LENGTHS.get(op._name_, 1)
            if oplength == len(instruction):
                bytecode.append(op._value_)
                bytecode.extend(instruction[1:])
        return bytecode

    def disassemble(self):
        ip = 0
        while ip < len(self):
            op = Op(self[ip])
            oplength = OP_LENGTHS.get(op._name_, 1)
            nextip = ip + oplength
            args = self[ip+1:nextip]
            ip = nextip
            yield (op,) + tuple(args)
