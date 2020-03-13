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
from . import types, scopes
from .ast import *
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

## Helper Functions
def unpack(vars, type):
    if not vars:
        raise ValueError('vars cannot be empty')
    if type in types.tuples:
        if len(vars) == len(type.params):
            return zip(vars, type.params)
        else:
            raise ValueError('incorrect number of values to unpack')
    else:
        raise types.TypeMismatch(types.tuples, type)

## Analyser Functions
def analyse(node, scope, values):
    if node is None:
        return passnode()
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
    scope = scope.child()
    items = [analyse(item, scope, values) for item in node.items]
    type = items[0].type
    for item in items:
        typecheck(type, item.type)
    return ListNode(types.List[type], items)

def tuplenode(node, scope, values):
    scope = scope.child()
    items = [analyse(item, scope, values) for item in node.items]
    types = [item.type for item in items]
    return TupleNode(types.Tuple[*types], items)

def pairnode(node, scope, values):
    return analyse(node.key, scope, values), analyse(node.value, scope, values)

def mappingnode(node, scope, values):
    scope = scope.child()
    items = [analyse(item, scope, values) for item in node.items]
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
    expressions = [analyse(expression, scope, values) for expression in node.expressions]
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
    expression = analyse(node.expression, scope, values)
    if expression.type in types.strings:
        yieldtype = expression.type
    elif expression.type in types.mappings:
        yieldtype = types.Tuple[*expression.type.params]
    elif expression.type in types.iterable:
        yieldtype, = expression.type.params
    else:
        raise types.TypeMismatch(types.iterable, expression.type)
    return IterNode(types.Iterator[yieldtype], expression)

def mutablenode(node, scope, values):
    expression = analyse(node.expression, scope, values)
    if isinstance(expression, ObjectNode):
        objecttype, = expression.type.params
        objecttype = types.Type(type.name, type.params, True, type.namespace)
        type = types.Type_[objecttype]
    else:
        type = types.make_mutable(expression.type)
    return MutableNode(type, expression)

def donode(node, scope, values):
    block = blocknode(node.block, scope, values)
    return DoNode(*block.type.params, block)

def objectnode(node, scope, values):
    pass

def enumnode(node, scope, values):
    pass

def modulenode(node, scope, values):
    pass

def exceptionnode(node, scope, values):
    pass

def thrownode(node, scope, values):
    expression = analyse(node.expression, scope, values)
    return ThrowNode(expression.type, expression)

def returnnode(node, scope, values):
    expression = analyse(node.expression, scope, values)
    return ReturnNode(expression.type, expression)

def yieldnode(node, scope, values):
    expression = analyse(node.expression, scope, values)
    return YieldNode(expression.type, expression)

def yieldfromnode(node, scope, values):
    expression = analyse(node.expression, scope, values)
    itertype = expression.type
    if itertype in types.strings:
        type = itertype
    elif itertype in types.mappings:
        type = types.Tuple[*itertype.params]
    elif itertype in types.iterable:
        type, = itertype.params
    else:
        raise types.TypeMismatch(types.iterable, itertype)
    return YieldFromNode(type, expression)

def breaknode(node=None, scope=None, values=None):
    return BreakNode(types.None_)

def continuenode(node=None, scope=None, values=None):
    return ContinueNode(types.None_)

def passnode(node=None, scope=None, values=None):
    return PassNode(types.None_)

def ifnode(node, scope, values):
    scope = scope.child()
    condition = analyse(node.condition, scope, values)
    then = analyse(node.then, scope, values)
    default = analyse(node.default, scope, values)
    # Typecheck condition: requires a builtin function (boolean? Boolean.new? truth?)
    if not isinstance(default, PassNode):
        typecheck(then.type, default.type)
    return IfNode(then.type, condition, then, default)

def casenode(node, scope, values):
    scope = scope.child()
    value = analyse(node.value, scope, values)
    cases = mappingnode(node.cases, scope, values)
    default = analyse(node.default, scope, values)
    valuetype, returntype = cases.type.params
    typecheck(valuetype, value.type)
    if not isinstance(default, PassNode):
        typecheck(returntype, default.type)
    return CaseNode(returntype, value, cases.items, default)

def catchnode(node, scope, values):
    exception = identifiernode(node.exception, scope, values)
    scope = scope.child()
    if node.name is not None:
        name = node.name.name
        type, = exception.type.params
        scope.bind(name, type, True)
    body = analyse(node.body, scope, values)
    return (exception, body)

def trynode(node, scope, values):
    body = analyse(node.body, scope, values)
    catches = [catchnode(catch, scope, values) for catch in node.catches]
    finally_ = analyse(node.finally_, scope, values)
    type = body.type
    for _, catchbody in catches:
        typecheck(type, catchbody.type)
    typecheck(types.None_, finally_.type)
    return TryNode(type, body, catches, finally_)

def fornode(node, scope, values):
    container = analyse(node.container, scope, values)
    if container.type in types.strings:
        type = container.type
    elif container.type in types.mappings:
        type = types.Tuple[*container.type.params]
    elif container.type in types.iterable:  # Needs to be aware about custom iterable types
        type, = container.type.params
    else:
        raise types.TypeMismatch(types.iterable, container.type)
    scope = scope.child()
    vars = node.vars
    if not isinstance(vars, list):
        scope.bind(vars.name, type, True)
    else:
        for var, vartype in unpack(vars, type):
            scope.bind(var.name, vartype, True)
    body = blocknode(node.body, scope, values)
    return ForNode(*body.type.params, container, body)

def whilenode(node, scope, values):
    scope = scope.child()
    condition = analyse(node.condition, scope, values)
    body = blocknode(node.body, scope, values)
    # Typecheck condition: see ifnode
    return ForNode(*body.type.params, condition, body)

def typenode(node, scope, values):
    type = scope.getname(node.type)
    params = [typenode(param, scope, values) for param in node.params]
    if type != types.Type_:
        raise types.TypeMismatch(types.Type_, type)
    return type[*params]

def declarationnode(node, scope, values):
    type = typenode(node.typehint, scope, values)
    name = node.name.name
    scope.bind(name, type, False, const=node.const)
    return passnode()

def targetnode(node, scope, values):
    if node.type is None:
        type = None
    else:
        type = typenode(node.type, scope, values)
    return (node.name, type, node.mode != 'nonlocal', node.mode == 'const')

def assignmentnode(node, scope, values):
    expression = analyse(node.expression, scope, values)
    if not isinstance(node.targets, list):
        name, type, local, const = targetnode(node.targets, scope, values)
        if type is None:
            type = expression.type
        else:
            typecheck(type, expression.type)
        index, _scope = scope.bind(name, type, True, local, const)
        targets = IdentifierNode(type, index, _scope)
    else:
        targets = []
        for target, targettype in unpack(node.targets, expression.type):
            name, type, local, const = targetnode(target, scope, values)
            if type is None:
                type = targettype
            else:
                typecheck(type, targettype)
            index, _scope = scope.bind(name, type, True, local, const)
            targets.append(IdentifierNode(type, index, _scope))
    return AssignmentNode(expression.type, targets, expression)
