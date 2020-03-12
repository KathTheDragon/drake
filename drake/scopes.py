from dataclasses import dataclass
from typing import List, Optional

## Exceptions
@dataclass
class NameNotFound(Exception):
    name: str
    local: Optional[bool] = None

@dataclass
class NameNotAssigned(Exception):
    name: str

@dataclass
class CannotRebindConstant(Exception):
    name: str

## Classes
@dataclass
class Binding:
    name: str
    type: 'Type'
    isassigned: bool = False
    const: bool = False

    def rebind(self, type, assignment=True):
        from .types import typecheck
        typecheck(self.type, type)
        if self.isassigned and assignment and self.const:
            raise CannotRebindConstant(self.name)
        else:
            self.assigned = assignment

@dataclass
class Scope:
    def __init__(self, *bindings, parent=_MISSING):
        self.bindings = list(bindings)
        if parent is _MISSING:
            parent = builtins
        self.parent = parent

    def __getitem__(self, item):
        binding = self.bindings[item]
        return binding

    def index(self, name, local=None):
        if local != False:
            for index, binding in enumerate(self.bindings):
                if binding.name == name:
                    return index, 0
        if local != True:
            if self.parent:
                try:
                    index, scope = self.parent.index(name)
                except NameNotFound as e:
                    e.local = local
                    raise e
                if scope != -1:
                    scope += 1
                return index, scope
        raise NameNotFound(name, local)

    def get(self, index, scope):
        if scope == -1:
            return builtins[index]
        elif scope == 0:
            return self[index]
        else:
            return self.parent.get(index, scope-1)

    def getname(self, name, local=None):
        return self.get(*self.index(name, local))

    def bind(self, name, type, assignment=True, local=True, const=False):
        try:
            index, scope = self.index(name, local)
            binding = self.get(index, scope)
            binding.rebind(type, assignment)
            return index, scope
        except NameNotFound:
            if local == False:
                raise
            index = len(self.bindings)
            binding = Binding(name, type, assignment, const)
            self.bindings.append(binding)
            return index, 0

    def child(self, *bindings):
        return Scope(bindings, parent=self)

class _Builtins(Scope):
    def index(self, name):
        index, scope = super().index(name)
        return index, -1

builtins = _Builtins(

)
