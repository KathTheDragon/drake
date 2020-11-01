from dataclasses import dataclass
from . import parser, scopes, types
from .ast import *

@dataclass
class Analyser(parser.Parser):
    def parse(self):
        scope = scopes.Scope()
        values = []
        return super().parse(scope=scope, values=values)

    # Node functions
