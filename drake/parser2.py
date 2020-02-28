from dataclasses import dataclass, field
from typing import Callable, Generic, Iterator, List, Tuple, TypeVar, Union
from .parsetree import *

## Types
Source = List[str]
ParseFunc = Callable[[Source, int, int], ParseNode]
N = TypeVar('N')

@dataclass
class ReturnTriple(Generic[N]):
    node: N
    linenum: int
    column: int

    def __iter__(self):
        yield self.node
        yield self.linenum
        yield self.column

def nodelist(item: ParseFunc, source: Source, linenum: int, column: int) -> ReturnTriple[List[ParseNode]]:
    pass

def binop(op: str, operand: ParseFunc, source: Source, linenum: int, column: int) -> ReturnTriple[BinaryOpNode]:
    pass

def program(source: Source, linenum: int, column: int) -> ReturnTriple[BlockNode]:
    pass

def assignment(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def vars(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def expression(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def params(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def vparam(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def kwparam(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def typehint(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def type(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def boolor(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def boolxor(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def booland(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def comparison(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def bitor(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def bitxor(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def bitand(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def bitshift(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def add(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def mult(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def exp(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def unary(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def primary(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def atom(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass

def pair(source: Source, linenum: int, column: int) -> ReturnTriple[ParseNode]:
    pass
