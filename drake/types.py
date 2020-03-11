from dataclasses import dataclass, field
from itertools import zip_longest

## Exceptions
@dataclass
class TypeMismatch(Exception):
    expected: 'Type'
    actual: 'Type'

## Classes
@dataclass
class Type:
    name: str
    params: tuple = field(default=(), compare=False)

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return Type(self.name, item)
        else:
            return Type(self.name, (item,))

## Functions
def typecheck(expected, actual):
    if expected.name != actual.name:
        raise TypeMismatch(expected, actual)
    for expparam, actparam in zip_longest(expected.params, actual.params):
        typecheck(expparam, actparam)

## Types
Type_ = Type('Type')
None_ = Type('None')
Boolean = Type('Boolean')
Number = Type('Number')
String = Type('String')
MutableString = Type('MutableString')
List = Type('List')
MutableList = Type('MutableList')
Tuple = Type('Tuple')
MutableTuple = Type('MutableTuple')
Mapping = Type('Mapping')
MutableMapping = Type('MutableMapping')
Block = Type('Block')
Lambda = Type('Lambda')
Function = Type('Function')
Iterator = Type('Iterator')
Module = Type('Module')

strings = (String, MutableString)
lists = (List, MutableList)
tuples = (Tuple, MutableTuple)
mappings = (Mapping, MutableMapping)
subscriptable = strings + lists + tuples + mappings
mutable = (
    MutableString,
    MutableList,
    MutableTuple,
    MutableMapping
)
exceptions = (

)
builtin = (
    Type_,
    None_,
    Boolean,
    Number,
    Block,
    Lambda,
    Function,
    Iterator,
    Module,
) + subscriptable + exceptions
