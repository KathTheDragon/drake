# Things the analyser must do:
# - Name resolution: turn names into an index, plus a measure of 'non-locality'; basically how many times an outer scope must be entered to find the binding
# - Type analysis: every expression must be assigned its type so that consistency constraints can be checked
# - Multiple dispatch: sort of as a corollary to the above, expressions that resolve to functions need to determine which definition to use, based on the call signature, and *maybe* also the return type, so far as that can be inferred. Might be a feature to defer, though.
# - Output the AST ready for compiling to bytecode
# Optional features:
# - Compile-time computation: one possible optimisation to the compiled bytecode would be to perform some of the computations statically during this phase - e.g, numeric arithmetic
# - Another optimisation could be to alter the program structure to eliminate unnecessary elements of the bytecode
import re
from dataclasses import dataclass
from typing import List, Optional
from . import types
from .ast import *
from .scopes import *
from .types import typecheck

## Exceptions
@dataclass
class AttributeNotFound(Exception):
    attribute: str

## Normalisation
def normalise_string(string):
    return string[1:-1]  # Also needs escape processing

def normalise_number(number):
    number = number.replace('_', '')
    if number.startswith('0b') or number.startswith('0o') or number.startswith('0x'):
        return str(int(number)), '', '', ''
    else:
        match = re.match(rf'(?P<integer>[0-9]+)(?:\.(?P<fractional>[0-9]+))?(?:[eE](?P<exponent>[+-]?[0-9]+))?(?P<imagunit>[jJ])?')
        integer, fractional, exponent, imagunit = match.groups(default='')
        integer = integer.lstrip('0') or '0'
        fractional = fractional.rstrip('0')
        if exponent.startswith('+'):
            exponent = exponent.lstrip('+0')
        elif exponent.startswith('-'):
            exponent = exponent.lstrip('-0')
            if exponent:
                exponent = '-' + exponent
        else:
            exponent = exponent.lstrip('0')
        imagunit = imagunit.lower()
        return integer, fractional, exponent, imagunit

## Functions
def analyse(node, scope, values):
    if isinstance(node, list):
        return [analyse(item, scope, values) for item in node]
    elif node is None:
        return passnode(node, scope, values)
    else:
        return globals()[node.__class__.__name__.lower()](node, scope, values)

def identifiernode(node, scope, values):
    index, _scope = scope.index(node.name)
    type = scope.get(index, _scope).type
    return IdentifierNode(type, index, _scope)

def stringnode(node, scope, values):
    value = normalise_string(node.value)
    if value in values:
        index = values.index(value)
    else:
        index = len(values)
        values.append(node.value)
    return ValueNode(types.String, index)

def numbernode(node, scope, values):
    value = normalise_number(node.value)
    if value in values:
        index = values.index(value)
    else:
        index = len(values)
        values.append(value)
    return ValueNode(types.Number, index)

def booleannode(node, scope, values):
    value = (node.value == 'true')
    if value in values:
        index = values.index(value)
    else:
        index = len(values)
        values.append(value)
    return ValueNode(types.Boolean, index)

def nonenode(node, scope, values):
    if None in values:
        index = values.index(None)
    else:
        index = len(values)
        values.append(None)
    return ValueNode(types.None_, index)

def range(node, scope, values):
    scope = scope.child()
    start = analyse(node.start, scope, values)
    type = start.type
    if node.end is not None:
        end = analyse(node.end, scope, values)
        typecheck(type, end.type)
    else:
        end = None
    if node.step is not None:
        step = analyse(node.step, scope, values)
        typecheck(types.Number, step.type)
    else:
        step = None
    return RangeNode(types.List[type], start, end, step)

def listnode(node, scope, values):
    items = analyse(node.items, scope.child(), values)
    type = items[0].type
    for item in items:
        typecheck(type, item.type)
    return ListNode(types.List[type], items)

def tuplenode(node, scope, values):
    items = analyse(node.items, scope.child(), values)
    types = [item.type for item in items]
    return TupleNode(types.Tuple[*types], items)

def pairnode(node, scope, values):
    return analyse(node.key, scope, values), analyse(node.value, scope, values)

def mappingnode(node, scope, values):
    items = analyse(node.items, scope.child(), values)
    keytype = items[0][0].type
    valuetype = items[0][1].type
    for item in items:
        key, value = item
        typecheck(keytype, key.type)
        typecheck(valuetype, value.type)
    return MappingNode(types.Mapping[keytype, valuetype], items)

def blocknode(node, scope, values):
    scope = scope.child()
    type = None
    expressions = analyse(node.expressions, scope, values)
    for expression in expressions:
        if isinstance(expression, (ReturnNode, YieldNode, YieldFromNode)):
            if type is None:
                type = expression.type
            else:
                typecheck(type, expression.type)
    if type is None:
        type = types.None_
    return BlockNode(types.Block[type], expressions, scope)

def subscriptnode(node, scope, values):
    container = analyse(node.container, scope, values)
    subscript = analyse(node.subscript, scope, values)
    contype = container.type
    subtype, = subscript.type.params
    if contype in types.subscriptable:
        if contype in types.mappings:
            keytype, valuetype = contype.params
            typecheck(keytype, subtype)
            if isinstance(subscript, RangeNode) or len(subscript.items) > 1:
                type = types.List[valuetype]
            else:
                type = valuetype
        else:
            typecheck(types.Number, subtype)
            if contype in types.strings:
                type = contype
            elif isinstance(subscript, RangeNode) or len(subscript.items) > 1:
                type = contype
            else:
                type = contype.params
    elif contype.name in types.builtin:
        raise types.TypeMismatch(types.subscriptable, contype)
    else:
        raise types.TypeMismatch(types.subscriptable, contype)  # Temporary

def lookupnode(node, scope, values):
    obj = analyse(node.obj, scope, values)
    attribute = node.attribute.name
    namespace = obj.type.namespace
    index, _scope = namespace.index(attribute)
    if _scope != 0:
        raise AttributeNotFound(attribute)
    type = namespace.get(index, 0).type
    return LookupNode(type, obj, index)

def callnode(node, scope, values):
    pass

def unaryopnode(node, scope, values):
    pass

def binaryopnode(node, scope, values):
    pass

def lambdanode(node, scope, values):
    pass

def iternode(node, scope, values):
    pass

def donode(node, scope, values):
    pass

def objectnode(node, scope, values):
    pass

def enumnode(node, scope, values):
    pass

def modulenode(node, scope, values):
    pass

def exceptionnode(node, scope, values):
    pass

def mutablenode(node, scope, values):
    pass

def thrownode(node, scope, values):
    pass

def returnnode(node, scope, values):
    pass

def yieldnode(node, scope, values):
    pass

def yieldfromnode(node, scope, values):
    pass

def breaknode(node, scope, values):
    pass

def continuenode(node, scope, values):
    pass

def passnode(node, scope, values):
    pass

def ifnode(node, scope, values):
    pass

def casenode(node, scope, values):
    pass

def catchnode(node, scope, values):
    pass

def trynode(node, scope, values):
    pass

def fornode(node, scope, values):
    pass

def whilenode(node, scope, values):
    pass

def typenode(node, scope, values):
    pass

def declarationnode(node, scope, values):
    pass

def targetnode(node, scope, values):
    pass

def assignmentnode(node, scope, values):
    pass
