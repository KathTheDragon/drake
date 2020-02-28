from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Tuple, Union
from .parsetree import *
from .lexer import Token, lex

## Constants
EOF = Token('EOF', 'eof', 0, 0)
LITERAL = (
    'STRING',
    'INTEGER',
    'DECIMAL',
    'IMAG_INTEGER',
    'IMAG_DECIMAL',
    'BOOLEAN',
    'NONE'
)
Values = Union[str, Tuple[str]]

## Exceptions
class DrakeSyntaxError(Exception):
    def __init__(self, error, token):
        value = token.value
        linenum = token.linenum
        column = token.column
        super().__init__(f'{error}: {value!r} @ {linenum}:{column}')
        self.error = error
        self.value = value
        self.linenum = linenum
        self.column = column

def expectedToken(expected, token):
    return DrakeSyntaxError(f'expected {expected!r}', token)

def unexpectedToken(token):
    return DrakeSyntaxError(f'unexpected {token.type.lower()}', token)

class DrakeCompilerWarning(Warning):
    def __init__(self, warning, token):
        value = token.value
        linenum = token.linenum
        column = token.column
        super().__init__(f'{warning}: {value!r} @ {linenum}:{column}')
        self.warning = warning
        self.value = value
        self.linenum = linenum
        self.column = column

