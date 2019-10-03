from dataclasses import dataclass
from .lexer import Token


class ASTNode():
    def pprint(self):
        raise NotImplementedError


@dataclass
class Primary(ASTNode):
    value: Token

    def pprint(self):
        return f'{self.value.type} {self.value.value}'

@dataclass
class BinaryOp(ASTNode):
    left: ASTNode
    operator: Token
    right: ASTNode

    def pprint(self):
        indent = lambda s: '\n'.join('  '+line for line in s.splitlines())
        left = self.left.pprint()
        right = self.right.pprint()
        br = ''
        if not (type(self.left) == type(self.right) == Primary):
            left = indent(left)
            right = indent(right)
            br = '\n'
        return f'Binary {self.operator.value}({br}{left},{br}{right}{br})'


class Precedence:
    NONE       = 0
    ASSIGNMENT = 1   # =
    OR         = 2   # or
    AND        = 3   # and
    EQUALITY   = 4   # == !=
    COMPARISON = 5   # < > <= >=
    ADD_SUB    = 6   # + -
    MULT_DIV   = 7   # * /
    UNARY      = 8   # ! -
    CALL       = 9   # . () []
    PRIMARY    = 10