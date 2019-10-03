import ast
from .ast import Precedence, ASTNode, BinaryOp, Primary
from .exceptions import DrakeParserError

class Parser():
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = next(tokens)
        self.next = next(tokens)
        self.previous = None

        self.ast = []

        self.parse()
    

    def parse(self):
        self.expression()

    def expression(self):
        return self.parse_precedence(Precedence.ASSIGNMENT)

    def get_rule(self, token):
        from collections import namedtuple
        Rule = namedtuple('Rule', 'prefix infix precedence')

        if token is None:
            return Rule(None, None, Precedence.NONE)

        elif token.type in ('IDENTIFIER', 'STRING', 'NUMBER'):
            return Rule(self.primary, None, Precedence.PRIMARY)

        return {
            '(':  Rule(self.grouping, None,        Precedence.NONE      ),
            '-':  Rule(self.unary,    self.binary, Precedence.ADD_SUB   ),
            '+':  Rule(None,          self.binary, Precedence.ADD_SUB   ),
            '/':  Rule(None,          self.binary, Precedence.MULT_DIV  ),
            '*':  Rule(None,          self.binary, Precedence.MULT_DIV  ),
            '==': Rule(None,          self.binary, Precedence.COMPARISON),
            '!=': Rule(None,          self.binary, Precedence.COMPARISON),
        }.get(token.value, Rule(None, None, Precedence.NONE))

    def grouping(self):
        self.expression()
        self.expect(')')

    def unary(self):
        self.parse_precedence(Precedence.UNARY)

    def binary(self):
        operator = self.previous

        rule_precedence = self.get_rule(operator).precedence
        self.parse_precedence(rule_precedence + 1)

        right = self.ast.pop()
        if not isinstance(right, ASTNode):
            right = Primary(right)

        left = self.ast.pop()
        if not isinstance(left, ASTNode):
            left = Primary(left)

        node = BinaryOp(left, operator, right)

        self.ast.append(node)

    def primary(self):
        self.ast.append(self.previous)

    def parse_precedence(self, precedence):
        self.advance()

        prefix = self.get_rule(self.previous).prefix
        if prefix is None:
            raise DrakeParserError(f'expected expression, got `{self.previous.value}`', self.previous)

        prefix()

        while precedence <= self.get_rule(self.current).precedence:
            self.advance()
            self.get_rule(self.previous).infix()


    def advance(self):
        self.previous = self.current
        self.current = self.next
        try:
            self.next = next(self.tokens)
        except StopIteration:
            self.current = None

    def expect(self, value):
        if self.current.value == value:
            self.advance()
        else:
            raise DrakeParserError(f'expected `{value}`, got {self.current.value}', self.current)