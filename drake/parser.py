import ast
from .ast import Precedence, ASTNode, UnaryOp, BinaryOp, Primary, Assignment
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
            '(':      Rule(self.grouping, None,            Precedence.NONE      ),
            '!':      Rule(self.unary,    None,            Precedence.UNARY     ),
            'not':    Rule(self.unary,    None,            Precedence.UNARY     ),
            '=':      Rule(None,          self.assignment, Precedence.ASSIGNMENT),
            '+=':     Rule(None,          self.assignment, Precedence.ASSIGNMENT),
            '-=':     Rule(None,          self.assignment, Precedence.ASSIGNMENT),
            '*=':     Rule(None,          self.assignment, Precedence.ASSIGNMENT),
            '/=':     Rule(None,          self.assignment, Precedence.ASSIGNMENT),
            '->':     Rule(None,          self.binary,     Precedence.ASSIGNMENT),
            ':':      Rule(None,          self.binary,     Precedence.ASSIGNMENT),
            '-':      Rule(self.unary,    self.binary,     Precedence.ADD       ),
            '+':      Rule(None,          self.binary,     Precedence.ADD       ),
            '/':      Rule(None,          self.binary,     Precedence.MULT      ),
            '*':      Rule(None,          self.binary,     Precedence.MULT      ),
            '%':      Rule(None,          self.binary,     Precedence.MULT      ),
            '**':     Rule(None,          self.binary,     Precedence.EXP       ),
            '..':     Rule(None,          self.binary,     Precedence.RANGE     ),
            'in':     Rule(None,          self.binary,     Precedence.EQUALITY  ),
            'not in': Rule(None,          self.binary,     Precedence.EQUALITY  ),
            'is':     Rule(None,          self.binary,     Precedence.EQUALITY  ),
            'is not': Rule(None,          self.binary,     Precedence.EQUALITY  ),
            '==':     Rule(None,          self.binary,     Precedence.EQUALITY  ),
            '!=':     Rule(None,          self.binary,     Precedence.EQUALITY  ),
            '>':      Rule(None,          self.binary,     Precedence.COMPARISON),
            '<':      Rule(None,          self.binary,     Precedence.COMPARISON),
            '>=':     Rule(None,          self.binary,     Precedence.COMPARISON),
            '<=':     Rule(None,          self.binary,     Precedence.COMPARISON),
            '>>':     Rule(None,          self.binary,     Precedence.SHIFT     ),
            '<<':     Rule(None,          self.binary,     Precedence.SHIFT     ),
            'and':    Rule(None,          self.binary,     Precedence.AND       ),
            'or':     Rule(None,          self.binary,     Precedence.OR        ),
            'xor':    Rule(None,          self.binary,     Precedence.XOR       ),
            '&':      Rule(None,          self.binary,     Precedence.BIT_AND   ),
            '|':      Rule(None,          self.binary,     Precedence.BIT_OR    ),
            '^':      Rule(None,          self.binary,     Precedence.BIT_XOR   ),
        }.get(token.value, Rule(None, None, Precedence.NONE))

    def assignment(self):
        operator = self.current

        self.parsePrecedence(Precedence.ASSIGNMENT)

        expression = self.ast.pop()
        if not isinstance(expression, ASTNode):
            expression = Primary(expression)

        name = self.ast.pop()
        if not isinstance(name, ASTNode):
            name = Primary(name)

        self.ast.append(node)
        node = Assignment(name, operator, expression)

    def grouping(self):
        self.expression()
        self.expect(')')

    def unary(self):
        operator = self.current

        self.parsePrecedence(Precedence.UNARY)

        operand = self.ast.pop()
        if not isinstance(operand, ASTNode):
            operand = Primary(operand)

        node = UnaryOp(operator, operand)
        self.ast.append(node)

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
            raise DrakeParserError(f'expected `{value}`, got `{self.next.value}`', self.next)
