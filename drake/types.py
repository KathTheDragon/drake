from dataclasses import dataclass, field

## Classes
@dataclass
class Type:
    name: str
    params: tuple = ()

## Exceptions
@dataclass
class TypeMismatch(Exception):
    expected: Type
    actual: Type
