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
from .ast import *
from .scopes import *
from .types import *

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
    return globals()[node.__class__.__name__.lower()](node, scope, values)

def identifiernode(node, scope, values):
    pass

def stringnode(node, scope, values):
    pass

def numbernode(node, scope, values):
    pass

def booleannode(node, scope, values):
    pass

def nonenode(node, scope, values):
    pass

def mappingnode(node, scope, values):
    pass

def blocknode(node, scope, values):
    pass

def range(node, scope, values):
    pass

def listnode(node, scope, values):
    pass

def tuplenode(node, scope, values):
    pass

def subscriptnode(node, scope, values):
    pass

def lookupnode(node, scope, values):
    pass

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
