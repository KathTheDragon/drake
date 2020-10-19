from dataclasses import dataclass, field
from itertools import zip_longest
from .scopes import Scope, Binding

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
    mutable: bool = field(default=False, compare=False)
    namespace: Scope = field(default_factory=Scope, compare=False)

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return Type(self.name, item, self.mutable, self.namespace)
        else:
            return Type(self.name, (item,), self.mutable, self.namespace)

## Types
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
subscriptable = strings + lists + tuples + mappings
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
) + subscriptable + exceptions

## Functions
def typecheck(expected, actual):
    if expected.name != actual.name:
        raise TypeMismatch(expected, actual)
    for expparam, actparam in zip_longest(expected.params, actual.params):
        typecheck(expparam, actparam)

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
        raise TypeMismatch((String, List, Tuple, Mapping), type)
    else:
        return mutabletuple
