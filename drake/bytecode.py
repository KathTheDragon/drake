import enum
from dataclasses import dataclass, field

## Classes
class Op(enum.Enum):
    INVALID = -1
    # Program
    NOP = 0x00
    HALT = 0x01
    # Stack
    POP = 0x08
    # Memory
    LOAD_VALUE = 0x20
    LOAD_LOCAL = 0x24
    STORE_LOCAL = 0x25
    LOAD_NONLOCAL = 0x28
    STORE_NONLOCAL = 0x29
    # Arithmetic
    NEGATION = 0x30
    ADD = 0x31
    SUBTRACT = 0x32
    MULTIPLY = 0x33
    DIVIDE = 0x34
    MODULUS = 0x35
    POWER = 0x36
    # Bitwise
    BITWISE_NOT = 0x40
    BITWISE_AND = 0x41
    BITWISE_OR = 0x42
    BITWISE_XOR = 0x43
    BITSHIFT_LEFT = 0x44
    BITSHIFT_RIGHT = 0x45
    # Boolean
    BOOLEAN_NOT = 0x48
    BOOLEAN_AND = 0x49
    BOOLEAN_OR = 0x4A
    BOOLEAN_XOR = 0x4B
    # Comparison
    IS = 0x50
    IS_NOT = 0x51
    EQUALS = 0x52
    NOT_EQUALS = 0x53
    LESS_THAN = 0x54
    LESS_EQUALS = 0x55
    GREATER_THAN = 0x56
    GREATER_EQUALS = 0x57
    # Containment
    IN = 0x58
    NOT_IN = 0x59
    # Misc
    RANGE = 0x5A

OP_LENGTHS = {
    'LOAD_VALUE': 2,
    'LOAD_LOCAL': 2,
    'STORE_LOCAL': 2,
    'LOAD_NONLOCAL': 3,
    'STORE_NONLOCAL': 3,
}


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
