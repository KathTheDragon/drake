import enum
from dataclasses import dataclass, field

## Classes
class Op(enum.Enum):
    INVALID = -1
    # Program
    NOP = 0x00
    HALT = 0x01
    RETURN = 0x02
    CONTINUE = 0x03
    BREAK = 0x04
    CALL = 0x05
    # Stack
    POP = 0x08
    PUSH = 0x09
    # Values
    MAKE_UNIT = 0x10  # Makes finite types (none, bool, etc)
    MAKE_STRING = 0x11
    MAKE_INTEGER = 0x12
    MAKE_DECIMAL = 0x13
    MAKE_IMAGINARY = 0x14
    MAKE_LIST = 0x18
    MAKE_TUPLE = 0x19
    MAKE_MAP = 0x1A
    MAKE_ITERATOR = 0x1B
    MAKE_LAMBDA = 0x1C
    MAKE_CLASS = 0x1D
    MAKE_INTERFACE = 0x1E
    MAKE_EXCEPTION = 0x1F
    # Memory
    LOAD_VALUE = 0x20
    LOAD_LOCAL = 0x24
    STORE_LOCAL = 0x25
    DELETE_LOCAL = 0x26
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
    # Subscript
    GET_SUBSCRIPT = 0x60
    SET_SUBSCRIPT = 0x61
    DEL_SUBSCRIPT = 0x62
    # Attributes
    GET_ATTRIBUTE = 0x64
    SET_ATTRIBUTE = 0x65

OP_LENGTHS = {
    Op.RETURN: 2,
    Op.CONTINUE: 2,
    Op.BREAK: 2,
    Op.PUSH: 2,
    Op.CALL: 2,
    Op.MAKE_UNIT: 2,
    Op.MAKE_STRING: 2,
    Op.MAKE_INTEGER: 2,
    Op.MAKE_DECIMAL: 2,
    Op.MAKE_IMAGINARY: 2,
    Op.MAKE_LIST: 2,
    Op.MAKE_TUPLE: 2,
    Op.MAKE_MAP: 2,
    Op.MAKE_LAMBDA: 2,
    Op.MAKE_CLASS: 2,
    # Op.MAKE_INTERFACE: 2,
    # Op.MAKE_EXCEPTION: 2,
    Op.LOAD_VALUE: 2,
    Op.LOAD_LOCAL: 2,
    Op.STORE_LOCAL: 2,
    Op.DELETE_LOCAL: 2,
    Op.LOAD_NONLOCAL: 3,
    Op.STORE_NONLOCAL: 3,
}

class Unit(enum.Enum):
    FALSE = 0
    TRUE = 1
    NONE = 2

class Bytecode(bytearray):
    def __repr__(self):
        contents = ''.join((fr'\x{hex(byte)[2:]:0>2}' for byte in self))
        return f"Bytecode(b'{contents}')"

    @staticmethod
    def assemble(instructions):
        bytecode = Bytecode()
        for instruction in instructions:
            op = instruction[0]
            oplength = OP_LENGTHS.get(op, 1)
            if oplength == len(instruction):
                bytecode.append(op._value_)
                bytecode.extend(instruction[1:])
        return bytecode

    def disassemble(self):
        ip = 0
        while ip < len(self):
            op = Op(self[ip])
            oplength = OP_LENGTHS.get(op, 1)
            nextip = ip + oplength
            args = self[ip+1:nextip]
            ip = nextip
            yield (op,) + tuple(args)
