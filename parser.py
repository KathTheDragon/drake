import ast
from .ast import Precedence, ASTNode, BinaryOp, Primary
from .exceptions import DrakeParserError

class Parser():
    def __init__(self, tokens):
        self.tokens = tokens
        self.next = next(tokens)
        self.current = None

        self.ast = []

        self.parse()
    

    def parse(self):
        self.expression()

    def expression(self):
        return self.parsePrecedence(Precedence.ASSIGNMENT)

    def getRule(self, token):
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
        self.parsePrecedence(Precedence.UNARY)

    def binary(self):
        operator = self.current

        rule_precedence = self.getRule(operator).precedence
        self.parsePrecedence(rule_precedence + 1)

        right = self.ast.pop()
        if not isinstance(right, ASTNode):
            right = Primary(right)

        left = self.ast.pop()
        if not isinstance(left, ASTNode):
            left = Primary(left)

        node = BinaryOp(left, operator, right)

        self.ast.append(node)

    def primary(self):
        self.ast.append(self.current)

    def parsePrecedence(self, precedence):
        self.advance()

        prefix = self.getRule(self.current).prefix
        if prefix is None:
            raise DrakeParserError(f'expected expression, got `{self.current.value}`', self.current)

        prefix()

        while precedence <= self.getRule(self.next).precedence:
            self.advance()
            self.getRule(self.current).infix()


    def advance(self):
        self.current = self.next
        try:
            self.next = next(self.tokens)
        except StopIteration:
            self.next = None

    def expect(self, value):
        if self.next.value == value:
            self.advance()
        else:
            raise DrakeParserError(f'expected `{value}`, got {self.next.value}', self.next)