## Classes
@dataclass
class DescentParser:
    source: str
    tokens: Iterator[Token] = field(init=False, default=iter([]))
    current: Token = field(init=False, default=EOF)
    log: List[Exception] = field(init=False, default_factory=list)

    # Basic token functions
    def advance(self) -> None:
        try:
            self.current = next(self.tokens)
        except StopIteration:
            pass

    def pop(self) -> Token:
        token = self.current
        self.advance()
        return token

    def matches(self, type: Values, value: Values=()) -> bool:
        if isinstance(type, str):
            if self.current.type != type:
                return False
        else:
            if self.current.type not in type:
                return False
        if isinstance(value, str):
            return self.current.value == value
        elif value:
            return self.current.value in value
        else:
            return True

    def maybe(self, type: Values, value: Values=()) -> bool:
        if self.matches(type, value):
            self.advance()
            return True
        else:
            return False

    def consume(self, type: Values, value: Values=()) -> None:
        if self.matches(type, value):
            self.advance()
        else:
            raise expectedToken(value or type, self.current)

    # Pattern functions
    def leftassoc(self, func: Callable, operator: Values) -> ParseNode:
        expr = func()
        while self.matches('OPERATOR', operator):
            op = self.pop()
            right = func()
            expr = BinaryOpNode(expr, op, right)
        return expr

    def rightassoc(self, func: Callable, operator: Values) -> ParseNode:
        expr = func()
        if not self.matches('OPERATOR', operator):
            return expr
        op = self.pop()
        right = self.rightassoc(func, operator)
        return BinaryOpNode(expr, op, right)

    def list(self, func: Callable, endtype: str, endvalue: Values=()) -> List[ParseNode]:
        expressions = []
        self.maybe('NEWLINE')
        if self.matches(endtype, endvalue):
            return expressions
        try:
            expressions.append(func())
        except DrakeSyntaxError as e:
            self.log.append(e)
            while not self.matches(('NEWLINE', 'COMMA', endtype)):
                self.advance()
        if self.matches(endtype, endvalue):
            return expressions
        delimiter = self.current.type
        newline = None
        while self.maybe(delimiter):
            if self.matches(endtype, endvalue):
                return expressions
            if newline is None:
                newline = self.matches('NEWLINE')
            if newline:
                self.consume('NEWLINE')
            try:
                expressions.append(func())
            except DrakeSyntaxError as e:
                self.log.append(e)
                while not self.matches((delimiter, endtype)):
                    self.advance()
        self.maybe('NEWLINE')
        return expressions

    # Parsing functions
    def parse(self) -> BlockNode:
        self.tokens = lex(self.source)
        self.advance()
        self.log = []
        program = self.list(self.parseAssignment, 'EOF')
        self.consume('EOF')
        return BlockNode(program)

    def parsePairList(self) -> List[ParseNode]:
        return self.list(self.parsePair, 'RBRACKET')

    def parsePair(self) -> ParseNode:
        expr = self.parseAssignment()
        if not self.maybe('COLON'):
            return expr
        if isinstance(expr, AssignmentNode):
            self.log.append(DrakeSyntaxError('cannot use assignment as a pair key', self.current))
        value = self.parseExpression()
        return PairNode(expr, value)

    def parseAssignList(self) -> List[ParseNode]:
        return self.list(self.parseAssignment, 'RBRACKET')

    def parseAssignment(self) -> ParseNode:
        if self.matches('KEYWORD', ('nonlocal', 'const')):
            mode = self.pop()
            target = self.parseExpression()
            if not self.matches('ASSIGNMENT'):
                self.log.append(unexpectedToken(mode))
                return target
            mode = mode.value
        else:
            mode = ''
            target = self.parseExpression()
            if not self.matches('ASSIGNMENT'):
                return target
        if not isinstance(target, IdentifierNode):
            # Need to fix this to use a more useful token
            self.log.append(DrakeSyntaxError('invalid target for assignment', self.current))
        operator = self.pop()
        expression = self.parseAssignment()
        if operator.value != '=':
            operator.type = 'OPERATOR'
            expression = BinaryOpNode(target, operator, expression)
        if isinstance(expression, (LambdaNode, ObjectNode, ExceptionNode)) and mode != 'const':
            # Need to fix this to use a more useful token
            self.log.append(DrakeCompilerWarning(f'{expression.nodetype.lower()} should be assigned to a constant', operator))
        return AssignmentNode(mode, target, expression)

    def parseExprList(self) -> List[ParseNode]:
        return self.list(self.parseExpression, 'RBRACKET')

    def parseExpression(self) -> ParseNode:
        return self.parseKeyword()

    def parseKeyword(self) -> ParseNode:
        if self.maybe('KEYWORD', 'return'):
            return ReturnNode(self.parseFlow())
        elif self.maybe('KEYWORD', 'yield'):
            return YieldNode(self.parseFlow())
        elif self.maybe('KEYWORD', 'yield from'):
            return YieldFromNode(self.parseFlow())
        elif self.maybe('KEYWORD', 'break'):
            return BreakNode()
        elif self.maybe('KEYWORD', 'continue'):
            return ContinueNode()
        elif self.maybe('KEYWORD', 'object'):
            constructor = self.parseLambda()
            return ObjectNode(constructor.params, constructor.returns)
        else:
            return self.parseFlow()

    def parseFlow(self) -> ParseNode:
        if self.maybe('KEYWORD', 'if'):
            condition = self.parseFlow()
            self.consume('KEYWORD', 'then')
            then = self.parseFlow()
            if self.maybe('KEYWORD', 'else'):
                default = self.parseFlow()
            else:
                default = None
            return IfNode(condition, then, default)
        elif self.maybe('KEYWORD', 'case'):
            value = self.parseCall()
            self.consume('OPERATOR', 'in')
            cases = self.parseFlow()
            if self.maybe('KEYWORD', 'else'):
                default = self.parseFlow()
            else:
                default = None
            return CaseNode(value, cases, default)
        elif self.maybe('KEYWORD', 'for'):
            vars = self.list(self.parseTypehint, 'OPERATOR', 'in')
            for var in vars:
                if isinstance(var, TypehintNode):
                    var = var.expr
                if not isinstance(var, IdentifierNode):
                    self.log.append(DrakeSyntaxError('invalid loop variable', self.current))
            self.consume('OPERATOR', 'in')
            container = self.parseFlow()
            body = self.parseBlock()
            return ForNode(vars, container, body)
        elif self.maybe('KEYWORD', 'while'):
            condition = self.parseFlow()
            body = self.parseBlock()
            return WhileNode(condition, body)
        else:
            return self.parseLambda()

    def parseLambda(self) -> ParseNode:
        expression = self.parseBoolOr()
        if not self.matches('LAMBDA'):
            return expression
        if isinstance(expression, GroupingNode):
            params = [expression.expr]
        elif isinstance(expression, TupleNode):
            params = expression.items
        else:
            params = [expression]
        errors = []
        for param in params:
            if isinstance(param, AssignmentNode):
                self.log.pop()
            elif not isinstance(param, IdentifierNode):
                # Need to fix this to use a more useful token
                errors.append(DrakeSyntaxError('invalid lambda argument', self.current))
        self.log.extend(errors)
        self.advance()
        returns = self.parseLambda()
        return LambdaNode(params, returns)

    def parseBoolOr(self) -> ParseNode:
        return self.rightassoc(self.parseBoolXor, 'or')

    def parseBoolXor(self) -> ParseNode:
        return self.rightassoc(self.parseBoolAnd, 'xor')

    def parseBoolAnd(self) -> ParseNode:
        return self.rightassoc(self.parseComparison, 'and')

    def parseComparison(self) -> ParseNode:
        return self.leftassoc(self.parseRange, ('in','not in','is','is not','==','!=','<','<=','>','>='))

    def parseRange(self) -> ParseNode:
        left = self.parseBitOr()
        if not self.matches('OPERATOR', '..'):
            return left
        operator = self.pop()
        right = self.parseBitOr()
        return BinaryOpNode(left, operator, right)

    def parseBitOr(self) -> ParseNode:
        return self.leftassoc(self.parseBitXor, '|')

    def parseBitXor(self) -> ParseNode:
        return self.leftassoc(self.parseBitAnd, '^')

    def parseBitAnd(self) -> ParseNode:
        return self.leftassoc(self.parseBitShift, '&')

    def parseBitShift(self) -> ParseNode:
        return self.leftassoc(self.parseAdd, ('<<', '>>'))

    def parseAdd(self) -> ParseNode:
        return self.leftassoc(self.parseMult, ('+', '-'))

    def parseMult(self) -> ParseNode:
        return self.leftassoc(self.parseExp, ('*', '/', '%'))

    def parseExp(self) -> ParseNode:
        return self.rightassoc(self.parseTypehint, '**')

    def parseTypehint(self) -> ParseNode:
        if self.matches('OPERATOR', '<'):
            self.advance()
            typehint = self.parseType()
            self.consume('OPERATOR', '>')
            return TypehintNode(typehint, self.parseUnary())
        else:
            return self.parseUnary()

    def parseType(self) -> TypeNode:
        type = self.current
        self.consume('IDENTIFIER')
        if self.matches('LBRACKET', '['):
            params = self.list(self.parseType, 'RBRACKET')
            self.consume('RBACKET', ']')
        else:
            params = []
        return TypeNode(type, params)

    def parseUnary(self) -> ParseNode:
        if not self.matches('OPERATOR', ('not', '!', '-', "*", "**")):
            return self.parseCall()
        operator = self.pop()
        operand = self.parseUnary()
        return UnaryOpNode(operator, operand)

    def parseCall(self) -> ParseNode:
        expr = self.parsePrimary()
        while True:
            if self.maybe('DOT'):
                if not self.matches('IDENTIFIER'):
                    raise DrakeSyntaxError('expected identifier', self.current)
                attribute = IdentifierNode(self.pop())
                expr = LookupNode(expr, attribute)
            elif self.maybe('LBRACKET', '('):
                arguments = self.parseAssignList()
                self.consume('RBRACKET', ')')
                expr = CallNode(expr, arguments)
            elif self.maybe('LBRACKET', '['):
                subscript = self.parseExprList()
                self.consume('RBRACKET', ']')
                expr = SubscriptNode(expr, subscript)
            else:
                return expr

    def parsePrimary(self) -> ParseNode:
        if self.maybe('LBRACKET', '('):
            items = self.parseAssignList()
            if len(items) == 1:
                if not self.maybe('COMMA'):
                    expr = items[0]
                    if isinstance(expr, AssignmentNode):
                        # Need to fix this to use a more useful token
                        self.log.append(DrakeSyntaxError('cannot put assignment inside grouping', self.current))
                    self.consume('RBRACKET', ')')
                    return GroupingNode(expr)
            for item in items:
                if isinstance(item, AssignmentNode):
                    # Need to fix this to use a more useful token
                    self.log.append(DrakeSyntaxError('cannot put assignment inside tuple', self.current))
            self.consume('RBRACKET', ')')
            return TupleNode(items)
        elif self.maybe('LBRACKET', '['):
            items = self.parseExprList()
            self.consume('RBRACKET', ']')
            return ListNode(items)
        elif self.maybe('LBRACKET', '{'):
            items = self.parsePairList()
            if all(isinstance(item, PairNode) for item in items):
                self.consume('RBRACKET', '}')
                return MapNode(items)
            for item in items:
                if isinstance(item, PairNode):
                    # Need to fix this to use a more useful token
                    self.log.append(DrakeSyntaxError('cannot put pairing inside block', self.current))
            self.consume('RBRACKET', '}')
            return BlockNode(items)
        elif self.matches(LITERAL):
            expr = LiteralNode(self.pop())
            return expr
        elif self.matches('IDENTIFIER'):
            expr = IdentifierNode(self.pop())
            return expr
        else:
            raise unexpectedToken(self.current)

    def parseBlock(self) -> BlockNode:
        self.consume('LBRACKET', '{')
        block = BlockNode(self.list(self.parseAssignment, 'RBRACKET'))
        self.consume('RBRACKET', '}')
        return block
