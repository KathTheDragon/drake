import ast
from .ast import (
    Precedence,
    ASTNode,
    UnaryOpNode,
    BinaryOpNode,
    PrimaryNode,
    LiteralNode,
    IdentifierNode,
    AssignmentNode,
    BlockNode
)
from .lexer import Token
from .exceptions import DrakeParserError


def makeASTNode(expression):
    if isinstance(expression, Token):
        if expression.type == 'IDENTIFIER':
            return IdentifierNode(expression)
        elif expression.type in ('STRING', 'NUMBER'):
            return LiteralNode(expression)
    else:
        return PrimaryNode(expression)

class Parser():
    def __init__(self, tokens):
        self.tokens = tokens
        self.next = next(tokens)
        self.current = None

        self.stack = []
        self.ast = self.parse()


    def parse(self):
        self.block()
        return self.stack.pop()

    def block(self):
        self.maybe(type='NEWLINE')

        self.expression()
        expressions = [self.stack.pop()]

        while self.next.type == 'NEWLINE':
            self.expect(type='NEWLINE')
            if self.next == None:
                break
            elif self.next.value == '}':
                self.advance()
                break

            self.expression()
            expressions.append(self.stack.pop())

        self.stack.append(BlockNode(expressions))

    def expression(self):
        self.parsePrecedence(Precedence.ASSIGNMENT)

    def getRule(self, token):
        from collections import namedtuple
        Rule = namedtuple('Rule', 'prefix infix precedence')

        if token is None:
            return Rule(None, None, Precedence.NONE)

        elif token.type in ('IDENTIFIER', 'STRING', 'NUMBER'):
            return Rule(self.primary, None, Precedence.PRIMARY)

        return {
            '{':      Rule(self.block,    None,            Precedence.NONE      ),
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

        rule_precedence = self.getRule(operator).precedence
        self.parsePrecedence(rule_precedence + 1)

        expression = self.stack.pop()
        if not isinstance(expression, ASTNode):
            expression = makeASTNode(expression)

        target = self.stack.pop()
        if not isinstance(target, ASTNode):
            target = makeASTNode(target)

        if operator.value[0] in '+-*/':
            expression = BinaryOpNode(target, operator, expression)

        node = AssignmentNode(target, expression)
        self.stack.append(node)

    def grouping(self):
        self.expression()
        self.expect(value=')')

    def unary(self):
        operator = self.current

        self.parsePrecedence(Precedence.UNARY)

        operand = self.stack.pop()
        if not isinstance(operand, ASTNode):
            operand = makeASTNode(operand)

        node = UnaryOpNode(operator, operand)
        self.stack.append(node)

    def binary(self):
        operator = self.current

        rule_precedence = self.getRule(operator).precedence
        self.parsePrecedence(rule_precedence + 1)

        right = self.stack.pop()
        if not isinstance(right, ASTNode):
            right = makeASTNode(right)

        left = self.stack.pop()
        if not isinstance(left, ASTNode):
            left = makeASTNode(left)

        node = BinaryOpNode(left, operator, right)
        self.stack.append(node)

    def primary(self):
        self.stack.append(self.current)

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

    def expect(self, value=None, type=None):
        if self.next.value == value:
            self.advance()
        elif self.next.type == type:
            self.advance()
        else:
            raise DrakeParserError(f'expected `{type} {value}`, got `{self.next.type} {self.next.value}`', self.next)

    def maybe(self, value=None, type=None):
        if self.next.value == value:
            self.advance()
        elif self.next.type == type:
            self.advance()
