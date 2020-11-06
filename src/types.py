from dataclasses import dataclass, field
from itertools import zip_longest
from .scopes import Scope, Binding

## Exceptions
class InvalidType(Exception):
    def __init__(self, type=None):
        if type is not None:
            super().__init__(str(type))
        else:
            super().__init__('no type given')

@dataclass
class TypeMismatch(Exception):
    actual: 'Type'
    expected: 'Type'

## Classes
@dataclass
class Type:
    name: str
    params: tuple = field(default=(), compare=False)
    mutable: bool = field(default=False, compare=False)
    namespace: Scope = field(default_factory=Scope, compare=False)

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return Type(self.name, item, self.mutable, self.namespace)
        else:
            return Type(self.name, (item,), self.mutable, self.namespace)

## Internal Types
Break = Type('Break')
Continue = Type('Continue')

## External Types
Type_ = Type('Type')
None_ = Type('None')
Boolean = Type('Boolean')
Number = Type('Number')
String = Type('String')
MutableString = Type('MutableString', mutable=True)
List = Type('List')
MutableList = Type('MutableList', mutable=True)
Tuple = Type('Tuple')
MutableTuple = Type('MutableTuple', mutable=True)
Mapping = Type('Mapping')
MutableMapping = Type('MutableMapping', mutable=True)
Block = Type('Block')
Lambda = Type('Lambda')
Function = Type('Function')
Iterator = Type('Iterator')
Module = Type('Module')

strings = (String, MutableString)
lists = (List, MutableList)
tuples = (Tuple, MutableTuple)
mappings = (Mapping, MutableMapping)
subscriptable = strings + lists + mappings
iterable = strings + lists + mappings + (Iterator,)
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
) + subscriptable + tuples + exceptions

## Functions
def typecheck(actual, expected):
    if actual.name != expected.name:
        raise TypeMismatch(actual, expected)
    for actparam, expparam in zip_longest(actual.params, expected.params):
        typecheck(actparam, expparam)

def is_subscriptable(type):
    return type in subscriptable  # Needs to be made aware of custom types

def is_iterable(type):
    return type in iterable  # Needs to be made aware of custom types

def make_mutable(type):
    mutabletype = {
        String: MutableString,
        List: MutableList,
        Tuple: MutableTuple,
        Mapping: MutableMapping
    }.get(type, None)
    if mutabletype is None:
        raise TypeMismatch(type, (String, List, Tuple, Mapping))
    else:
        return mutabletuple
