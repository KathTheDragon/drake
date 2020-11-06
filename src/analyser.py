from dataclasses import dataclass
from . import parser, scopes, types, values
from .ast import *

@dataclass
class Analyser(parser.Parser):
    def parse(self):
        scope = scopes.Scope()
        registry = values.Registry()
        return super().parse(scope=scope, registry=registry)

    # Node functions
    def passnode(self, scope, registry):
        index = registry.register(values.None_)
        return ValueNode(types.None_, index)

    def continuenode(self, scope, registry):
        index = registry.register(values.Continue)
        return ValueNode(types.Continue, index)

    def breaknode(self, scope, registry):
        index = registry.register(values.Break)
        return ValueNode(types.Break, index)

    def nonenode(self, scope, registry):
        index = registry.register(values.None_)
        return ValueNode(types.None_, index)

    def boolnode(self, value, scope, registry):
        index = registry.register(values.Boolean.parse(value))
        return ValueNode(types.Boolean, index)

    def numbernode(self, value, scope, registry):
        index = registry.register(values.Number.parse(value))
        return ValueNode(types.Number, index)

    def stringnode(self, value, scope, registry):
        index = registry.register(values.String.parse(value))
        return ValueNode(types.String, index)
