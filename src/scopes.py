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
    assigned: bool = False
    const: bool = False

    def rebind(self, type, assignment=True, const=False):
        from .types import typecheck
        typecheck(self.type, type)
        if self.assigned and assignment and self.const:
            raise CannotRebindConstant(self.name)
        elif self.const and not const:
            raise CannotRebindConstant(self.name)
        else:
            self.assigned = assignment
            self.const = const

@dataclass
class Scope:
    def __init__(self, *bindings, parent=None):
        self.bindings = list(bindings)
        if parent is None:
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

    def bind(self, name, type, assignment=True, const=False):
        for index, binding in enumerate(self.bindings):
            if binding.name == name:
                binding.rebind(type, assignment, const)
                return index
        else:
            index = len(self.bindings)
            binding = Binding(name, type, assignment, const)
            self.bindings.append(binding)
            return index

    def child(self, *bindings):
        return Scope(bindings, parent=self)

class _Builtins(Scope):
    def __init__(self, *bindings):
        self.bindings = bindings

    def index(self, name):
        index, _ = super().index(name, local=True)
        return index, -1

builtins = _Builtins(

)