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

def pairnode(node, scope, values):
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
