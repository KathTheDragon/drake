# Things the analyser must do:
# - Name resolution: turn names into an index, plus a measure of 'non-locality'; basically how many times an outer scope must be entered to find the binding
# - Type analysis: every expression must be assigned its type so that consistency constraints can be checked
# - Multiple dispatch: sort of as a corollary to the above, expressions that resolve to functions need to determine which definition to use, based on the call signature, and *maybe* also the return type, so far as that can be inferred. Might be a feature to defer, though.
# - Output the AST ready for compiling to bytecode
# Optional features:
# - Compile-time computation: one possible optimisation to the compiled bytecode would be to perform some of the computations statically during this phase - e.g, numeric arithmetic
# - Another optimisation could be to alter the program structure to eliminate unnecessary elements of the bytecode
from dataclasses import dataclass
from typing import List, Optional
from .ast import *
from .scopes import *
from .types import *

## Exceptions

## Functions
def analyse(node, scope, values):
    return globals()[node.__class__.__name__.lower()](node, scope, values)

def identifiernode(node, scope):
    pass

def stringnode():
    pass

def numbernode():
    pass

def booleannode():
    pass

def nonenode():
    pass

def pairnode():
    pass

def mappingnode():
    pass

def blocknode():
    pass

def range():
    pass

def listnode():
    pass

def tuplenode():
    pass

def groupingnode():
    pass

def subscriptnode():
    pass

def lookupnode():
    pass

def callnode():
    pass

def unaryopnode():
    pass

def binaryopnode():
    pass

def lambdanode():
    pass

def iternode():
    pass

def donode():
    pass

def objectnode():
    pass

def enumnode():
    pass

def modulenode():
    pass

def exceptionnode():
    pass

def mutablenode():
    pass

def thrownode():
    pass

def returnnode():
    pass

def yieldnode():
    pass

def yieldfromnode():
    pass

def breaknode():
    pass

def continuenode():
    pass

def passnode():
    pass

def ifnode():
    pass

def casenode():
    pass

def catchnode():
    pass

def trynode():
    pass

def fornode():
    pass

def whilenode():
    pass

def typenode():
    pass

def declarationnode():
    pass

def targetnode():
    pass

def assignmentnode():
    pass
