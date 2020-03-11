from dataclasses import dataclass, field

## Classes
@dataclass
class Type:
    name: str
    params: tuple = ()

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return Type(self.name, item)
        else:
            return Type(self.name, (item,))

## Exceptions
@dataclass
class TypeMismatch(Exception):
    expected: Type
    actual: Type
